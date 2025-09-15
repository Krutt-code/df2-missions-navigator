"""
Репозиторий для работы с миссиями.
"""

from typing import List, Optional, Tuple, Union

from src.df2_missions.enums import AvanpostType, BuildingType, District, MissionType
from src.df2_missions.interfaces import (
    GameMapDataSource,
    MissionsDataSource,
    MissionsRepository,
)
from src.df2_missions.schemas import BuildingLocation, MapDF2, MapDF2Cell, Mission
from src.utils.cache import cache_to_memory
from src.utils.logger import get_class_logger


class DF2MissionsRepository(MissionsRepository):
    """Репозиторий для работы с миссиями из разных источников данных"""

    def __init__(
        self,
        missions_sources: List[MissionsDataSource],
        map_source: GameMapDataSource,
    ):
        """
        Инициализация репозитория.

        Args:
            missions_sources: Список источников данных о миссиях
            map_source: Источник данных о карте игры
        """
        self.missions_sources = missions_sources
        self.map_source = map_source
        self._logger = get_class_logger(self)
        self._logger.info(
            f"Инициализирован репозиторий миссий с {len(missions_sources)} источниками"
        )

    async def get_all_missions(self) -> List[Mission]:
        """
        Получение всех миссий из всех источников с дедупликацией.

        Returns:
            Список уникальных миссий
        """
        self._logger.info("Получение всех миссий из всех источников")
        all_missions: List[List[Mission]] = []

        for source in self.missions_sources:
            self._logger.debug(
                f"Получение миссий из источника {source.__class__.__name__}"
            )
            missions = await source.get_missions_list()
            all_missions.append(missions)
            self._logger.debug(
                f"Получено {len(missions)} миссий из источника {source.__class__.__name__}"
            )

        # Объединяем миссии последовательно (попарно)
        result = []
        if all_missions:
            result = all_missions[0]
            for missions in all_missions[1:]:
                result = await self._concat_missions(result, missions)

        self._logger.info(
            f"Всего получено {len(result)} уникальных миссий после дедупликации"
        )
        return result

    async def normalize_missions_locations(
        self, missions: List[Mission]
    ) -> List[Mission]:
        """
        Нормализация координат зданий в миссиях.
        """
        game_map: MapDF2 = await self.get_map()

        for m in missions:
            if m.building_location is not None:
                m.building_location = game_map.normalize_coords(m.building_location)
        return missions

    def filter_missions(
        self,
        missions: List[Mission],
        *,
        level_range: Optional[Tuple[int, int]] = None,
        types: Optional[List[MissionType]] = None,
        districts: Optional[List[District]] = None,
        building_types: Optional[List[Union[BuildingType, AvanpostType]]] = None,
        has_customer: Optional[bool] = None,
        has_building: Optional[bool] = None,
        has_coordinates: Optional[bool] = None,
        has_quest_walkthrough: Optional[bool] = None,
    ) -> List[Mission]:
        """
        Фильтрация миссий по различным критериям.

        Args:
            missions: Список миссий для фильтрации
            level_range: Диапазон уровней (мин, макс)
            types: Список типов миссий
            districts: Список районов
            building_types: Список типов зданий
            has_customer: Фильтр по наличию заказчика
            has_building: Фильтр по наличию здания
            has_coordinates: Фильтр по наличию координат
            has_quest_walkthrough: Фильтр по наличию прохождения квеста

        Returns:
            Отфильтрованный список миссий
        """
        filter_params = []
        if level_range:
            filter_params.append(f"уровни {level_range[0]}-{level_range[1]}")
        if types:
            filter_params.append(f"типы {[t.value for t in types]}")
        if districts:
            filter_params.append(f"районы {[d.value for d in districts]}")
        if building_types:
            filter_params.append(f"типы зданий {[bt.value for bt in building_types]}")
        if has_customer is not None:
            filter_params.append("с заказчиком")
        if has_building is not None:
            filter_params.append("с зданием")
        if has_coordinates is not None:
            filter_params.append("с координатами")
        if has_quest_walkthrough is not None:
            filter_params.append("с прохождением квеста")

        filter_desc = ", ".join(filter_params) if filter_params else "без фильтров"
        self._logger.info(f"Фильтрация {len(missions)} миссий: {filter_desc}")

        if all(
            v is None
            for v in [
                level_range,
                types,
                districts,
                building_types,
                has_customer,
                has_building,
                has_coordinates,
                has_quest_walkthrough,
            ]
        ):
            return missions

        result_list = []

        for mission in missions:
            if has_customer is not None and getattr(mission, "customer", None) is (
                None if has_customer else not None
            ):
                continue
            if has_building is not None and getattr(
                mission, "building_location", None
            ) is (None if has_building else not None):
                continue
            if (
                has_coordinates
                and getattr(mission, "building_location", None) is None
                and getattr(mission.building_location, "x", None) is None
            ):
                continue
            if has_quest_walkthrough is not None and getattr(
                mission, "quest_walkthrough", None
            ) is (None if has_quest_walkthrough else not None):
                continue
            if (getattr(mission, "building_location", None)) and any(
                [
                    (
                        level_range
                        and getattr(mission.building_location, "level", None)
                        is not None
                        and (
                            mission.building_location.level < level_range[0]
                            or mission.building_location.level > level_range[1]
                        )
                    ),
                    (
                        districts
                        and getattr(mission.building_location, "district", None)
                        is not None
                        and mission.building_location.district not in districts
                    ),
                    (
                        building_types
                        and getattr(mission.building_location, "building_type", None)
                        is not None
                        and mission.building_location.building_type
                        not in building_types
                    ),
                ]
            ):
                continue
            if (types and hasattr(mission, "target")) and any(
                [mission.target.type is not None and mission.target.type not in types]
            ):
                continue
            result_list.append(mission)

        self._logger.info(f"Результат фильтрации: {len(result_list)} миссий")
        return result_list

    async def get_map(self) -> MapDF2:
        """
        Получение данных карты игры.

        Returns:
            Объект карты
        """
        self._logger.info("Получение данных карты игры")
        map_data = await self.map_source.get_map_data()
        self._logger.info(f"Получена карта с {len(map_data.cells)} ячейками")
        return map_data

    @cache_to_memory(ttl=600, namespace="missions_routes")  # 10 минут
    async def build_missions_route(
        self,
        missions: List[Mission],
        *,
        start_building: Optional[BuildingLocation] = None,
        start_cell: Optional[MapDF2Cell] = None,
    ) -> dict[int, Mission]:
        """
        Построение оптимального маршрута для выполнения миссий (жадный алгоритм ближайшего соседа).

        Args:
            missions: Список миссий
            start_building: Начальное здание
            start_cell: Начальная ячейка карты

        Returns:
            Словарь порядка обхода -> миссия
        """
        start_desc = ""
        if start_building:
            start_desc = f"от здания {start_building.name} в {start_building.district}"
        elif start_cell:
            start_desc = (
                f"от координат ({start_cell.x}, {start_cell.y}) в {start_cell.district}"
            )
        else:
            start_desc = "без указания начальной точки"

        self._logger.info(
            f"Построение маршрута для {len(missions)} миссий {start_desc}"
        )

        if start_building is None and start_cell is None:
            self._logger.debug(
                "Начальная точка не указана, возвращаем исходный порядок миссий"
            )
            return {i: m for i, m in enumerate(missions)}

        if not missions:
            self._logger.debug("Список миссий пуст, маршрут не требуется")
            return {}

        # Карта нужна для нормализации координат и расчёта расстояний
        game_map: MapDF2 = await self.get_map()

        def mission_location(m: Mission) -> Optional[BuildingLocation]:
            # Предпочитаем локацию здания, иначе место заказчика
            return m.building_location or (m.customer.location if m.customer else None)

        # Текущая точка старта
        if start_building is not None:
            current_loc: Optional[BuildingLocation] = start_building
        else:
            # Преобразуем клетку в "локацию" для расчётов
            current_loc = BuildingLocation(
                name="",
                district=start_cell.district,  # type: ignore[union-attr]
                x=start_cell.x,  # type: ignore[union-attr]
                y=start_cell.y,  # type: ignore[union-attr]
                level=start_cell.level,  # type: ignore[union-attr]
            )

        # Неизменяем список миссий вместе с их исходными индексами, чтобы при желании
        # можно было легко восстановить связь. На выходе же ключи — порядок обхода.
        remaining: List[Tuple[int, Mission]] = list(enumerate(missions))
        route: List[Mission] = []

        while remaining:
            # Выбираем следующую миссию с минимальным расстоянием от текущего положения.
            best_pos = 0
            best_dist_val = float("inf")

            for pos, (_, m) in enumerate(remaining):
                loc = mission_location(m)
                if loc is None:
                    dist = None
                else:
                    dist = game_map.distance_between(current_loc, loc)  # type: ignore[arg-type]
                # None -> считаем бесконечным расстоянием, чтобы такие миссии шли в конце
                val = dist if dist is not None else float("inf")
                if val < best_dist_val:
                    best_dist_val = val
                    best_pos = pos

            _, chosen = remaining.pop(best_pos)
            route.append(chosen)

            loc_info = ""
            if chosen.building_location:
                loc_info = f"{chosen.building_location.name} ({chosen.building_location.x}, {chosen.building_location.y})"
            self._logger.debug(
                f"Добавлена миссия к маршруту: {chosen.target.type.value} в {loc_info}, расстояние: {best_dist_val}"
            )

            # Обновляем текущую точку. Если можем сопоставить здание с клеткой —
            # фиксируемся на координатах клетки (в одной клетке может быть несколько зданий).
            next_loc = mission_location(chosen)
            if next_loc is not None:
                cell = game_map.get_cell_for_building(next_loc)
                if cell is not None:
                    current_loc = BuildingLocation(
                        name="",
                        district=cell.district,
                        x=cell.x,
                        y=cell.y,
                        level=cell.level,
                    )
                else:
                    current_loc = next_loc
            # Если локации нет, остаёмся в текущей точке (маршрут продолжится к ближайшим доступным)

        self._logger.info(f"Построен маршрут для {len(route)} миссий")
        return {i: m for i, m in enumerate(route)}

    @staticmethod
    async def _concat_missions(
        missions_a: List[Mission], missions_b: List[Mission]
    ) -> List[Mission]:
        """
        Объединение миссий из разных источников в уникальный список.
        Ключ уникальности — тип + (заказчик | здание | описание). Дубликаты сливаются.

        Args:
            missions_a: Первый список миссий
            missions_b: Второй список миссий

        Returns:
            Объединенный список уникальных миссий
        """
        merged_by_identity: dict[tuple[str, str, str], Mission] = {}

        def upsert(m: Mission):
            key = m._base_identity()
            if key in merged_by_identity:
                merged_by_identity[key] = merged_by_identity[key].merge(m)
            else:
                merged_by_identity[key] = m

        for mission in missions_a:
            upsert(mission)
        for mission in missions_b:
            upsert(mission)

        return list(merged_by_identity.values())
