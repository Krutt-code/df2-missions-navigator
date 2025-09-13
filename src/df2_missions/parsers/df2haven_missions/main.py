"""Получение данных с сайта df2haven.com"""

from src.df2_missions.parsers.base import BaseParser
from src.df2_missions.parsers.df2haven_missions.data_processors.missions_extractor import (
    MissionsExtractor,
)
from src.df2_missions.schemas import Mission


class DF2HavenMissionsParser(BaseParser):
    """Класс для парсинга данных с сайта df2haven.com"""

    SITE_URL = "https://df2haven.com/missions/"

    async def get_missions_list(self) -> list[Mission]:
        soup = await self.get_site_page()
        return MissionsExtractor.extract_missions(soup)
