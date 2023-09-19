from enum import Enum


class Language(str, Enum):
    """Language code for text language"""

    TC = "tc"
    EN = "en"

    @classmethod
    def values(cls) -> list["str"]:
        return list(map(lambda c: c.value, cls))

    def from_str(locale: str) -> "Language":
        for code in Language.members():
            if (code.value.lower() == locale.lower()):
                return code
        raise ValueError(f"language not exists: {locale}")

    def description(self) -> str:
        match self:
            case Language.TC:
                return "繁體中文"
            case Language.EN:
                return "English"
