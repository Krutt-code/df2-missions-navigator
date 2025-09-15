from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from src.df2_missions.enums import District, MissionType
from src.df2_missions.parsers.base import BaseParser
from src.df2_missions.parsers.df2haven_missions.data_processors.missions_extractor import (
    MissionsExtractor,
)
from src.df2_missions.parsers.df2haven_missions.main import DF2HavenMissionsParser
from src.df2_missions.parsers.df2profiler_gamemap.data_processors.card_extractor import (
    CardExtractor,
)
from src.df2_missions.parsers.df2profiler_gamemap.data_processors.missions_extractor import (
    MissionsExtractor as ProfilerMissionsExtractor,
)
from src.df2_missions.parsers.df2profiler_gamemap.main import DF2ProfilerGamemapParser


class TestBaseParser:
    """Тесты для базового парсера"""

    @patch("src.df2_missions.parsers.base.RequestsManager")
    async def test_get_site_page(self, mock_requests_manager):
        """Тест получения страницы сайта"""
        # Настройка мока
        mock_session = AsyncMock()
        mock_requests_manager.return_value.__aenter__.return_value = mock_session

        mock_response = MagicMock()
        mock_response.text = "<html><body>Test content</body></html>"
        mock_session.get_request.return_value = mock_response

        # Создаем тестируемый объект
        parser = BaseParser()
        parser.SITE_URL = "https://test.com"

        # Тестируем
        result = await parser.get_site_page()

        # Проверяем результат
        assert isinstance(result, BeautifulSoup)
        assert "Test content" in str(result)
        mock_session.get_request.assert_called_once_with("https://test.com")

    @patch("src.df2_missions.parsers.base.RequestsManager")
    async def test_get_site_page_error(self, mock_requests_manager):
        """Тест обработки ошибки при получении страницы сайта"""
        # Настройка мока
        mock_session = AsyncMock()
        mock_requests_manager.return_value.__aenter__.return_value = mock_session
        mock_session.get_request.return_value = None

        # Создаем тестируемый объект
        parser = BaseParser()
        parser.SITE_URL = "https://test.com"

        # Проверяем, что вызывается исключение
        with pytest.raises(Exception, match="Failed to get site page"):
            await parser.get_site_page()


class TestDF2HavenMissionsParser:
    """Тесты для парсера миссий с df2haven.com"""

    @patch("src.df2_missions.parsers.df2haven_missions.main.MissionsExtractor")
    @patch("src.df2_missions.parsers.base.BaseParser.get_site_page")
    async def test_get_missions_list(self, mock_get_site_page, mock_extractor):
        """Тест получения списка миссий с df2haven.com"""
        # Настройка моков
        mock_soup = MagicMock()
        mock_get_site_page.return_value = mock_soup

        expected_missions = [MagicMock(), MagicMock()]
        mock_extractor.extract_missions.return_value = expected_missions

        # Создаем тестируемый объект и выполняем метод
        parser = DF2HavenMissionsParser()
        result = await parser.get_missions_list()

        # Проверяем результат
        assert result == expected_missions
        mock_get_site_page.assert_called_once()
        mock_extractor.extract_missions.assert_called_once_with(mock_soup)


class TestDF2ProfilerGamemapParser:
    """Тесты для парсера данных с df2profiler.com"""

    @patch(
        "src.df2_missions.parsers.df2profiler_gamemap.main.ProfilerMissionsExtractor"
    )
    @patch("src.df2_missions.parsers.base.BaseParser.get_site_page")
    async def test_get_missions_list(self, mock_get_site_page, mock_extractor):
        """Тест получения списка миссий с df2profiler.com"""
        # Настройка моков
        mock_soup = MagicMock()
        mock_get_site_page.return_value = mock_soup

        expected_missions = [MagicMock(), MagicMock()]
        mock_extractor.extract_missions.return_value = expected_missions

        # Создаем тестируемый объект и выполняем метод
        parser = DF2ProfilerGamemapParser()
        result = await parser.get_missions_list()

        # Проверяем результат
        assert result == expected_missions
        mock_get_site_page.assert_called_once()
        mock_extractor.extract_missions.assert_called_once_with(mock_soup)

    @patch("src.df2_missions.parsers.df2profiler_gamemap.main.CardExtractor")
    @patch("src.df2_missions.parsers.base.BaseParser.get_site_page")
    async def test_get_map_data(self, mock_get_site_page, mock_extractor):
        """Тест получения данных карты с df2profiler.com"""
        # Настройка моков
        mock_soup = MagicMock()
        mock_get_site_page.return_value = mock_soup

        expected_map = MagicMock()
        mock_extractor.extract_card_data.return_value = expected_map

        # Создаем тестируемый объект и выполняем метод
        parser = DF2ProfilerGamemapParser()
        result = await parser.get_map_data()

        # Проверяем результат
        assert result == expected_map
        mock_get_site_page.assert_called_once()
        mock_extractor.extract_card_data.assert_called_once_with(mock_soup)


