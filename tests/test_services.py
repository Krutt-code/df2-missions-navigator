from unittest.mock import AsyncMock

import pytest

from src.df2_missions.enums import BuildingType, District, MissionType
from src.df2_missions.schemas import BuildingLocation, Mission, Target
from src.services.missions import MissionsService


class TestMissionsService:
    """Тесты для сервиса миссий"""

    @pytest.fixture
    def df2_missions_mock(self):
        """Фикстура, возвращающая мок DF2Missions"""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def missions_service(self, df2_missions_mock):
        """Фикстура, возвращающая экземпляр MissionsService с моком DF2Missions"""
        return MissionsService(df2_missions_mock)

    @pytest.fixture
    def sample_missions(self):
        """Фикстура с тестовыми миссиями разных типов"""
        return [
            # Автостартовая миссия FIND_ITEM
            Mission(
                id="1",
                target=Target(type=MissionType.FIND_ITEM, description="Find item test"),
                building_location=BuildingLocation(
                    name="Building A",
                    district=District.DALLBOW,
                    level=5,
                    building_type=BuildingType.HOU,
                ),
            ),
            # Автостартовая миссия COLLECT_ITEMS
            Mission(
                id="2",
                target=Target(
                    type=MissionType.COLLECT_ITEMS, description="Collect items test"
                ),
                building_location=BuildingLocation(
                    name="Building B",
                    district=District.ALBANDALE_PARK,
                    level=10,
                    building_type=BuildingType.SHP,
                ),
            ),
            # Автостартовая миссия FIND_PERSON
            Mission(
                id="3",
                target=Target(
                    type=MissionType.FIND_PERSON, description="Find person test"
                ),
                building_location=BuildingLocation(
                    name="Building C",
                    district=District.GREYWOOD,
                    level=15,
                    building_type=BuildingType.APT,
                ),
            ),
            # Не автостартовая миссия
            Mission(
                id="4",
                target=Target(type=MissionType.KILL_BOSS, description="Kill boss test"),
                building_location=BuildingLocation(
                    name="Building D",
                    district=District.LERWILLBURY,
                    level=20,
                    building_type=BuildingType.HOU,
                ),
            ),
        ]

    async def test_get_all_missions(
        self, missions_service, df2_missions_mock, sample_missions
    ):
        """Тест получения всех миссий"""
        # Настройка мока
        df2_missions_mock.get_missions.return_value = sample_missions

        # Вызов тестируемого метода
        result = await missions_service.get_all_missions()

        # Проверки
        df2_missions_mock.get_missions.assert_called_once()
        assert result == sample_missions
        assert len(result) == 4

    async def test_get_autostart_missions(
        self, missions_service, df2_missions_mock, sample_missions
    ):
        """Тест получения автостартовых миссий"""
        # Настройка моков
        df2_missions_mock.get_missions.return_value = sample_missions
        df2_missions_mock.missions_filter.return_value = [
            m
            for m in sample_missions
            if m.target.type
            in [
                MissionType.FIND_ITEM,
                MissionType.COLLECT_ITEMS,
                MissionType.FIND_PERSON,
            ]
        ]

        # Вызов тестируемого метода
        result = await missions_service.get_autostart_missions()

        # Проверки
        df2_missions_mock.get_missions.assert_called_once()
        df2_missions_mock.missions_filter.assert_called_once()

        # Проверяем вызов missions_filter с правильными параметрами
        _, kwargs = df2_missions_mock.missions_filter.call_args
        assert kwargs["types"] == [
            MissionType.FIND_ITEM,
            MissionType.COLLECT_ITEMS,
            MissionType.FIND_PERSON,
        ]
        assert kwargs["level_range"] is None
        assert kwargs["districts"] is None
        assert kwargs["building_types"] is None

        # Проверяем результат
        assert len(result) == 3
        assert all(m.id in ["1", "2", "3"] for m in result)
        assert all(
            m.target.type
            in [
                MissionType.FIND_ITEM,
                MissionType.COLLECT_ITEMS,
                MissionType.FIND_PERSON,
            ]
            for m in result
        )

    async def test_get_autostart_missions_with_filters(
        self, missions_service, df2_missions_mock, sample_missions
    ):
        """Тест получения автостартовых миссий с дополнительными фильтрами"""
        # Настройка мока
        df2_missions_mock.get_missions.return_value = sample_missions
        df2_missions_mock.missions_filter.return_value = [
            m
            for m in sample_missions
            if m.id == "1"  # Только миссия FIND_ITEM в Dallbow
        ]

        # Параметры фильтрации
        level_range = (1, 10)
        districts = [District.DALLBOW]
        building_types = [BuildingType.HOU]

        # Вызов тестируемого метода
        result = await missions_service.get_autostart_missions(
            level_range=level_range, districts=districts, building_types=building_types
        )

        # Проверки
        df2_missions_mock.get_missions.assert_called_once()
        df2_missions_mock.missions_filter.assert_called_once()

        # Проверяем вызов missions_filter с правильными параметрами
        _, kwargs = df2_missions_mock.missions_filter.call_args
        assert kwargs["types"] == [
            MissionType.FIND_ITEM,
            MissionType.COLLECT_ITEMS,
            MissionType.FIND_PERSON,
        ]
        assert kwargs["level_range"] == level_range
        assert kwargs["districts"] == districts
        assert kwargs["building_types"] == building_types

        # Проверяем результат
        assert len(result) == 1
        assert result[0].id == "1"
        assert result[0].building_location.district == District.DALLBOW
        assert result[0].building_location.building_type == BuildingType.HOU

    async def test_get_autostart_missions_with_provided_missions(
        self, missions_service, df2_missions_mock, sample_missions
    ):
        """Тест получения автостартовых миссий с предоставленным списком миссий"""
        # Настройка мока
        df2_missions_mock.missions_filter.return_value = [
            m for m in sample_missions if m.id in ["1", "3"]
        ]

        # Вызов тестируемого метода с предоставленным списком миссий
        result = await missions_service.get_autostart_missions(
            missions=sample_missions, districts=[District.DALLBOW, District.GREYWOOD]
        )

        # Проверки
        df2_missions_mock.get_missions.assert_not_called()  # Не должен вызываться, так как миссии уже предоставлены
        df2_missions_mock.missions_filter.assert_called_once()

        # Проверяем вызов missions_filter с правильными параметрами
        args, kwargs = df2_missions_mock.missions_filter.call_args
        assert args[0] == sample_missions
        assert kwargs["districts"] == [District.DALLBOW, District.GREYWOOD]

        # Проверяем результат
        assert len(result) == 2
        assert set(m.id for m in result) == {"1", "3"}
