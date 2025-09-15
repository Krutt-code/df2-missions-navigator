from unittest.mock import AsyncMock, MagicMock, patch

from src.df2_missions.missions import DF2Missions
from src.df2_missions.schemas import (
    BuildingLocation,
    District,
    MapDF2,
    MapDF2Cell,
    Mission,
    MissionType,
    Person,
    Target,
)


def test_missions_filter():
    missions = [
        Mission(
            target=Target(
                type=MissionType.FIND_ITEM,
                description="test",
            ),
            building_location=BuildingLocation(
                district=District.ALBANDALE_PARK,
                name="test",
            ),
        ),
    ]
    filtered_missions = DF2Missions.missions_filter(
        missions, types=[MissionType.FIND_ITEM]
    )
    assert len(filtered_missions) == 1
    assert filtered_missions[0].target.type == MissionType.FIND_ITEM
    assert filtered_missions[0].building_location.district == District.ALBANDALE_PARK


def test_missions_filter_multiple_conditions():
    """Тест фильтрации миссий по нескольким условиям"""
    missions = [
        # Соответствует всем фильтрам
        Mission(
            target=Target(
                type=MissionType.FIND_ITEM, description="Find item in level 5"
            ),
            building_location=BuildingLocation(
                name="Building 1",
                district=District.ALBANDALE_PARK,
                level=5,
            ),
        ),
        # Не соответствует типу
        Mission(
            target=Target(type=MissionType.KILL_BOSS, description="Kill boss"),
            building_location=BuildingLocation(
                name="Building 2",
                district=District.ALBANDALE_PARK,
                level=5,
            ),
        ),
        # Не соответствует району
        Mission(
            target=Target(type=MissionType.FIND_ITEM, description="Find in Dallbow"),
            building_location=BuildingLocation(
                name="Building 3",
                district=District.DALLBOW,
                level=5,
            ),
        ),
        # Не соответствует уровню
        Mission(
            target=Target(type=MissionType.FIND_ITEM, description="Find in high level"),
            building_location=BuildingLocation(
                name="Building 4",
                district=District.ALBANDALE_PARK,
                level=20,
            ),
        ),
    ]

    filtered_missions = DF2Missions.missions_filter(
        missions,
        types=[MissionType.FIND_ITEM],
        districts=[District.ALBANDALE_PARK],
        level_range=(1, 10),
    )

    assert len(filtered_missions) == 1
    assert filtered_missions[0].building_location.name == "Building 1"


@patch("src.df2_missions.missions.DF2Missions.parser_df2haven", new_callable=AsyncMock)
@patch(
    "src.df2_missions.missions.DF2Missions.parser_df2profiler", new_callable=AsyncMock
)
async def test_get_missions(mock_profiler, mock_haven):
    """Тест получения и объединения миссий из разных источников"""
    # Подготовка тестовых данных
    missions_haven = [
        Mission(
            id="1",
            target=Target(type=MissionType.FIND_ITEM, description="Find item A"),
            building_location=BuildingLocation(
                name="Building A",
                district=District.DALLBOW,
            ),
            site="df2haven.com",
        ),
    ]

    missions_profiler = [
        Mission(
            target=Target(
                type=MissionType.FIND_ITEM, description="Find item A (more details)"
            ),
            building_location=BuildingLocation(
                name="Building A",
                district=District.DALLBOW,
                x=5,
                y=5,
                level=10,
            ),
            site="df2profiler.com",
        ),
        Mission(
            target=Target(type=MissionType.KILL_BOSS, description="Kill boss B"),
            building_location=BuildingLocation(
                name="Building B",
                district=District.LERWILLBURY,
            ),
            site="df2profiler.com",
        ),
    ]

    # Настройка моков
    mock_haven.get_missions_list.return_value = missions_haven
    mock_profiler.get_missions_list.return_value = missions_profiler

    # Выполнение тестируемой функции
    df2_missions = DF2Missions()
    result = await df2_missions.get_missions()

    # Проверки
    assert len(result) == 2  # Должно быть две уникальные миссии

    # Проверяем слияние миссии с одинаковым ключом идентичности
    find_mission = next(m for m in result if m.target.type == MissionType.FIND_ITEM)
    assert find_mission.id == "1"  # ID из df2haven сохранен
    assert (
        "more details" in find_mission.target.description
    )  # Описание из df2profiler предпочтено
    assert find_mission.building_location.x == 5  # Координаты из df2profiler добавлены


