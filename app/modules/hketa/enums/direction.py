from enum import Enum

from .language import Language


class Direction(str, Enum):
    """Direction of a route"""

    OUTBOUND = UPLINK = "outbound"
    INBOUND = DOWNLINK = "inbound"

    @classmethod
    def members(cls) -> list["Direction"]:
        return [enum for enum in cls]

    @classmethod
    def values(cls) -> list[str]:
        return list(map(lambda c: c.value, cls))

    def from_str(direction: str) -> "Direction":
        for dir in Direction.members():
            if (dir.value.lower() == direction.lower()):
                return dir
        raise ValueError(f"direction not exists: {direction}")

    def description(self, language: Language = Language.TC) -> str:
        match language, self:
            case Language.TC, Direction.OUTBOUND:
                return "去程"
            case Language.TC, Direction.INBOUND:
                return "回程"
            case Language.EN, Direction.OUTBOUND:
                return "Outbound"
            case Language.EN, Direction.INBOUND:
                return "Inbound"
