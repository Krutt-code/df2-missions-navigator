from src.df2_missions.parsers import DF2HavenMissionsParser, DF2ProfilerGamemapParser
from src.df2_missions.schemas import MapDF2, Mission


class DF2Missions:
    """Миссии"""

    def __init__(self):
        self.parser_df2haven = DF2HavenMissionsParser()
        self.parser_df2profiler = DF2ProfilerGamemapParser()

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
