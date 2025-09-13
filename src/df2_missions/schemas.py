from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

"""
Нужно оставить только уникальные типы миссий.

Bring Items
Find Item
Sell Item
Collect Items
Find Person
Kill Boss
Kill Infected
Exterminate
Loot Buildings
Talk to NPC
Clear Escape
Complete Challenges
Complete Missions
Escape Stalker
Scrap
UNKNOWN

Buy Item                -> Bring Items
Find Items              -> Find Item
Challenges              -> Complete Challenges
Complete Mission        -> Complete Missions
Locate / Contact Person -> Find Person
Loot                    -> Loot Buildings
Loot Search             -> Loot Buildings
Equip                   -> UNKNOWN
"""

DISTRICTS = (
    "Ravenwall Heights",
    "Albandale Park",
    "Overwood",
    "Greywood",
    "Lerwillbury",
    "Dallbow",
    "Coopertown",
    "Richbow Hunt",
    "Duntsville",
    "Archbrook",
    "West Moledale",
    "Dawnhill",
    "Haverbrook",
    "South Moorhurst",
    "Wolfstable",
)


class District(StrEnum):
    RAVENWALL_HEIGHTS = "Ravenwall Heights"
    ALBANDALE_PARK = "Albandale Park"
    OVERWOOD = "Overwood"
    GREYWOOD = "Greywood"
    LERWILLBURY = "Lerwillbury"
    DALLBOW = "Dallbow"
    COOPERTOWN = "Coopertown"
    RICHBOW_HUNT = "Richbow Hunt"
    DUNTSVILLE = "Duntsville"
    ARCHBROOK = "Archbrook"
    WEST_MOLEDALE = "West Moledale"
    DAWNHILL = "Dawnhill"
    HAVERBROOK = "Haverbrook"
    SOUTH_MOORHURST = "South Moorhurst"
    WOLFSTABLE = "Wolfstable"


class BuildingLocation(BaseModel):
    """Локация здания"""

    name: str
    district: District
    x: Optional[int] = None
    y: Optional[int] = None
    level: Optional[int] = None
    building_type: Optional[str] = None

    @field_validator("district", mode="before")
    @classmethod
    def _validate_district(cls, v: object) -> object:
        if isinstance(v, District):
            return v
        if isinstance(v, str):
            # точное совпадение или без пробелов
            for district in District:
                if v == district.value or v == district.value.replace(" ", ""):
                    return district
        return v

    def merge(self, other: Optional["BuildingLocation"]) -> "BuildingLocation":
        """Соединение локаций. Берем непустые поля, координаты/уровень приоритетно с числовыми значениями."""
        if other is None:
            return self
        return BuildingLocation(
            name=other.name or self.name,
            district=other.district or self.district,
            x=other.x if other.x not in (None, -1) else self.x,
            y=other.y if other.y not in (None, -1) else self.y,
            level=other.level if other.level not in (None, -1) else self.level,
            building_type=other.building_type or self.building_type,
        )

    def __str__(self) -> str:
        district_str = (
            self.district.value
            if isinstance(self.district, District)
            else str(self.district)
        )
        return f"{self.name}, {district_str}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BuildingLocation):
            return False
        return self.__str__() == other.__str__()


MISSION_TYPES = (
    "Bring Items",
    "Find Item",
    "Sell Item",
    "Collect Items",
    "Find Person",
    "Kill Boss",
    "Kill Infected",
    "Exterminate",
    "Loot Buildings",
    "Talk to NPC",
    "Clear Escape",
    "Complete Challenges",
    "Complete Missions",
    "Escape Stalker",
    "Scrap",
    "UNKNOWN",
)


class MissionType(StrEnum):
    BRING_ITEMS = "Bring Items"
    FIND_ITEM = "Find Item"
    SELL_ITEM = "Sell Item"
    COLLECT_ITEMS = "Collect Items"
    FIND_PERSON = "Find Person"
    KILL_BOSS = "Kill Boss"
    KILL_INFECTED = "Kill Infected"
    EXTERMINATE = "Exterminate"
    LOOT_BUILDINGS = "Loot Buildings"
    TALK_TO_NPC = "Talk to NPC"
    CLEAR_ESCAPE = "Clear Escape"
    COMPLETE_CHALLENGES = "Complete Challenges"
    COMPLETE_MISSIONS = "Complete Missions"
    ESCAPE_STALKER = "Escape Stalker"
    SCRAP = "Scrap"
    UNKNOWN = "UNKNOWN"


