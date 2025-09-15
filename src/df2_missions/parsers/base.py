from typing import Optional

from bs4 import BeautifulSoup as BS

from src.utils import RequestsManager
from src.utils.cache import cache_to_file
from src.utils.logger import get_class_logger


class BaseParser:
    """Базовый класс для парсеров"""

    SITE_URL: str

    def __init__(self):
        self._logger = get_class_logger(self)
        self._site_page = None

    @cache_to_file(ttl=3600, namespace="parser_data", use_pickle=True)
    async def get_site_page(
        self, url: Optional[str] = None, *, update: bool = False
    ) -> BS:
        """Получение страницы сайта"""
        if update or self._site_page is None and (hasattr(self, "SITE_URL") or url):
            if not url:
                url = self.SITE_URL
            self._logger.info(f"Загрузка данных с {url}")
            async with RequestsManager() as requests_manager:
                response = await requests_manager.get_request(url)
            if response is None:
                self._logger.error(f"Не удалось получить данные с {url}")
                raise Exception("Failed to get site page")
            self._logger.info(f"Данные с {url} успешно получены")
            self._site_page = BS(response.text, "lxml")
        return self._site_page
