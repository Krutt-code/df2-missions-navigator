from typing import Optional

from src.df2_missions.enums import BuildingType, District, MissionType
from src.df2_missions.parsers import DF2HavenMissionsParser, DF2ProfilerGamemapParser
from src.df2_missions.schemas import BuildingLocation, MapDF2, MapDF2Cell, Mission


class DF2Missions:
    """Миссии"""

    def __init__(self):
        self.parser_df2haven = DF2HavenMissionsParser()
        self.parser_df2profiler = DF2ProfilerGamemapParser()

    @staticmethod
    def missions_filter(
        missions: list[Mission],
        *,
        level_range: Optional[tuple[int, int]] = None,
        types: Optional[list[MissionType]] = None,
        districts: Optional[list[District]] = None,
        building_types: Optional[list[BuildingType]] = None,
    ) -> list[Mission]:
        """Фильтрация миссий по уровню, типу, району и типу здания"""
        if all(v is None for v in [level_range, types, districts, building_types]):
            return missions

        result_list = []

        for mission in missions:
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

        return result_list

    async def get_shortroute_missions(
        self,
        missions: list[Mission],
        *,
        start_building: Optional[BuildingLocation] = None,
        start_cell: Optional[MapDF2Cell] = None,
    ) -> dict[int, Mission]:
        """Оптимальный маршрут для выполнения миссий (жадный ближайший сосед).

        Возвращает словарь порядка обхода -> миссия. Если старт не задан, возвращает
        исходный порядок.
        """
        if start_building is None and start_cell is None:
            return {i: m for i, m in enumerate(missions)}

        if not missions:
            return {}

        # Карта нужна для нормализации координат и расчёта расстояний
        game_map: MapDF2 = await self.parser_df2profiler.get_map_data()

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
        remaining: list[tuple[int, Mission]] = list(enumerate(missions))
        route: list[Mission] = []

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

        return {i: m for i, m in enumerate(route)}

    async def get_df2profiler_map(self) -> MapDF2:
        return await self.parser_df2profiler.get_map_data()

    async def concat_missions(
        self, missions_df2haven: list[Mission], missions_df2profiler: list[Mission]
    ) -> list[Mission]:
        """Объединение миссий из разных источников в уникальный список.
        Ключ уникальности — тип + (заказчик | здание | описание). Дубликаты сливаются.
        """
        merged_by_identity: dict[tuple[str, str, str], Mission] = {}

        def upsert(m: Mission):
            key = m._base_identity()
            if key in merged_by_identity:
                merged_by_identity[key] = merged_by_identity[key].merge(m)
            else:
                merged_by_identity[key] = m

        for mission in missions_df2haven:
            upsert(mission)
        for mission in missions_df2profiler:
            upsert(mission)

        return list(merged_by_identity.values())

    async def get_missions(self) -> list[Mission]:
        missions_df2haven = await self.parser_df2haven.get_missions_list()
        missions_df2profiler = await self.parser_df2profiler.get_missions_list()

        return await self.concat_missions(missions_df2haven, missions_df2profiler)