class Target(BaseModel):
    """Цель миссии"""

    type: MissionType
    description: str

    @field_validator("type", mode="before")
    @classmethod
    def _validate_type(cls, v: object) -> object:
        """
        Buy Item                -> Bring Items
        Find Items              -> Find Item
        Challenges              -> Complete Challenges
        Complete Mission        -> Complete Missions
        Locate / Contact Person -> Find Person
        Loot                    -> Loot Buildings
        Loot Search             -> Loot Buildings
        Equip                   -> UNKNOWN
        """
        if isinstance(v, MissionType):
            return v
        if isinstance(v, str):
            aliases: dict[str, MissionType] = {
                "Buy Item": MissionType.BRING_ITEMS,
                "Find Items": MissionType.FIND_ITEM,
                "Challenges": MissionType.COMPLETE_CHALLENGES,
                "Complete Mission": MissionType.COMPLETE_MISSIONS,
                "Locate / Contact Person": MissionType.FIND_PERSON,
                "Loot": MissionType.LOOT_BUILDINGS,
                "Loot Search": MissionType.LOOT_BUILDINGS,
                "Equip": MissionType.UNKNOWN,
            }
            return aliases.get(v, v)
        return v

    def merge(self, other: Optional["Target"]) -> "Target":
        """Соединение целей: тип одинаковый, описание выбираем самое информативное (длиннее)."""
        if other is None:
            return self
        best_description = self.description or ""
        if other.description and len(other.description) > len(best_description):
            best_description = other.description
        return Target(type=self.type or other.type, description=best_description)


class Person(BaseModel):
    """Персонаж"""

    name: str
    location: BuildingLocation
    location_in_building: Optional[str] = None

    def merge(self, other: Optional["Person"]) -> "Person":
        """Соединение данных персонажа."""
        if other is None:
            return self
        best_name = other.name or self.name
        merged_location = (
            self.location.merge(other.location) if other.location else self.location
        )
        best_location_in_building = (
            other.location_in_building or self.location_in_building
        )
        return Person(
            name=best_name,
            location=merged_location,
            location_in_building=best_location_in_building,
        )


class Mission(BaseModel):
    """Миссия"""

    id: Optional[str] = None
    target: Target
    building_location: Optional[BuildingLocation] = None
    customer: Optional[Person] = None
    cash_reward: Optional[int] = None
    exp_reward: Optional[int] = None
    quest_walkthrough: Optional[str] = None
    site: Optional[str] = None

    @staticmethod
    def _normalize_text(value: Optional[str]) -> str:
        if value is None:
            return ""
        value = value.strip().lower()
        value = " ".join(value.split())
        return value

    def _person_key(self) -> Optional[str]:
        if not self.customer:
            return None
        name = Mission._normalize_text(self.customer.name)
        district_value = (
            self.customer.location.district.value
            if self.customer.location
            and isinstance(self.customer.location.district, District)
            else None
        )
        return f"{name}|{district_value or ''}"

    def _building_key(self) -> Optional[str]:
        if not self.building_location:
            return None
        name = Mission._normalize_text(self.building_location.name)
        district_value = (
            self.building_location.district.value
            if isinstance(self.building_location.district, District)
            else str(self.building_location.district)
        )
        return f"{name}|{district_value or ''}"

    def _base_identity(self) -> tuple[str, str, str]:
        """Идентичность миссии для сравнения и дедупликации.
        Приоритет:
        1) тип + заказчик (имя + район)
        2) тип + здание (имя + район)
        3) тип + нормализованное описание
        """
        mission_type = (
            self.target.type.value
            if isinstance(self.target.type, MissionType)
            else str(self.target.type)
        )
        person_key = self._person_key()
        if person_key:
            return (mission_type, "C", person_key)
        building_key = self._building_key()
        if building_key:
            return (mission_type, "B", building_key)
        return (mission_type, "D", Mission._normalize_text(self.target.description))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Mission):
            return False
        # Если есть одинаковый id
        if self.id and other.id and self.id == other.id:
            return True
        return self._base_identity() == other._base_identity()

    def __hash__(self) -> int:
        return hash(self._base_identity())

    @staticmethod
    def _looks_like_profiler(m: "Mission") -> bool:
        """Эвристика для определения источника df2profiler"""
        if m.site:
            return "df2profiler" in m.site.lower()
        return False

    def merge(self, other: Optional["Mission"]) -> "Mission":
        """Соединение миссий, заполняя все пустые места из другой миссии.
        Описание цели по возможности берем из df2profiler.
        """
        if other is None:
            return self
        # Цель: тип — любой ненулевой, описание — предпочитаем df2profiler
        self_is_prof = Mission._looks_like_profiler(self)
        other_is_prof = Mission._looks_like_profiler(other)
        if other_is_prof and other.target and other.target.description:
            best_desc = other.target.description
        elif self_is_prof and self.target and self.target.description:
            best_desc = self.target.description
        else:
            self_desc = self.target.description if self.target else None
            other_desc = other.target.description if other.target else None
            if other_desc and (not self_desc or len(other_desc) > len(self_desc)):
                best_desc = other_desc
            else:
                best_desc = self_desc
        merged_target = Target(
            type=(
                self.target.type
                if self.target and self.target.type
                else other.target.type
            ),
            description=best_desc or "",
        )
        # Локация здания
        if self.building_location and other.building_location:
            merged_building_location = self.building_location.merge(
                other.building_location
            )
        else:
            merged_building_location = self.building_location or other.building_location
        # Заказчик
        if self.customer and other.customer:
            merged_customer = self.customer.merge(other.customer)
        else:
            merged_customer = self.customer or other.customer
        # Вознаграждения и прохождение
        merged_cash = (
            other.cash_reward
            if other.cash_reward not in (None, 0)
            else self.cash_reward
        )
        merged_exp = (
            other.exp_reward if other.exp_reward not in (None, 0) else self.exp_reward
        )
        merged_walkthrough = (
            self.quest_walkthrough
            if len(self.quest_walkthrough or "") > len(other.quest_walkthrough or "")
            else other.quest_walkthrough
        )
        # id оставляем, если уже есть, иначе берем из другой
        merged_id = self.id or other.id
        merged_site = self.site or other.site
        return Mission(
            id=merged_id,
            target=merged_target,
            building_location=merged_building_location,
            customer=merged_customer,
            cash_reward=merged_cash,
            exp_reward=merged_exp,
            quest_walkthrough=merged_walkthrough,
            site=merged_site,
        )


