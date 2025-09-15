from bs4 import BeautifulSoup

from src.df2_missions.schemas import BuildingLocation, Mission, Person, Target


class Selectors:
    """Селекторы"""

    MISSIONS = "span[data-searchselected]"
    TARGET_TYPE = "strong"
    GIVER_LOOKUP = "span.giverLookup"


class MissionsExtractor:
    """Извлечение миссий из страницы"""

    SITE_URL = "https://df2profiler.com/gamemap/"
    _selectors = Selectors

    @staticmethod
    def extract_missions(soup: BeautifulSoup) -> list[Mission]:
        """Извлечение миссий из страницы"""

        def extract_target(mission: BeautifulSoup) -> Target:
            """Извлечение цели из миссии"""
            target_type = mission.select_one(
                MissionsExtractor._selectors.TARGET_TYPE
            ).text.strip()
            target_description = (
                mission.text.strip()
                .split("wants you to:")[1]
                .strip()
                .split("Building:")[0]
                .strip()
            )
            return Target(
                type=target_type,
                description=target_description,
            )

        def extract_building_location(mission: BeautifulSoup) -> BuildingLocation:
            """Извлечение локации здания из миссии"""
            building_name = mission.get("data-building")
            if building_name:
                building_location_district = mission.get("data-district")
                building_location_x = mission.get("data-xcoord", -1)
                building_location_y = mission.get("data-ycoord", -1)
                building_location_level = mission.get("data-level", 0)
                return BuildingLocation(
                    name=building_name,
                    district=building_location_district,
                    x=building_location_x,
                    y=building_location_y,
                    level=building_location_level,
                )
            return None

        def extract_customer(mission: BeautifulSoup) -> Person:
            """Извлечение клиента из миссии"""
            giver_lookup = mission.select_one(MissionsExtractor._selectors.GIVER_LOOKUP)
            person_building_name = giver_lookup.get("data-building")
            person_building_location_district = giver_lookup.get("data-giverdistrict")
            person_building_location_x = giver_lookup.get("data-xcoord", -1)
            person_building_location_y = giver_lookup.get("data-ycoord", -1)
            person_building_location_level = 0
            person_building_location = BuildingLocation(
                name=person_building_name,
                district=person_building_location_district,
                x=person_building_location_x,
                y=person_building_location_y,
                level=person_building_location_level,
            )
            person_name = giver_lookup.text.split("(")[0].strip().replace("\n", " ")
            return Person(
                name=person_name,
                location=person_building_location,
            )

        def extract_mission(mission: BeautifulSoup) -> Mission:
            """Извлечение миссии из страницы"""
            target = extract_target(mission)
            building_location = extract_building_location(mission)
            customer = extract_customer(mission)
            return Mission(
                target=target,
                building_location=building_location,
                customer=customer,
                site=MissionsExtractor.SITE_URL,
            )

        missions = soup.select(MissionsExtractor._selectors.MISSIONS)
        missions_list = []
        for mission in missions:
            if "wants you to:" not in mission.text.strip():
                continue

            missions_list.append(extract_mission(mission))

        return missions_list
