from bs4 import BeautifulSoup as BS

from src.df2_missions.schemas import MapDF2, MapDF2Cell


class Selectors:
    """Селекторы для извлечения данных карты с сайта"""

    CARD_DATA = "table#map"
    MAP_TABLE_ROW = "tr"
    MAP_TABLE_CELL = "td"


class CardExtractor:
    """Извлечение карты из страницы"""

    _selectors = Selectors

    @staticmethod
    def extract_card_data(soup: BS) -> dict:
        """Извлечение данных карты с сайта"""

        def extract_map_rows(map_table: BS) -> list[BS]:
            """Извлечение строк карты"""
            return map_table.select("tr")

        def extract_map_cells(map_row: BS) -> list[BS]:
            """Извлечение ячеек карты"""
            return map_row.select(CardExtractor._selectors.MAP_TABLE_CELL)

        def extract_cell_data(map_cell: BS) -> MapDF2Cell:
            """Извлечение данных ячейки карты"""

            cell = MapDF2Cell(
                x=map_cell.get("data-xcoord"),
                y=map_cell.get("data-ycoord"),
                level=map_cell.get("data-level"),
                district=map_cell.get("data-district"),
                types=map_cell.get("data-types").split(","),
            )

            buildings = map_cell.get("data-buildings").split(",")
            for building in buildings:
                cell.add_building(building.strip())

            return cell

        map = MapDF2()

        map_table = soup.select_one(CardExtractor._selectors.CARD_DATA)
        map_rows = extract_map_rows(map_table)
        for map_row in map_rows:
            map_cells = extract_map_cells(map_row)
            for map_cell in map_cells:
                cell = extract_cell_data(map_cell)
                map.add_cell(cell)

        return map
