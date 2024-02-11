from enum import Enum


class Locale(str, Enum):
    """Locale codes"""

    TC = "tc"
    EN = "en"

    def description(self) -> str:
        match self:
            case Locale.TC:
                return "繁體中文"
            case Locale.EN:
                return "English"


class Transport(str, Enum):
    """Enums representing different types of transport"""

    KMB = "kmb"
    MTRBUS = "mtr_bus"
    MTRLRT = "mtr_lrt"
    MTRTRAIN = "mtr_train"
    CTB = "ctb"
    NWFB = "nwfb"
    NLB = "nlb"

    def description(self, language: Locale = Locale.TC) -> str:
        if language == Locale.EN:
            match self:
                case Transport.KMB: return "KMB"
                case Transport.MTRBUS: return "MTR (Bus)"
                case Transport.MTRLRT: return "MTR (Light Rail)"
                case Transport.MTRTRAIN: return "MTR"
                case Transport.CTB: return "City Bus"
                case Transport.NLB: return "New Lantao Bus"
        else:
            match self:
                case Transport.KMB: return "九巴"
                case Transport.MTRBUS: return "港鐵巴士"
                case Transport.MTRLRT: return "輕鐵"
                case Transport.MTRTRAIN: return "港鐵"
                case Transport.CTB: return "城巴"
                case Transport.NLB: return "新大嶼山巴士"


class Direction(str, Enum):
    """Direction of a route"""

    OUTBOUND = UPLINK = "outbound"
    INBOUND = DOWNLINK = "inbound"

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
    """Type of a stop"""

    ORIG = ORIGINATION = "orig"
    STOP = MIDWAY = "stop"
    DEST = DESTINATION = "dest"

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
