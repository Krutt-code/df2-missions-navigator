import asyncio
from pprint import pprint

from src.df2_missions.parsers.df2profiler_gamemap import DF2ProfilerGamemapParser


async def main():
    parser = DF2ProfilerGamemapParser()
    # missions = await parser.get_missions_list()

    # for mission in missions:
    #     print(mission.model_dump_json(indent=4))

    map = await parser.map_data()
    pprint(map, indent=4)


if __name__ == "__main__":
    asyncio.run(main())
