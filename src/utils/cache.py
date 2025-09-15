"""
Утилита для кеширования данных.

Поддерживает:
- Кеширование в памяти
- Файловый кеш (JSON)
- Установку TTL (Time To Live)
"""

import functools
import importlib
import inspect
import json
import os
import pickle
import time
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from src.utils.logger import get_logger

# Пытаемся импортировать Pydantic для типов моделей
try:
    from pydantic import BaseModel as PydanticModel

    HAVE_PYDANTIC = True
except ImportError:
    HAVE_PYDANTIC = False
    PydanticModel = type("PydanticModel", (), {})

T = TypeVar("T")

# Директория для хранения кеша
CACHE_DIR = Path("./cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Время жизни кеша по умолчанию (в секундах)
DEFAULT_TTL = 3600  # 1 час

# Логгер для кеша
logger = get_logger("utils.cache")

# Кеш в памяти
_memory_cache: Dict[str, Dict[str, Any]] = {}


class CustomJSONEncoder(json.JSONEncoder):
    """
    Кастомный JSON энкодер, который правильно сериализует:
    - Pydantic модели
    - Enum значения
    - Наборы (set)
    - Другие нестандартные типы
    """

    def default(self, obj):
        # Обработка Pydantic моделей
        if HAVE_PYDANTIC and isinstance(obj, PydanticModel):
            return {
                "__type__": "pydantic",
                "__class__": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
                "__value__": (
                    obj.model_dump() if hasattr(obj, "model_dump") else obj.dict()
                ),
            }

        # Обработка перечислений
        if isinstance(obj, Enum):
            return {
                "__type__": "enum",
                "__class__": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
                "__value__": obj.value,
            }

        # Обработка множеств
        if isinstance(obj, set):
            return {"__type__": "set", "__value__": list(obj)}

        # Обработка кортежей
        if isinstance(obj, tuple):
            return {"__type__": "tuple", "__value__": list(obj)}

        # Обработка классов и других типов
        if inspect.isclass(obj):
            return {
                "__type__": "class",
                "__class__": f"{obj.__module__}.{obj.__name__}",
            }

        # Для других типов используем дефолтную сериализацию
        return super().default(obj)


def custom_json_decoder_hook(obj):
    """
    Кастомный декодер для восстановления объектов из JSON.
    """
    if not isinstance(obj, dict):
        return obj

    # Проверяем, есть ли маркер типа
    if "__type__" in obj:
        obj_type = obj["__type__"]

        # Восстановление Pydantic моделей
        if obj_type == "pydantic" and HAVE_PYDANTIC:
            try:
                class_path = obj["__class__"]
                module_name, class_name = class_path.rsplit(".", 1)
                module = importlib.import_module(module_name)
                model_class = getattr(module, class_name)

                if hasattr(model_class, "model_validate"):
                    return model_class.model_validate(obj["__value__"])
                else:
                    return model_class(**obj["__value__"])
            except (ImportError, AttributeError, ValueError) as e:
                logger.error(f"Failed to restore Pydantic model: {e}")
                return obj["__value__"]

        # Восстановление перечислений
        elif obj_type == "enum":
            try:
                class_path = obj["__class__"]
                module_name, class_name = class_path.rsplit(".", 1)
                module = importlib.import_module(module_name)
                enum_class = getattr(module, class_name)
                return enum_class(obj["__value__"])
            except (ImportError, AttributeError, ValueError) as e:
                logger.error(f"Failed to restore Enum: {e}")
                return obj["__value__"]

        # Восстановление множеств
        elif obj_type == "set":
            return set(obj["__value__"])

        # Восстановление кортежей
        elif obj_type == "tuple":
            return tuple(obj["__value__"])

        # Восстановление классов
        elif obj_type == "class":
            try:
                class_path = obj["__class__"]
                module_name, class_name = class_path.rsplit(".", 1)
                module = importlib.import_module(module_name)
                return getattr(module, class_name)
            except (ImportError, AttributeError) as e:
                logger.error(f"Failed to restore class: {e}")
                return obj

    return obj


def _get_cache_key(func: Callable, *args: Any, **kwargs: Any) -> str:
    """
    Создает ключ кеша на основе функции и ее аргументов.

    Args:
        func: Функция для кеширования
        args: Позиционные аргументы функции
        kwargs: Именованные аргументы функции

    Returns:
        Строковый ключ кеша
    """
    # Формируем ключ на основе имени функции и аргументов
    key_parts = [f"{func.__module__}.{func.__qualname__}"]
    if args:
        key_parts.append(str(args))
    if kwargs:
        key_parts.append(str(kwargs))
    return ":".join(key_parts)


def _get_cache_filepath(cache_key: str, namespace: str = "default") -> Path:
    """
    Получает путь к файлу кеша.

    Args:
        cache_key: Ключ кеша
        namespace: Пространство имен кеша

    Returns:
        Путь к файлу кеша
    """
    # Хешируем ключ для безопасного использования в имени файла
    filename = f"{namespace}_{hash(cache_key)}.cache"
    return CACHE_DIR / filename


def cache_to_memory(ttl: int = DEFAULT_TTL, namespace: str = "default") -> Callable:
    """
    Декоратор для кеширования результатов функции в памяти.

    Args:
        ttl: Время жизни кеша в секундах
        namespace: Пространство имен кеша

    Returns:
        Декорированная функция
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            cache_key = _get_cache_key(func, *args, **kwargs)

            # Инициализируем кеш для namespace, если его еще нет
            if namespace not in _memory_cache:
                _memory_cache[namespace] = {}

            # Проверяем наличие данных в кеше и их актуальность
            if cache_key in _memory_cache[namespace]:
                cached_data = _memory_cache[namespace][cache_key]
                cached_time = cached_data.get("timestamp", 0)

                # Если данные актуальны, возвращаем их
                if time.time() - cached_time < ttl:
                    logger.debug(f"Cache hit for {func.__name__} (memory)")
                    return cast(T, cached_data["data"])
                else:
                    logger.debug(f"Cache expired for {func.__name__} (memory)")

            # Данных в кеше нет или они устарели, вызываем функцию
            result = func(*args, **kwargs)

            # Сохраняем результат в кеш
            _memory_cache[namespace][cache_key] = {
                "data": result,
                "timestamp": time.time(),
            }
            logger.debug(f"Cached result for {func.__name__} (memory)")

            return result

        return wrapper

    return decorator


def cache_to_file(
    ttl: int = DEFAULT_TTL, namespace: str = "default", use_pickle: bool = False
) -> Callable:
    """
    Декоратор для кеширования результатов функции в файл.

    Args:
        ttl: Время жизни кеша в секундах
        namespace: Пространство имен кеша
        use_pickle: Использовать pickle вместо JSON для сериализации

    Returns:
        Декорированная функция
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            cache_key = _get_cache_key(func, *args, **kwargs)
            cache_path = _get_cache_filepath(cache_key, namespace)

            # Проверяем наличие файла кеша и его актуальность
            if cache_path.exists():
                try:
                    if use_pickle:
                        with open(cache_path, "rb") as f:
                            cached_data = pickle.load(f)
                    else:
                        with open(cache_path, "r", encoding="utf-8") as f:
                            cached_data = json.load(
                                f, object_hook=custom_json_decoder_hook
                            )

                    cached_time = cached_data.get("timestamp", 0)
                    expiry_time = datetime.fromtimestamp(cached_time) + timedelta(
                        seconds=ttl
                    )

                    # Если данные актуальны, возвращаем их
                    if datetime.now() < expiry_time:
                        logger.debug(f"Cache hit for {func.__name__} (file)")
                        return cast(T, cached_data["data"])
                    else:
                        logger.debug(f"Cache expired for {func.__name__} (file)")
                except (json.JSONDecodeError, pickle.PickleError, IOError) as e:
                    logger.warning(f"Cache error for {func.__name__}: {str(e)}")

            # Данных в кеше нет, они устарели или произошла ошибка, вызываем функцию
            result = await func(*args, **kwargs)

            # Сохраняем результат в файловый кеш
            try:
                cache_data = {"data": result, "timestamp": datetime.now().timestamp()}

                if use_pickle:
                    with open(cache_path, "wb") as f:
                        pickle.dump(cache_data, f, protocol=pickle.HIGHEST_PROTOCOL)
                else:
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump(
                            cache_data, f, ensure_ascii=False, cls=CustomJSONEncoder
                        )

                logger.debug(f"Cached result for {func.__name__} (file)")
            except (IOError, TypeError) as e:
                logger.error(f"Failed to cache result for {func.__name__}: {str(e)}")

            return result

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            cache_key = _get_cache_key(func, *args, **kwargs)
            cache_path = _get_cache_filepath(cache_key, namespace)

            # Проверяем наличие файла кеша и его актуальность
            if cache_path.exists():
                try:
                    if use_pickle:
                        with open(cache_path, "rb") as f:
                            cached_data = pickle.load(f)
                    else:
                        with open(cache_path, "r", encoding="utf-8") as f:
                            cached_data = json.load(
                                f, object_hook=custom_json_decoder_hook
                            )

                    cached_time = cached_data.get("timestamp", 0)
                    expiry_time = datetime.fromtimestamp(cached_time) + timedelta(
                        seconds=ttl
                    )

                    # Если данные актуальны, возвращаем их
                    if datetime.now() < expiry_time:
                        logger.debug(f"Cache hit for {func.__name__} (file)")
                        return cast(T, cached_data["data"])
                    else:
                        logger.debug(f"Cache expired for {func.__name__} (file)")
                except (json.JSONDecodeError, pickle.PickleError, IOError) as e:
                    logger.warning(f"Cache error for {func.__name__}: {str(e)}")

            # Данных в кеше нет, они устарели или произошла ошибка, вызываем функцию
            result = func(*args, **kwargs)

            # Сохраняем результат в файловый кеш
            try:
                cache_data = {"data": result, "timestamp": datetime.now().timestamp()}

                if use_pickle:
                    with open(cache_path, "wb") as f:
                        pickle.dump(cache_data, f, protocol=pickle.HIGHEST_PROTOCOL)
                else:
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump(
                            cache_data, f, ensure_ascii=False, cls=CustomJSONEncoder
                        )

                logger.debug(f"Cached result for {func.__name__} (file)")
            except (IOError, TypeError) as e:
                logger.error(f"Failed to cache result for {func.__name__}: {str(e)}")

            return result

        # Возвращаем соответствующий враппер в зависимости от типа функции
        if asyncio_is_coroutine_function(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def clear_cache(namespace: Optional[str] = None) -> None:
    """
    Очищает кеш в памяти и/или файловый кеш для указанного пространства имен.
    Если namespace не указан, очищает весь кеш.

    Args:
        namespace: Пространство имен кеша для очистки
    """
    # Очистка кеша в памяти
    if namespace is None:
        _memory_cache.clear()
        logger.info("Cleared all memory cache")
    elif namespace in _memory_cache:
        del _memory_cache[namespace]
        logger.info(f"Cleared memory cache for namespace '{namespace}'")

    # Очистка файлового кеша
    try:
        if namespace is None:
            # Удаляем все файлы кеша
            for file in CACHE_DIR.glob("*.cache"):
                file.unlink()
            logger.info("Cleared all file cache")
        else:
            # Удаляем только файлы с указанным namespace
            for file in CACHE_DIR.glob(f"{namespace}_*.cache"):
                file.unlink()
            logger.info(f"Cleared file cache for namespace '{namespace}'")
    except IOError as e:
        logger.error(f"Failed to clear file cache: {str(e)}")


def get_cache_info(namespace: Optional[str] = None) -> Dict[str, Any]:
    """
    Получает информацию о текущем состоянии кеша.

    Args:
        namespace: Пространство имен кеша

    Returns:
        Словарь с информацией о кеше
    """
    info = {
        "memory_cache": {
            "entries": 0,
            "namespaces": list(_memory_cache.keys()),
        },
        "file_cache": {"entries": 0, "size_bytes": 0, "files": []},
    }

    # Информация о кеше в памяти
    if namespace is None:
        for ns, cache_data in _memory_cache.items():
            info["memory_cache"]["entries"] += len(cache_data)
    elif namespace in _memory_cache:
        info["memory_cache"]["entries"] = len(_memory_cache[namespace])

    # Информация о файловом кеше
    try:
        pattern = f"{namespace}_*.cache" if namespace else "*.cache"
        cache_files = list(CACHE_DIR.glob(pattern))
        info["file_cache"]["entries"] = len(cache_files)
        info["file_cache"]["files"] = [f.name for f in cache_files]
        info["file_cache"]["size_bytes"] = sum(f.stat().st_size for f in cache_files)
    except IOError as e:
        logger.error(f"Failed to get file cache info: {str(e)}")

    return info


def asyncio_is_coroutine_function(func: Callable) -> bool:
    """
    Проверяет, является ли функция корутиной.

    Args:
        func: Проверяемая функция

    Returns:
        True, если функция является корутиной, иначе False
    """
    import inspect

    return inspect.iscoroutinefunction(func)