class TestMissionsExtractor:
    """Тесты для экстрактора миссий с df2haven.com"""

    def test_extract_missions(self):
        """Тест извлечения миссий из HTML-страницы df2haven.com"""
        # Подготовка тестовых данных - упрощенный HTML с миссиями
        html = """
        <table id="missions_table">
            <thead>
                <tr>
                    <th>Mission Type</th>
                    <th>Details</th>
                    <th>Mission Building</th>
                    <th>Mission City</th>
                    <th>Giver Name</th>
                    <th>Giver Building</th>
                    <th>Giver City</th>
                    <th>Giver Location</th>
                    <th>Cash</th>
                    <th>Exp</th>
                </tr>
            </thead>
            <tbody>
                <tr id="mission-1">
                    <td>Find Item</td>
                    <td>Find a test item</td>
                    <td>Test Building</td>
                    <td>Dallbow</td>
                    <td>Test Person</td>
                    <td>Giver Building</td>
                    <td>Albandale Park</td>
                    <td>First floor</td>
                    <td>100</td>
                    <td>200</td>
                </tr>
            </tbody>
        </table>
        """
        soup = BeautifulSoup(html, "lxml")

        # Извлекаем миссии
        missions = MissionsExtractor.extract_missions(soup)

        # Проверки
        assert len(missions) == 1
        mission = missions[0]

        assert mission.id == "mission-1"
        assert mission.target.type == MissionType.FIND_ITEM
        assert mission.target.description == "Find a test item"
        assert mission.building_location.name == "Test Building"
        assert mission.building_location.district == District.DALLBOW
        assert mission.customer.name == "Test Person"
        assert mission.customer.location.district == District.ALBANDALE_PARK
        assert mission.customer.location_in_building == "First floor"
        assert mission.cash_reward == "100"
        assert mission.exp_reward == "200"
        assert mission.site == "https://df2haven.com/missions/"


class TestProfilerMissionsExtractor:
    """Тесты для экстрактора миссий с df2profiler.com"""

    def test_extract_missions(self):
        """Тест извлечения миссий из HTML-страницы df2profiler.com"""
        # Подготовка тестовых данных
        html = """
        <span data-searchselected data-building="Test Building" data-district="Dallbow" 
              data-xcoord="3" data-ycoord="4">
            <span class="giverLookup" data-building="Giver Building" data-giverdistrict="Albandale Park"
                  data-xcoord="1" data-ycoord="2">Test Person (Location)</span> wants you to:
            <strong>Find Item</strong> Find a test item in Building: Test Building
        </span>
        """
        soup = BeautifulSoup(html, "lxml")

        # Извлекаем миссии
        missions = ProfilerMissionsExtractor.extract_missions(soup)

        # Проверки
        assert len(missions) == 1
        mission = missions[0]

        assert mission.target.type == MissionType.FIND_ITEM
        assert "Find a test item" in mission.target.description
        assert mission.building_location.name == "Test Building"
        assert mission.building_location.district == District.DALLBOW
        assert mission.building_location.x == "3"
        assert mission.building_location.y == "4"
        assert mission.customer.name == "Test Person"
        assert mission.customer.location.district == District.ALBANDALE_PARK
        assert mission.site == "https://df2profiler.com/gamemap/"


class TestCardExtractor:
    """Тесты для экстрактора карты с df2profiler.com"""

    def test_extract_card_data(self):
        """Тест извлечения данных карты из HTML-страницы df2profiler.com"""
        # Подготовка тестовых данных
        html = """
        <table id="map">
            <tr>
                <td data-xcoord="1" data-ycoord="1" data-level="5" data-district="Dallbow" 
                    data-types="HOU" data-buildings="Building A (HOU),Building B (SHP)"></td>
                <td data-xcoord="1" data-ycoord="2" data-level="5" data-district="Dallbow" 
                    data-types="POL" data-buildings="Police Station (POL)"></td>
            </tr>
        </table>
        """
        soup = BeautifulSoup(html, "lxml")

        # Извлекаем карту
        map_data = CardExtractor.extract_card_data(soup)

        # Проверки
        assert len(map_data.cells) == 2

        # Проверяем первую ячейку с двумя зданиями
        cell1 = next(cell for cell in map_data.cells if cell.x == 1 and cell.y == 1)
        assert cell1.level == 5
        assert cell1.district == District.DALLBOW
        assert len(cell1.buildings) == 2
        assert cell1.buildings[0].name == "Building A"
        assert cell1.buildings[1].name == "Building B"

        # Проверяем вторую ячейку
        cell2 = next(cell for cell in map_data.cells if cell.x == 1 and cell.y == 2)
        assert cell2.level == 5
        assert cell2.district == District.DALLBOW
        assert len(cell2.buildings) == 1
        assert cell2.buildings[0].name == "Police Station"
        # Проверяем вторую ячейку
        cell2 = next(cell for cell in map_data.cells if cell.x == 1 and cell.y == 2)
        assert cell2.level == 5
        assert cell2.district == District.DALLBOW
        assert len(cell2.buildings) == 1
        assert cell2.buildings[0].name == "Police Station"
