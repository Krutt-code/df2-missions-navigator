from typing import List, Optional, Union

from src.df2_missions.enums import AvanpostType, BuildingType, District, MissionType
from src.df2_missions.interfaces import MissionsRepository
from src.df2_missions.schemas import BuildingLocation, Mission
from src.utils.logger import get_class_logger


class MissionsService:
    def __init__(self, missions_repository: MissionsRepository):
        """
        Инициализация сервиса миссий.

        Args:
            missions_repository: Репозиторий миссий
        """
        self.missions_repository = missions_repository
        self._logger = get_class_logger(self)
        self._logger.info("Сервис миссий инициализирован")

    async def get_all_missions(self) -> List[Mission]:
        """
        Получение всех доступных миссий.

        Returns:
            Список всех миссий
        """
        self._logger.info("Запрос на получение всех миссий")
        missions = await self.missions_repository.get_all_missions()
        self._logger.info(f"Получено {len(missions)} миссий")
        return missions

    async def get_autostart_missions(
        self,
        missions: Optional[List[Mission]] = None,
        *,
        level_range: Optional[tuple[int, int]] = None,
        districts: Optional[List[District]] = None,
        building_types: Optional[List[BuildingType]] = None,
    ) -> List[Mission]:
        """
        Миссии, которые не нужно брать, чтобы начать выполнение.
        Возвращает только типы: FIND_ITEM, COLLECT_ITEMS, FIND_PERSON.

        Args:
            missions: Предварительно загруженные миссии (если None, загружаются автоматически)
            level_range: Диапазон уровней для фильтрации
            districts: Список районов для фильтрации
            building_types: Список типов зданий для фильтрации

        Returns:
            Список отфильтрованных автостартовых миссий
        """
        self._logger.info("Запрос на получение автостартовых миссий")

        filter_info = []
        if level_range:
            filter_info.append(f"уровни {level_range}")
        if districts:
            filter_info.append(f"районы {[d.value for d in districts]}")
        if building_types:
            filter_info.append(f"типы зданий {[bt.value for bt in building_types]}")

        if filter_info:
            self._logger.debug(f"Фильтры: {', '.join(filter_info)}")

        if missions is None:
            self._logger.debug("Миссии не предоставлены, загружаем из репозитория")
            missions = await self.missions_repository.get_all_missions()

        auto_mission_types = [
            MissionType.FIND_ITEM,
            MissionType.COLLECT_ITEMS,
            MissionType.FIND_PERSON,
        ]

        self._logger.debug(
            f"Применяем фильтрацию по типам миссий: {[t.value for t in auto_mission_types]}"
        )

        filtered_missions = self.missions_repository.filter_missions(
            missions,
            level_range=level_range,
            types=auto_mission_types,
            districts=districts,
            building_types=building_types,
        )

        self._logger.info(
            f"Найдено {len(filtered_missions)} автостартовых миссий из {len(missions)}"
        )
        return filtered_missions

    async def get_missions_route(
        self,
        missions: Optional[List[Mission]] = None,
        *,
        start_building: Optional[BuildingLocation] = None,
        mission_types: Optional[List[MissionType]] = None,
        districts: Optional[List[District]] = None,
        level_range: Optional[tuple[int, int]] = None,
        building_types: Optional[List[Union[AvanpostType, BuildingType]]] = None,
    ) -> dict[int, Mission]:
        """
        Построение оптимального маршрута для выполнения отфильтрованных миссий.

        Args:
            missions: Предварительно загруженные миссии (если None, загружаются автоматически)
            start_building: Начальное здание маршрута
            mission_types: Типы миссий для фильтрации
            districts: Районы для фильтрации
            level_range: Диапазон уровней для фильтрации
            building_types: Типы зданий для фильтрации

        Returns:
            Словарь с оптимальным порядком миссий (индекс -> миссия)
        """
        self._logger.info("Запрос на построение оптимального маршрута миссий")

        # Получаем миссии, если не предоставлены
        if missions is None:
            self._logger.debug("Миссии не предоставлены, загружаем из репозитория")
            missions = await self.missions_repository.get_all_missions()

        # Применяем фильтры, если заданы
        if any(
            param is not None
            for param in [mission_types, districts, level_range, building_types]
        ):
            self._logger.debug("Применяем фильтры перед построением маршрута")
            missions = self.missions_repository.filter_missions(
                missions,
                types=mission_types,
                districts=districts,
                level_range=level_range,
                building_types=building_types,
            )

        start_desc = "без начальной точки"
        if start_building:
            start_desc = f"от {start_building.name} ({start_building.district})"

        self._logger.debug(
            f"Построение маршрута {start_desc} для {len(missions)} миссий"
        )

        # Строим маршрут
        route = await self.missions_repository.build_missions_route(
            missions,
            start_building=start_building,
        )

        self._logger.info(f"Построен маршрут из {len(route)} миссий")
        return route
