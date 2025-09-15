from typing import Optional, Union

import pandas as pd
from pydantic import BaseModel, Field, field_validator

from src.df2_missions.enums import AvanpostType, BuildingType, District, MissionType


def _to_building_enum(value: object) -> object:
    """Приведение типа здания к Enum по коду (NAME) или по значению ("Label").
    Неизвестные значения возвращаются как исходная строка или None.
    """
    if value is None:
        return None
    if isinstance(value, (BuildingType, AvanpostType)):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        code = s.upper()
        # По имени (коду) ENUM
        for enum_cls in (BuildingType, AvanpostType):
            try:
                return enum_cls[code]
            except KeyError:
                pass
        # По значению (label)
        for enum_cls in (BuildingType, AvanpostType):
            for member in enum_cls:
                if s == member.value:
                    return member
        # Неизвестное значение оставляем строкой
        return s
    return value


class BuildingLocation(BaseModel):
    """Локация здания"""

    name: str
    district: District
    x: Optional[int] = None
    y: Optional[int] = None
    level: Optional[int] = None
    building_type: Optional[Union[BuildingType, AvanpostType, str]] = None

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

    @field_validator("building_type", mode="before")
    @classmethod
    def _validate_building_type(cls, v: object) -> object:
        return _to_building_enum(v)

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
    types: list[Union[BuildingType, AvanpostType, str]] = Field(default_factory=list)

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

    @field_validator("types", mode="before")
    @classmethod
    def _validate_types(cls, v: object) -> object:
        if v is None:
            return []
        if isinstance(v, list):
            return [_to_building_enum(i) for i in v if i not in (None, "")]
        if isinstance(v, str):
            items = [i.strip() for i in v.split(",")]
            return [_to_building_enum(i) for i in items if i]
        return [_to_building_enum(v)]

    def add_building(self, building_name: str):
        """Добавление здания в ячейку. Формат источника: "Name (TYPE)".
        TYPE маппится к Enum по коду (NAME) или по значению. Неизвестные значения сохраняются как строка.
        """
        raw = building_name.strip()
        if "(" in raw and ")" in raw and raw.rfind("(") < raw.rfind(")"):
            type_part = raw.split("(")[-1].split(")")[0].strip()
        else:
            type_part = None
        name_part = raw.split("(")[0].strip()
        norm_type = _to_building_enum(type_part) if type_part else None
        self.buildings.append(
            BuildingLocation(
                name=name_part,
                district=self.district,
                x=self.x,
                y=self.y,
                level=self.level,
                building_type=norm_type,
            )
        )


