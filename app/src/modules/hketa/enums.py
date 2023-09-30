from typing import Iterable
from enum import Enum


class Locale(str, Enum):
    """Locale codes"""

    TC = "tc"
    EN = "en"

    @classmethod
    def values(cls) -> Iterable[str]:
        return list(map(lambda c: c.value, cls))

    def from_str(self, locale: str) -> "Locale":
        for code in Locale:
            if (code.value.lower() == locale.lower()):
                return code
        raise ValueError(f"Locale not exists: {locale}")

    def description(self) -> str:
        match self:
            case Locale.TC:
                return "繁體中文"
            case Locale.EN:
                return "English"


class Company(str, Enum):
    """Company identifier for transport companies"""

    KMB = "kmb"
    MTRBUS = "mtr_bus"
    MTRLRT = "mtr_lrt"
    MTRTRAIN = "mtr_train"
    CTB = "ctb"
    NWFB = "nwfb"

    @classmethod
    def values(cls) -> Iterable[str]:
        return list(map(lambda c: c.value, cls))

    def from_str(self, company: str) -> "Company":
        for co in Company:
            if (co.value.lower() == company.lower()):
                return co
        raise ValueError(f"company abbreviation not exists: {company}")

    def description(self, language: Locale = Locale.TC) -> str:
        match language, self:
            case Locale.TC, Company.KMB:
                return "九巴"
            case Locale.TC, Company.MTRBUS:
                return "港鐵巴士"
            case Locale.TC, Company.MTRLRT:
                return "輕鐵"
            case Locale.TC, Company.MTRTRAIN:
                return "地鐵"
            case Locale.TC, Company.CTB:
                return "城巴"
            case Locale.TC, Company.NWFB:
                return "新巴"
            case Locale.EN, Company.KMB:
                return "KMB"
            case Locale.EN, Company.MTRBUS:
                return "MTR Bus"
            case Locale.EN, Company.MTRLRT:
                return "MTR LRT"
            case Locale.EN, Company.MTRTRAIN:
                return "MTR Train"
            case Locale.EN, Company.CTB:
                return "City Bus"
            case Locale.EN, Company.NWFB:
                return "First Bus"


class Direction(str, Enum):
    """Direction of a route"""

    OUTBOUND = UPLINK = "outbound"
    INBOUND = DOWNLINK = "inbound"

    @classmethod
    def values(cls) -> Iterable[str]:
        return list(map(lambda c: c.value, cls))

    def from_str(self, direction: str) -> "Direction":
        for dir in Direction:
            if (dir.value.lower() == direction.lower()):
                return dir
        raise ValueError(f"direction not exists: {direction}")

    def description(self, language: Locale = Locale.TC) -> str:
        match language, self:
            case Locale.TC, Direction.OUTBOUND:
                return "去程"
            case Locale.TC, Direction.INBOUND:
                return "回程"
            case Locale.EN, Direction.OUTBOUND:
                return "Outbound"
            case Locale.EN, Direction.INBOUND:
                return "Inbound"


class StopType(str, Enum):
    """Stop type of a stop"""

    ORIG = ORIGINATION = "orig"
    STOP = MIDWAY = "stop"
    DEST = DESTINATION = "dest"

    @classmethod
    def values(cls) -> Iterable[str]:
        return list(map(lambda c: c.value, cls))

    def from_str(self, type_: str) -> "StopType":
        for ty in StopType:
            if (ty.value.lower() == type_.lower()):
                return ty
        raise ValueError(f"stop type not exists: {type_}")

    def description(self, language: Locale = Locale.TC) -> "StopType":
        match language, self:
            case Locale.TC, StopType.ORIG | StopType.ORIGINATION:
                return "起點站"
            case Locale.TC, StopType.STOP | StopType.MIDWAY:
                return "中途站"
            case Locale.TC, StopType.DEST | StopType.DESTINATION:
                return "終點站"
            case Locale.EN, StopType.ORIG | StopType.ORIGINATION:
                return "Origination"
            case Locale.EN, StopType.STOP | StopType.MIDWAY:
                return "Midway Stop"
            case Locale.EN, StopType.DEST | StopType.DESTINATION:
                return "Destination"
