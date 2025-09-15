"""Получение данных с сайта df2haven.com"""

from src.df2_missions.parsers.base import BaseParser
from src.df2_missions.parsers.df2haven_missions.data_processors.missions_extractor import (
    MissionsExtractor,
)
from src.df2_missions.schemas import Mission
from src.utils.cache import cache_to_file


class DF2HavenMissionsParser(BaseParser):
    """Класс для парсинга данных с сайта df2haven.com"""

    SITE_URL = "https://df2haven.com/missions/"

    @cache_to_file(ttl=7200, namespace="df2haven_missions", use_pickle=True)  # 2 часа
    async def get_missions_list(self) -> list[Mission]:
        self._logger.info("Начинаем получение списка миссий с df2haven.com")
        soup = await self.get_site_page()
        missions = MissionsExtractor.extract_missions(soup)
        self._logger.info(f"Получено {len(missions)} миссий с df2haven.com")
        return missions
