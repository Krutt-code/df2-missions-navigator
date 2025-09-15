from enum import StrEnum

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


class BuildingType(StrEnum):
    """Building Type Lookup"""

    HOS = "Hospital"
    POL = "Police"
    IND = "Industrial"
    HOT = "Hotel"
    HOU = "House"
    SHP = "Shop"
    RST = "Restaurant"
    APT = "Apartment"
    OFF = "Office"
    MAN = "Mansion"


class AvanpostType(StrEnum):
    """Avanpost Type Lookup"""

    DBPD = "Dallbow Police Department"
    HBH = "Haverbrook Memorial Hospital"
    GWHT1 = "Greywood Star Hotel"