class MapDF2Cell(BaseModel):
    """Ячейка карты"""

    x: int
    y: int
    level: int
    buildings: list[BuildingLocation] = Field(default_factory=list)
    district: District
    types: list[str] = Field(default_factory=list)

    @field_validator("district", mode="before")
    @classmethod
    def _validate_district(cls, v: object) -> object:
        if isinstance(v, District):
            return v
        if isinstance(v, str):
            for district in District:
                if v == district.value or v == district.value.replace(" ", ""):
                    return district
        return v

    def add_building(self, building_name: str):
        """Добавление здания в ячейку"""
        if "(" in building_name:
            building_type = building_name.split("(")[1].split(")")[0].strip()
        else:
            building_type = None
        building_name = building_name.split("(")[0].strip()
        self.buildings.append(
            BuildingLocation(
                name=building_name,
                district=self.district,
                x=self.x,
                y=self.y,
                level=self.level,
                building_type=building_type,
            )
        )


class MapDF2(BaseModel):
    """Карта"""

    cells: list[MapDF2Cell] = Field(default_factory=list)

    @property
    def building_name_to_cell(self) -> dict[str, MapDF2Cell]:
        """Все здания на карте, сгруппированные по имени и квадрату"""
        buildings = {}
        for cell in self.cells:
            for building in cell.buildings:
                buildings[building.__str__()] = cell
        return buildings

    @property
    def map_size(self) -> tuple[int, int]:
        """Размер карты
        Возвращает (x, y)
        """
        return (
            max(cell.x for cell in self.cells),
            max(cell.y for cell in self.cells),
        )

    @property
    def map_list(self) -> list[list[MapDF2Cell]]:
        """Список ячеек карты [x][y]"""
        map_list = [[None] * self.map_size[1] for _ in range(self.map_size[0])]
        for cell in self.cells:
            map_list[cell.x - 1][cell.y - 1] = cell
        return map_list

    def get_buildings_by_coords(self, x: int, y: int) -> list[BuildingLocation]:
        """Здания в ячейке"""
        cell = self.map_list[x - 1][y - 1]
        return cell.buildings or []

    def add_cell(self, cell: MapDF2Cell):
        """Добавление ячейки в карту"""
        self.cells.append(cell)

    def get_cell_for_building(self, building: BuildingLocation) -> Optional[MapDF2Cell]:
        """Найти ячейку карты по локации здания.

        Алгоритм:
        1) Если заданы координаты (x, y, level) — ищем точное совпадение ячейки.
        2) Иначе ищем по имени здания и району в списках зданий ячеек.
        """
        # Попытка точного совпадения по координатам/уровню/району
        if all([_ not in (None, -1) for _ in [building.x, building.y, building.level]]):
            return self.get_buildings_by_coords(building.x, building.y)
        # Поиск по имени здания и району
        building_key = building.__str__()
        return self.building_name_to_cell.get(building_key)

    def distance_between(
        self, a: BuildingLocation, b: BuildingLocation
    ) -> Optional[int]:
        """Манхэттенское расстояние между двумя зданиями.

        Если у здания отсутствуют координаты, выполняется попытка определить их
        через соответствующую ячейку карты (см. get_cell_for_building).
        Возвращает None, если определить координаты не удалось.
        """

        def get_coords(loc: BuildingLocation) -> Optional[tuple[int, int]]:
            if loc.x not in (None, -1) and loc.y not in (None, -1):
                return loc.x, loc.y
            cell = self.get_cell_for_building(loc)
            if cell is None:
                return None
            return cell.x, cell.y

        coords_a = get_coords(a)
        coords_b = get_coords(b)
        if coords_a is None or coords_b is None:
            return None
        ax, ay = coords_a
        bx, by = coords_b
        return abs(ax - bx) + abs(ay - by)
