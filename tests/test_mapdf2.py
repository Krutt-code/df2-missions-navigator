import pytest

from src.df2_missions.enums import BuildingType, District
from src.df2_missions.schemas import BuildingLocation, MapDF2, MapDF2Cell


def make_cell(x: int, y: int, level: int, district: District, buildings: list[str]):
    cell = MapDF2Cell(x=x, y=y, level=level, district=district, types=["HOU"])  # any
    for b in buildings:
        cell.add_building(b)
    return cell


def test_map_size_empty():
    m = MapDF2()
    assert m.map_size == (0, 0)
    assert m.map_list == []


def test_get_buildings_by_coords_missing():
    m = MapDF2()
    assert m.get_buildings_by_coords(1, 1) == []


def test_get_cell_for_building_by_coords():
    m = MapDF2()
    cell = make_cell(4, 4, 1, District.RAVENWALL_HEIGHTS, ["Foo (HOU)"])
    m.add_cell(cell)

    found = m.get_cell_for_building(
        BuildingLocation(
            name="", district=District.RAVENWALL_HEIGHTS, x=4, y=4, level=1
        )
    )
    assert found is cell


def test_get_cell_for_building_by_name_and_district():
    m = MapDF2()
    cell1 = make_cell(2, 2, 1, District.LERWILLBURY, ["Payne Residence (HOU)"])
    cell2 = make_cell(3, 5, 1, District.LERWILLBURY, ["Payne Residence (HOU)"])
    m.add_cell(cell2)
    m.add_cell(cell1)

    # Должен выбрать детерминированно минимальный по (x,y) — cell1
    found = m.get_cell_for_building(
        BuildingLocation(name="Payne Residence", district=District.LERWILLBURY)
    )
    assert found is cell1


def test_building_type_normalization():
    bl1 = BuildingLocation(name="N", district=District.DALLBOW, building_type="HOU")
    assert bl1.building_type == BuildingType.HOU

    bl2 = BuildingLocation(name="N", district=District.DALLBOW, building_type="House")
    assert bl2.building_type == BuildingType.HOU

    bl3 = BuildingLocation(name="N", district=District.DALLBOW, building_type="XYZ")
    assert bl3.building_type == "XYZ"

    bl4 = BuildingLocation(name="N", district=District.DALLBOW, building_type=None)
    assert bl4.building_type is None


def test_indexation_flags_and_add_cell_invalidates():
    m = MapDF2()
    c1 = make_cell(1, 1, 1, District.DAWNHILL, ["A (HOU)"])
    m.add_cell(c1)
    # Первый доступ строит индексы
    _ = m.get_cell(1, 1)
    assert m.indexes_built is True

    # Повторный доступ не должен ломать флаг
    _ = m.get_cell(1, 1)
    assert m.indexes_built is True

    # Добавление новой ячейки инвалидирует индексы
    c2 = make_cell(2, 1, 1, District.DAWNHILL, ["B (HOU)"])
    m.add_cell(c2)
    assert m.indexes_built is False

    # Любой доступ снова их построит
    _ = m.get_cell(2, 1)
    assert m.indexes_built is True


def test_to_buildings_df_optional_pandas():
    m = MapDF2()
    c1 = make_cell(1, 1, 1, District.OVERWOOD, ["A (HOU)", "B (HOU)"])
    c2 = make_cell(2, 2, 1, District.OVERWOOD, ["C (HOU)"])
    m.add_cell(c1)
    m.add_cell(c2)

    df = m.to_buildings_df()
    assert len(df) == 3
    expected_cols = {
        "name",
        "district",
        "x",
        "y",
        "level",
        "building_type",
        "cell_types",
    }
    assert expected_cols.issubset(set(df.columns))