async def test_concat_missions():
    """Тест объединения миссий из разных источников"""
    df2_missions = DF2Missions()

    # Миссии с одинаковым ключом идентичности (тип + локация)
    mission1 = Mission(
        id="1",
        target=Target(type=MissionType.FIND_ITEM, description="Short description"),
        building_location=BuildingLocation(
            name="Target Building",
            district=District.OVERWOOD,
        ),
        customer=Person(
            name="John",
            location=BuildingLocation(
                name="Customer Building",
                district=District.DALLBOW,
            ),
        ),
        cash_reward=100,
    )

    mission2 = Mission(
        target=Target(
            type=MissionType.FIND_ITEM,
            description="Detailed description with more info",
        ),
        building_location=BuildingLocation(
            name="Target Building",
            district=District.OVERWOOD,
            x=10,
            y=15,
            level=5,
        ),
        exp_reward=200,
    )

    # Миссия с другим ключом идентичности
    mission3 = Mission(
        target=Target(type=MissionType.KILL_BOSS, description="Kill boss"),
        building_location=BuildingLocation(
            name="Boss Building",
            district=District.LERWILLBURY,
        ),
    )

    # Объединяем миссии
    result = await df2_missions.concat_missions([mission1], [mission2, mission3])

    # Проверки
    assert len(result) == 2  # Должно быть две уникальные миссии

    # Находим объединенную миссию
    merged_mission = next(m for m in result if m.target.type == MissionType.FIND_ITEM)

    # Проверяем, что данные корректно объединены
    assert merged_mission.id == "1"  # ID из первой миссии
    assert (
        "Detailed description" in merged_mission.target.description
    )  # Предпочтено более длинное описание
    assert merged_mission.building_location.x == 10  # Координаты из второй миссии
    assert merged_mission.building_location.level == 5  # Уровень из второй миссии
    assert merged_mission.cash_reward == 100  # Награда из первой миссии
    assert merged_mission.exp_reward == 200  # Опыт из второй миссии
    assert merged_mission.customer.name == "John"  # Заказчик из первой миссии


@patch(
    "src.df2_missions.missions.DF2Missions.parser_df2profiler", new_callable=MagicMock
)
async def test_get_shortroute_missions(mock_profiler):
    """Тест построения оптимального маршрута"""
    df2_missions = DF2Missions()

    # Создаем тестовую карту
    test_map = MapDF2()

    # Добавляем ячейки в карту
    cell1 = MapDF2Cell(x=1, y=1, level=1, district=District.DALLBOW, types=["HOU"])
    cell1.add_building("Building A (HOU)")

    cell2 = MapDF2Cell(x=2, y=2, level=1, district=District.DALLBOW, types=["HOU"])
    cell2.add_building("Building B (HOU)")

    cell3 = MapDF2Cell(x=4, y=4, level=1, district=District.DALLBOW, types=["HOU"])
    cell3.add_building("Building C (HOU)")

    test_map.add_cell(cell1)
    test_map.add_cell(cell2)
    test_map.add_cell(cell3)

    # Настраиваем мок для возврата тестовой карты
    mock_profiler.get_map_data.return_value = test_map

    # Создаем тестовые миссии
    mission1 = Mission(
        target=Target(type=MissionType.FIND_ITEM, description="Find in A"),
        building_location=BuildingLocation(
            name="Building A",
            district=District.DALLBOW,
            x=1,
            y=1,
        ),
    )

    mission2 = Mission(
        target=Target(type=MissionType.FIND_ITEM, description="Find in B"),
        building_location=BuildingLocation(
            name="Building B",
            district=District.DALLBOW,
            x=2,
            y=2,
        ),
    )

    mission3 = Mission(
        target=Target(type=MissionType.FIND_ITEM, description="Find in C"),
        building_location=BuildingLocation(
            name="Building C",
            district=District.DALLBOW,
            x=4,
            y=4,
        ),
    )

    # Устанавливаем начальную точку
    start_building = BuildingLocation(
        name="Start",
        district=District.DALLBOW,
        x=3,
        y=3,
        level=1,
    )

    # Получаем оптимальный маршрут
    route = await df2_missions.get_shortroute_missions(
        [mission1, mission2, mission3], start_building=start_building
    )

    # Проверяем порядок маршрута (ближайший сосед)
    assert list(route.keys()) == [0, 1, 2]

    # Первой должна быть миссия в здании B (ближайшая к старту)
    assert route[0].building_location.name == "Building B"

    # Второй должна быть миссия в здании A (ближайшая к B)
    assert route[1].building_location.name == "Building A"

    # Третьей должна быть миссия в здании C (последняя)
    assert route[2].building_location.name == "Building C"