class MapDF2(BaseModel):
    """Карта DF2.

    Оси координат 1-based. Предоставляет O(1) доступ к ячейкам по координатам и по (name, district)
    через ленивые индексы с инвалидацией при модификациях.
    """

    cells: list[MapDF2Cell] = Field(default_factory=list)

    # Ленивая индексация (служебные поля не сериализуются)
    idx_coords_to_cell: dict[tuple[int, int], MapDF2Cell] = Field(
        default_factory=dict, exclude=True
    )
    idx_name_district_to_cells: dict[tuple[str, str], list[MapDF2Cell]] = Field(
        default_factory=dict, exclude=True
    )
    max_x: int = Field(default=0, exclude=True)
    max_y: int = Field(default=0, exclude=True)
    indexes_built: bool = Field(default=False, exclude=True)

    # Константы

    MAP_X_COORD_TO_LEVEL: dict[int, int] = {
        **{i: 1 for i in range(1, 6)},
        **{i: 5 for i in range(6, 8)},
        **{i: 10 for i in range(8, 10)},
        **{i: 15 for i in range(10, 13)},
        **{i: 20 for i in range(13, 15)},
        **{i: 25 for i in range(15, 17)},
        **{i: 30 for i in range(17, 19)},
        **{i: 35 for i in range(19, 22)},
        **{i: 40 for i in range(22, 24)},
        **{i: 45 for i in range(24, 26)},
        **{i: 50 for i in range(26, 31)},
    }

    # ───── Индексация ─────
    @staticmethod
    def _normalize_name(value: str) -> str:
        return " ".join((value or "").strip().lower().split())

    @staticmethod
    def _district_value(d: Union[District, str]) -> str:
        return d.value if isinstance(d, District) else str(d)

    def _touch(self) -> None:
        self.indexes_built = False

    def _ensure_indexes(self) -> None:
        if self.indexes_built:
            return
        self.idx_coords_to_cell.clear()
        self.idx_name_district_to_cells.clear()
        self.max_x = 0
        self.max_y = 0
        for cell in self.cells:
            # Координаты
            self.idx_coords_to_cell[(cell.x, cell.y)] = cell
            if cell.x > self.max_x:
                self.max_x = cell.x
            if cell.y > self.max_y:
                self.max_y = cell.y
            # Индекс по (name, district)
            for b in cell.buildings:
                key = (self._normalize_name(b.name), self._district_value(b.district))
                self.idx_name_district_to_cells.setdefault(key, []).append(cell)
            # Если здание отсутствует, индекс по district не пополняем
        # Детализация порядка выборки: сортируем списки по (x, y)
        for key, lst in self.idx_name_district_to_cells.items():
            lst.sort(key=lambda c: (c.x, c.y))
        self.indexes_built = True

    # ───── Базовые свойства ─────
    @property
    def building_name_to_cell(self) -> dict[str, MapDF2Cell]:
        """Сопоставление "Name, District" -> MapDF2Cell.
        При наличии дубликатов в пределах района выбирается детерминированно первая
        ячейка по минимуму (x, y). Для работы использует внутренний индекс.
        """
        self._ensure_indexes()
        result: dict[str, MapDF2Cell] = {}
        for cell in self.cells:
            district_str = self._district_value(cell.district)
            for b in cell.buildings:
                key_str = f"{b.name}, {district_str}"
                # Берём минимальную по (x,y)
                current = result.get(key_str)
                if current is None or (cell.x, cell.y) < (current.x, current.y):
                    result[key_str] = cell
        return result

    @property
    def building_name_to_cells(self) -> dict[str, list[MapDF2Cell]]:
        """Сопоставление "Name, District" -> список ячеек с таким зданием в районе.
        Порядок детерминирован: отсортировано по (x, y).
        """
        self._ensure_indexes()
        result: dict[str, list[MapDF2Cell]] = {}
        for cell in self.cells:
            district_str = self._district_value(cell.district)
            for b in cell.buildings:
                key_str = f"{b.name}, {district_str}"
                result.setdefault(key_str, []).append(cell)
        for key in result:
            # удаляем дубликаты, сортируем
            uniq = {(c.x, c.y): c for c in result[key]}
            result[key] = sorted(uniq.values(), key=lambda c: (c.x, c.y))
        return result

    @property
    def map_size(self) -> tuple[int, int]:
        """Размер карты (x, y). Для пустой карты возвращает (0, 0).
        Оси координат 1-based.
        """
        if not self.cells:
            return (0, 0)
        self._ensure_indexes()
        return (self.max_x, self.max_y)

    @property
    def map_list(self) -> list[list[Optional[MapDF2Cell]]]:
        """Список ячеек карты [x][y]. Оси 1-based. Отсутствующие ячейки — None."""
        size_x, size_y = self.map_size
        if size_x == 0 or size_y == 0:
            return []
        map_list: list[list[Optional[MapDF2Cell]]] = [
            [None] * size_y for _ in range(size_x)
        ]
        for cell in self.cells:
            map_list[cell.x - 1][cell.y - 1] = cell
        return map_list

    @staticmethod
    def x_coord_to_level(x_coord: int) -> int:
        """Преобразование координаты X в уровень"""

        return MapDF2._map_x_coord_to_level.get(x_coord, 0)

    def get_buildings_by_coords(self, x: int, y: int) -> list[BuildingLocation]:
        """Здания в ячейке. Если ячейка отсутствует — возвращает пустой список."""
        cell = self.get_cell(x, y)
        return cell.buildings if cell else []

    def add_cell(self, cell: MapDF2Cell):
        """Добавление ячейки в карту. Помечает индексы как грязные и обновляет габариты."""
        self.cells.append(cell)
        # Быстрый апдейт габаритов; окончательно подтверждается в _ensure_indexes
        if cell.x > self.max_x:
            self.max_x = cell.x
        if cell.y > self.max_y:
            self.max_y = cell.y
        self._touch()

    def get_cell(self, x: int, y: int) -> Optional[MapDF2Cell]:
        """Получить ячейку по координатам O(1). Оси 1-based."""
        self._ensure_indexes()
        return self.idx_coords_to_cell.get((x, y))

    def get_cell_for_building(self, building: BuildingLocation) -> Optional[MapDF2Cell]:
        """Найти ячейку карты по локации здания.

        Алгоритм:
        1) Если заданы координаты (x, y, level) — ищем точное совпадение ячейки.
        2) Иначе ищем по имени здания и району в индексах.
        """
        # Попытка точного совпадения по координатам/уровню/району
        if all([_ not in (None, -1) for _ in [building.x, building.y, building.level]]):
            return self.get_cell(building.x, building.y)
        # Поиск по имени здания и району
        name_norm = self._normalize_name(building.name)
        district_str = self._district_value(building.district)
        self._ensure_indexes()
        cells = self.idx_name_district_to_cells.get((name_norm, district_str))
        if not cells:
            return None
        # Уже отсортировано по (x,y)
        return cells[0]

    def get_coords(self, loc: BuildingLocation) -> Optional[tuple[int, int]]:
        if loc.x not in (None, -1) and loc.y not in (None, -1):
            return loc.x, loc.y
        cell = self.get_cell_for_building(loc)
        if cell is None:
            return None
        return cell.x, cell.y

    def distance_between(
        self, a: BuildingLocation, b: BuildingLocation
    ) -> Optional[int]:
        """Манхэттенское расстояние между двумя зданиями.

        Если у здания отсутствуют координаты, выполняется попытка определить их
        через соответствующую ячейку карты (см. get_cell_for_building).
        Возвращает None, если определить координаты не удалось.
        """

        coords_a = self.get_coords(a)
        coords_b = self.get_coords(b)
        if coords_a is None or coords_b is None:
            return None
        ax, ay = coords_a
        bx, by = coords_b
        return abs(ax - bx) + abs(ay - by)

    def normalize_coords(self, locations: BuildingLocation) -> BuildingLocation:
        """Нормализация координат зданий."""
        coords = self.get_coords(locations)
        if coords is None:
            return None
        return BuildingLocation(
            name=locations.name,
            district=locations.district,
            x=coords[0],
            y=coords[1],
            level=self.MAP_X_COORD_TO_LEVEL.get(coords[0], 0),
        )

    # ───── Удобные методы ─────
    def get_cells_by_filter(
        self,
        *,
        districts: Optional[list[Union[District, str]]] = None,
        level_range: Optional[tuple[int, int]] = None,
        types: Optional[list[Union[BuildingType, AvanpostType, str]]] = None,
    ) -> list[MapDF2Cell]:
        """Фильтрация ячеек по списку районов, диапазону уровней и типам зданий.
        Пустые фильтры игнорируются.
        """
        self._ensure_indexes()
        result: list[MapDF2Cell] = []

        allowed_districts: Optional[set[str]] = None
        if districts:
            allowed_districts = {self._district_value(d) for d in districts}

        min_level, max_level = (None, None)
        if level_range is not None:
            min_level, max_level = level_range

        allowed_types: Optional[set[str]] = None
        if types:

            def names_values(item: object) -> set[str]:
                if isinstance(item, (BuildingType, AvanpostType)):
                    return {item.name, item.value}
                if isinstance(item, str):
                    s = item.strip()
                    return {s, s.upper()}
                return {str(item)}

            allowed_types = set()
            for t in types:
                allowed_types.update(names_values(t))

        for cell in self.cells:
            # district
            if allowed_districts is not None:
                if self._district_value(cell.district) not in allowed_districts:
                    continue
            # level
            if min_level is not None and cell.level < min_level:
                continue
            if max_level is not None and cell.level > max_level:
                continue
            # types
            if allowed_types is not None:
                cell_keys: set[str] = set()
                for t in cell.types:
                    if isinstance(t, (BuildingType, AvanpostType)):
                        cell_keys.update((t.name, t.value))
                    elif isinstance(t, str):
                        cell_keys.update((t, t.upper()))
                if cell_keys.isdisjoint(allowed_types):
                    continue
            result.append(cell)
        return result

    def to_cells_df(self):  # type: ignore[override]
        """Опциональная проекция ячеек в pandas.DataFrame."""
        rows = []
        for c in self.cells:
            rows.append(
                {
                    "x": c.x,
                    "y": c.y,
                    "level": c.level,
                    "district": self._district_value(c.district),
                    "types": [
                        (
                            t.value
                            if isinstance(t, (BuildingType, AvanpostType))
                            else str(t)
                        )
                        for t in (c.types or [])
                    ],
                }
            )
        return pd.DataFrame(rows)

    def to_buildings_df(self):  # type: ignore[override]
        """Опциональная проекция зданий в pandas.DataFrame.
        Колонки: name, district, x, y, level, building_type, cell_types
        """
        rows = []
        for c in self.cells:
            cell_types = [
                t.value if isinstance(t, (BuildingType, AvanpostType)) else str(t)
                for t in (c.types or [])
            ]
            district_str = self._district_value(c.district)
            for b in c.buildings or []:
                rows.append(
                    {
                        "name": b.name,
                        "district": district_str,
                        "x": c.x,
                        "y": c.y,
                        "level": c.level,
                        "building_type": (
                            b.building_type.value
                            if isinstance(b.building_type, (BuildingType, AvanpostType))
                            else (
                                None
                                if b.building_type is None
                                else str(b.building_type)
                            )
                        ),
                        "cell_types": cell_types,
                    }
                )
        return pd.DataFrame(rows)
