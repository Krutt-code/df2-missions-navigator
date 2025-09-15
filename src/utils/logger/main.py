"""
Лёгкий инструмент логирования.

• Поддерживает:
    get_logger(name)          – любой произвольный логгер
    get_function_logger(func) – логгер функции/метода
    get_class_logger(obj)     – логгер экземпляра класса
"""

from __future__ import annotations

import contextvars
import logging
from pathlib import Path

from concurrent_log_handler import ConcurrentRotatingFileHandler

# ──────────────────────────────
# Параметры по умолчанию
# ──────────────────────────────
_LOG_DIR = Path("logs")
_LOG_DIR.mkdir(parents=True, exist_ok=True)

_LOG_FILE = _LOG_DIR / "app.log"

try:
    from src.utils.settings import SETTINGS

    _LOG_LEVEL = SETTINGS.log_level
except Exception:
    _LOG_LEVEL = logging.INFO

_LOG_FMT = "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"

_current_name: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_name", default="default"
)
_cache: dict[str, logging.Logger] = {}  # кэш созданных логгеров


# ──────────────────────────────
# Внутренние функции
# ──────────────────────────────
def _build_logger(name: str) -> logging.Logger:
    """Создаёт и настраивает новый logger с именем *name* (если его ещё нет)."""
    logger = logging.getLogger(name)

    # Если хендлеры уже установлены – значит логгер сконфигурирован; просто вернём его
    if logger.handlers:
        return logger

    logger.setLevel(_LOG_LEVEL)
    logger.propagate = False  # не дублируем записи в root-logger

    file_handler = ConcurrentRotatingFileHandler(
        _LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=7, encoding="utf-8"
    )
    stream_handler = logging.StreamHandler()

    formatter = logging.Formatter(_LOG_FMT)
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger


# ──────────────────────────────
# Публичное API
# ──────────────────────────────
def get_logger(name: str | None = None) -> logging.Logger:
    """
    Возвращает (и кеширует) логгер с указанным *name*.
    Если *name* не указан, используется текущее значение context-переменной «current_name».
    """
    name = name or _current_name.get()

    # Используем кэш, чтобы не создавать одинаковые логгеры
    if name not in _cache:
        _cache[name] = _build_logger(name)

    return _cache[name]


def get_function_logger(func) -> logging.Logger:
    """Логгер вида «module:function»."""
    full_name = f"{func.__module__}:{func.__qualname__}"
    return get_logger(full_name)


def get_class_logger(obj) -> logging.Logger:
    """Логгер вида «module:ClassName»."""
    full_name = f"{obj.__module__}:{obj.__class__.__qualname__}"
    return get_logger(full_name)
