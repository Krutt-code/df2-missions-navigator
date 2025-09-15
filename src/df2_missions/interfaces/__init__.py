"""
Модуль с интерфейсами для обеспечения чистой архитектуры и слабой связности компонентов.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Protocol, Tuple, TypeVar, Union

from src.df2_missions.enums import AvanpostType, BuildingType, District, MissionType
from src.df2_missions.schemas import BuildingLocation, MapDF2, MapDF2Cell, Mission

T = TypeVar("T")


class MissionsDataSource(Protocol):
    """Интерфейс источника данных о миссиях"""

    @abstractmethod
    async def get_missions_list(self) -> List[Mission]:
        """Получить список миссий из источника данных"""
        pass


class GameMapDataSource(Protocol):
    """Интерфейс источника данных о карте игры"""

    @abstractmethod
    async def get_map_data(self) -> MapDF2:
        """Получить данные карты из источника данных"""
        pass


class MissionsRepository(ABC):
    """Репозиторий для работы с миссиями"""

    @abstractmethod
    async def get_all_missions(self) -> List[Mission]:
        """Получить все доступные миссии из всех источников"""
        pass

    @abstractmethod
    def filter_missions(
        self,
        missions: List[Mission],
        *,
        level_range: Optional[Tuple[int, int]] = None,
        types: Optional[List[MissionType]] = None,
        districts: Optional[List[District]] = None,
        building_types: Optional[List[Union[BuildingType, AvanpostType]]] = None,
    ) -> List[Mission]:
        """Фильтровать миссии по различным критериям"""
        pass

    @abstractmethod
    async def get_map(self) -> MapDF2:
        """Получить данные карты"""
        pass

    @abstractmethod
    async def build_missions_route(
        self,
        missions: List[Mission],
        *,
        start_building: Optional[BuildingLocation] = None,
        start_cell: Optional[MapDF2Cell] = None,
    ) -> dict[int, Mission]:
        """Построить оптимальный маршрут для выполнения миссий"""
        pass
