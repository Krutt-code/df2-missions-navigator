"""Получение данных с сайта df2profiler.com"""

from src.df2_missions.parsers.base import BaseParser
from src.df2_missions.parsers.df2profiler_gamemap.data_processors.card_extractor import (
    CardExtractor,
)
from src.df2_missions.parsers.df2profiler_gamemap.data_processors.missions_extractor import (
    MissionsExtractor,
)
from src.df2_missions.schemas import Mission
from src.utils.cache import cache_to_file


class DF2ProfilerGamemapParser(BaseParser):
    """Класс для парсинга данных с сайта df2profiler.com"""

    SITE_URL = "https://df2profiler.com/gamemap/"

    @cache_to_file(ttl=7200, namespace="df2profiler_missions", use_pickle=True)
    async def get_missions_list(self) -> list[Mission]:
        self._logger.info("Начинаем получение списка миссий с df2profiler.com")
        soup = await self.get_site_page()
        missions = MissionsExtractor.extract_missions(soup)
        self._logger.info(f"Получено {len(missions)} миссий с df2profiler.com")
        return missions

    @cache_to_file(ttl=86400, namespace="df2profiler_map", use_pickle=True)  # 24 часа
    async def get_map_data(self):
        self._logger.info("Начинаем получение данных карты с df2profiler.com")
        soup = await self.get_site_page()
        map_data = CardExtractor.extract_card_data(soup)
        self._logger.info(
            f"Получена карта с {len(map_data.cells)} ячейками с df2profiler.com"
        )
        return map_data
