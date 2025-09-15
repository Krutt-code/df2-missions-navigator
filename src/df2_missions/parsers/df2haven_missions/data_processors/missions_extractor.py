from bs4 import BeautifulSoup

from src.df2_missions.schemas import BuildingLocation, Mission, Person, Target


class Selectors:
    """Селекторы"""

    MISSION_TABLE = "table#missions_table"
    MISSION_TABLE_HEADER = "thead tr"
    MISSION_TABLE_HEADER_CELLS = "th"
    MISSION_ROWS = "tbody tr"
    MISSION_CELLS = "td"
    MISSION_QUEST_WALKTHROUGH = ".guide-text"


class MissionsExtractor:
    """Извлечение миссий из страницы"""

    _selectors = Selectors
    SITE_URL = "https://df2haven.com/missions/"

    @staticmethod
    def extract_missions(soup: BeautifulSoup) -> list[Mission]:
        """Извлечение миссий из страницы"""

        def extract_header_names(header: BeautifulSoup) -> list[str]:
            """Извлечение заголовка таблицы"""
            return [
                th.text.strip() if th.text and not th.select_one("span") else None
                for th in header.select(
                    MissionsExtractor._selectors.MISSION_TABLE_HEADER_CELLS
                )
            ]

        def extract_target(mission_data: dict[str, str]) -> Target:
            """Извлечение цели из данных миссии"""

            target_name = mission_data.get("Mission Type")
            target_description = mission_data.get("Details")

            return Target(
                type=target_name,
                description=target_description,
            )

        def extract_location(mission_data: dict[str, str]) -> BuildingLocation:
            """Извлечение локации из данных миссии"""

            building_name = mission_data.get("Mission Building")
            district = mission_data.get("Mission City")

            return BuildingLocation(
                name=building_name,
                district=district,
            )

        def extract_customer(mission_data: dict[str, str]) -> Person:
            """Извлечение заказчика из данных миссии"""

            customer_name = mission_data.get("Giver Name")
            customer_building_name = mission_data.get("Giver Building")
            customer_district = mission_data.get("Giver City")
            customer_location = BuildingLocation(
                name=customer_building_name,
                district=customer_district,
            )
            customer_location_in_building = mission_data.get("Giver Location")

            return Person(
                name=customer_name,
                location=customer_location,
                location_in_building=customer_location_in_building,
            )

        def extract_mission(mission: BeautifulSoup, header_names: list[str]) -> Mission:
            """Извлечение миссии из страницы"""

            mission_data = {}
            mission_cells = mission.select(MissionsExtractor._selectors.MISSION_CELLS)
            for mission_cell, header_name in zip(mission_cells, header_names):
                if header_name:
                    mission_data[header_name] = mission_cell.text

            mission_id = mission.get("id")
            target = extract_target(mission_data)
            location = extract_location(mission_data)
            customer = extract_customer(mission_data)
            cash_reward = mission_data.get("Cash")
            exp_reward = mission_data.get("Exp")
            quest_walkthrough = mission.select_one(
                MissionsExtractor._selectors.MISSION_QUEST_WALKTHROUGH
            )
            quest_walkthrough = (
                quest_walkthrough.text.strip() if quest_walkthrough else None
            )

            return Mission(
                id=mission_id,
                target=target,
                building_location=location,
                customer=customer,
                cash_reward=cash_reward,
                exp_reward=exp_reward,
                quest_walkthrough=quest_walkthrough,
                site=MissionsExtractor.SITE_URL,
            )

        table = soup.select_one(MissionsExtractor._selectors.MISSION_TABLE)
        header = table.select_one(MissionsExtractor._selectors.MISSION_TABLE_HEADER)
        mission_rows = table.select(MissionsExtractor._selectors.MISSION_ROWS)

        header_names = extract_header_names(header)

        missions = [extract_mission(mission, header_names) for mission in mission_rows]
        return missions
