import asyncio
from pprint import pprint

from src.df2_missions.missions import DF2Missions
from src.df2_missions.schemas import BuildingLocation


async def main():
    df2_missions = DF2Missions()
    map = await df2_missions.get_df2profiler_map()

    pprint(map.get_buildings_by_coords(4, 4), indent=4)
    pprint(
        map.get_cell_for_building(
            BuildingLocation(name="", district="Ravenwall Heights", x=4, y=4, level=1)
        ),
        indent=4,
    )
    pprint(
        map.get_cell_for_building(
            BuildingLocation(
                name="Payne Residence",
                district="Lerwillbury",
            )
        ),
        indent=4,
    )


if __name__ == "__main__":
    asyncio.run(main())
