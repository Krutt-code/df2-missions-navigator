# from enum import StrEnum
from typing import Literal, Optional, get_args

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
DistrictLiteral = Literal[*DISTRICTS]


class BuildingLocation(BaseModel):
    """Локация здания"""

    name: str
    district: DistrictLiteral
    x: int
    y: int
    level: int
    building_type: Optional[str] = None

    @field_validator("district", mode="before")
    @classmethod
    def _validate_district(cls, v: str) -> DistrictLiteral:
        districts = get_args(DistrictLiteral)
        if v in districts:
            return v
        for district in districts:
            if v == district.replace(" ", ""):
                return district
        return v


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
MissionTypeLiteral = Literal[*MISSION_TYPES]


class Target(BaseModel):
    """Цель миссии"""

    type: MissionTypeLiteral
    description: str

    @field_validator("type", mode="before")
    @classmethod
    def _validate_type(cls, v: str) -> MissionTypeLiteral:
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
        aliases = {
            "Buy Item": "Bring Items",
            "Find Items": "Find Item",
            "Challenges": "Complete Challenges",
            "Complete Mission": "Complete Missions",
            "Locate / Contact Person": "Find Person",
            "Loot": "Loot Buildings",
            "Loot Search": "Loot Buildings",
            "Equip": "UNKNOWN",
        }
        return aliases.get(v, v)


class Person(BaseModel):
    """Персонаж"""

    name: str
    location: BuildingLocation
    location_in_building: Optional[str] = None


class Mission(BaseModel):
    """Миссия"""

    id: Optional[int] = None
    target: Target
    building_location: Optional[BuildingLocation] = None
    customer: Optional[Person] = None
    cash_reward: Optional[int] = None
    exp_reward: Optional[int] = None
    quest_walkthrough: Optional[str] = None


class MapDF2Cell(BaseModel):
    """Ячейка карты"""

    x: int
    y: int
    level: int
    buildings: list[BuildingLocation] = Field(default_factory=list)
    district: DistrictLiteral
    types: list[str] = Field(default_factory=list)

    @field_validator("district", mode="before")
    @classmethod
    def _validate_district(cls, v: str) -> DistrictLiteral:
        districts = get_args(DistrictLiteral)
        if v in districts:
            return v
        for district in districts:
            if v == district.replace(" ", ""):
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

    def add_cell(self, cell: MapDF2Cell):
        """Добавление ячейки в карту"""
        self.cells.append(cell)
