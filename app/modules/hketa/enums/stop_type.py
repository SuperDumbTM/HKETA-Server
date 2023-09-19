from enum import Enum

from .language import Language


class StopType(str, Enum):
    """Stop type of a stop"""

    ORIG = ORIGINATION = "orig"
    STOP = MIDWAY = "stop"
    DEST = DESTINATION = "dest"

    def from_str(type_: str) -> "StopType":
        for ty in StopType.members():
            if (ty.value.lower() == type_.lower()):
                return ty
        raise ValueError(f"stop type not exists: {type_}")

    def description(self, language: Language = Language.TC) -> "StopType":
        match language, self:
            case Language.TC, StopType.ORIG | StopType.ORIGINATION:
                return "起點站"
            case Language.TC, StopType.STOP | StopType.MIDWAY:
                return "中途站"
            case Language.TC, StopType.DEST | StopType.DESTINATION:
                return "終點站"
            case Language.EN, StopType.ORIG | StopType.ORIGINATION:
                return "Origination"
            case Language.EN, StopType.STOP | StopType.MIDWAY:
                return "Midway Stop"
            case Language.EN, StopType.DEST | StopType.DESTINATION:
                return "Destination"
