"""Получение данных с сайта df2profiler.com"""

from bs4 import BeautifulSoup as BS

from src.df2_missions.parsers.df2profiler_gamemap.data_processors.card_extractor import (
    CardExtractor,
)
from src.df2_missions.parsers.df2profiler_gamemap.data_processors.missions_extractor import (
    MissionsExtractor,
)
from src.df2_missions.schemas import Mission
from src.utils import RequestsManager
from src.utils.logger import get_class_logger


class DF2ProfilerGamemapParser:
    """Класс для парсинга данных с сайта df2profiler.com"""

    SITE_URL = "https://df2profiler.com/gamemap/"

    def __init__(self):
        self._logger = get_class_logger(self)
        self._site_page = None

    async def get_site_page(self, update: bool = False) -> BS:
        """Получение страницы сайта"""
        if update or self._site_page is None:
            async with RequestsManager() as requests_manager:
                response = await requests_manager.get_request(self.SITE_URL)
            if response is None:
                self._logger.error("Failed to get site page")
                raise Exception("Failed to get site page")
            self._logger.info("Site page received successfully")
            self._site_page = BS(response.text, "lxml")
        return self._site_page

    async def get_missions_list(self) -> list[Mission]:
        soup = await self.get_site_page()
        return MissionsExtractor.extract_missions(soup)

    async def map_data(self):
        soup = await self.get_site_page()
        return CardExtractor.extract_card_data(soup)
