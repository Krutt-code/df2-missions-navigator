import argparse
import asyncio

from src.df2_missions.enums import AvanpostType
from src.factories import create_missions_service
from src.utils import clear_cache, get_cache_info
from src.utils.logger import get_logger


async def main():
    # Настройка логирования для основного скрипта
    logger = get_logger("run")
    logger.info("Запуск приложения df2-missions-navigator")

    # Обработка аргументов командной строки
    parser = argparse.ArgumentParser(description="DF2 Missions Navigator")
    parser.add_argument(
        "--clear-cache", action="store_true", help="Очистить весь кеш перед запуском"
    )
    parser.add_argument(
        "--clear-namespace",
        type=str,
        help="Очистить кеш определенного namespace (например: df2profiler_missions)",
    )
    parser.add_argument(
        "--cache-info", action="store_true", help="Показать информацию о кеше"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Показать подробную информацию об объектах",
    )
    args = parser.parse_args()

    # Вывод информации о кеше
    if args.cache_info:
        cache_info = get_cache_info()
        print("Информация о кеше:")
        print(f"Записей в памяти: {cache_info['memory_cache']['entries']}")
        print(f"Пространств имен в памяти: {cache_info['memory_cache']['namespaces']}")
        print(f"Файлов кеша: {cache_info['file_cache']['entries']}")
        print(
            f"Размер файлов кеша: {cache_info['file_cache']['size_bytes'] / 1024:.2f} KB"
        )
        if cache_info["file_cache"]["files"]:
            print(f"Файлы кеша: {', '.join(cache_info['file_cache']['files'][:5])}...")

    # Очистка кеша при необходимости
    if args.clear_cache:
        logger.info("Очистка всего кеша перед запуском")
        clear_cache()
        print("Кеш успешно очищен")

    if args.clear_namespace and args.clear_namespace.strip():
        namespace = args.clear_namespace.strip()
        logger.info(f"Очистка кеша для namespace '{namespace}'")
        clear_cache(namespace=namespace)
        print(f"Кеш для namespace '{namespace}' успешно очищен")

    # Создаем сервис миссий через фабрику
    missions_service = create_missions_service()

    # Получаем все миссии
    logger.info("Запрашиваем список всех миссий")
    missions = await missions_service.get_all_missions()
    print(f"Всего доступно миссий: {len(missions)}")

    # Показываем типы объектов при необходимости
    if args.verbose and missions:
        first_mission = missions[0]
        print("\nПример объекта миссии:")
        print(f"- Тип: {type(first_mission).__name__}")
        print(f"- ID: {first_mission.id}")
        print(f"- Цель миссии: {first_mission.target.type.value}")
        print(f"- Тип цели миссии: {type(first_mission.target.type).__name__}")
        if first_mission.building_location:
            print(f"- Локация: {first_mission.building_location.name}")
            print(f"- Район: {first_mission.building_location.district.value}")
            print(
                f"- Тип района: {type(first_mission.building_location.district).__name__}"
            )

    logger.info("Запрашиваем автостартовые миссии")
    autostart_missions = await missions_service.get_autostart_missions()
    print(f"Автостартовых миссий: {len(autostart_missions)}")

    normalized_missions = (
        await missions_service.missions_repository.normalize_missions_locations(
            autostart_missions
        )
    )
    normalized_missions = missions_service.missions_repository.filter_missions(
        missions=normalized_missions,
        has_building=True,
        has_coordinates=True,
        has_quest_walkthrough=True,
    )
    start_building = missions_service.missions_repository.filter_missions(
        missions=await missions_service.get_all_missions(),
        building_types=[AvanpostType.DBPD],
    )[0].building_location
    print(f"Нормализованных миссий: {len(normalized_missions)}")

    logger.info("Построение оптимального маршрута")
    route = await missions_service.get_missions_route(
        missions=normalized_missions,
        start_building=start_building,
    )

    # Выводим маршрут
    print("\nОптимальный маршрут:")
    for i, mission in route.items():
        location = mission.building_location
        coords = (
            f"({location.x}, {location.y})"
            if location and location.x is not None
            else "N/A"
        )
        print(
            (
                f"{i + 1}. {mission.target.type}: {getattr(location, 'name', 'N/A')} {coords}"
                # f"\nРешение:\n{mission.quest_walkthrough}\n"
            )
        )

    logger.info("Выполнение завершено")


if __name__ == "__main__":
    asyncio.run(main())
