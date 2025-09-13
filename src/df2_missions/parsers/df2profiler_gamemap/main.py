"""Получение данных с сайта df2profiler.com"""

from src.df2_missions.parsers.base import BaseParser
from src.df2_missions.parsers.df2profiler_gamemap.data_processors.card_extractor import (
    CardExtractor,
)
from src.df2_missions.parsers.df2profiler_gamemap.data_processors.missions_extractor import (
    MissionsExtractor,
)
from src.df2_missions.schemas import Mission


class DF2ProfilerGamemapParser(BaseParser):
    """Класс для парсинга данных с сайта df2profiler.com"""

    SITE_URL = "https://df2profiler.com/gamemap/"

    async def get_missions_list(self) -> list[Mission]:
        soup = await self.get_site_page()
        return MissionsExtractor.extract_missions(soup)

    async def get_map_data(self):
        soup = await self.get_site_page()
        return CardExtractor.extract_card_data(soup)
