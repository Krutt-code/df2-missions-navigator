"""
Фабрики для создания компонентов для работы с миссиями.
"""

from typing import List

from src.df2_missions.interfaces import GameMapDataSource, MissionsDataSource
from src.df2_missions.parsers import DF2HavenMissionsParser, DF2ProfilerGamemapParser
from src.df2_missions.repositories import DF2MissionsRepository
from src.services.missions import MissionsService
from src.utils.logger import get_logger


def create_missions_service() -> MissionsService:
    """
    Создает и настраивает сервис для работы с миссиями
    со всеми необходимыми зависимостями.

    Returns:
        Полностью настроенный сервис миссий
    """
    logger = get_logger("factories.missions")
    logger.info("Создание сервиса миссий и его зависимостей")

    # Создаем источники данных
    logger.debug("Инициализация парсеров данных")
    df2haven_parser = DF2HavenMissionsParser()
    df2profiler_parser = DF2ProfilerGamemapParser()

    # Источники данных о миссиях
    mission_sources: List[MissionsDataSource] = [df2haven_parser, df2profiler_parser]

    # Источник данных о карте
    map_source: GameMapDataSource = df2profiler_parser

    # Создаем репозиторий
    logger.debug("Инициализация репозитория миссий")
    missions_repository = DF2MissionsRepository(
        missions_sources=mission_sources, map_source=map_source
    )

    # Создаем и возвращаем сервис
    logger.debug("Инициализация сервиса миссий")
    service = MissionsService(missions_repository)
    logger.info("Сервис миссий успешно создан")
    return service
