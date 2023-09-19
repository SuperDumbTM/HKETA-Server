from enum import Enum

from .language import Language


class Company(str, Enum):
    """Company identifier for transport companies"""

    KMB = "kmb"
    MTRBUS = "mtr_bus"
    MTRLRT = "mtr_lrt"
    MTRTRAIN = "mtr_train"
    CTB = "ctb"
    NWFB = "nwfb"

    @classmethod
    def values(cls) -> list[str]:
        return list(map(lambda c: c.value, cls))

    def from_str(company: str) -> "Company":
        for co in Company.members():
            if (co.value.lower() == company.lower()):
                return co
        raise ValueError(f"company abbreviation not exists: {company}")

    def description(self, language: Language = Language.TC) -> str:
        match language, self:
            case Language.TC, Company.KMB:
                return "九巴"
            case Language.TC, Company.MTRBUS:
                return "港鐵巴士"
            case Language.TC, Company.MTRLRT:
                return "輕鐵"
            case Language.TC, Company.MTRTRAIN:
                return "地鐵"
            case Language.TC, Company.CTB:
                return "城巴"
            case Language.TC, Company.NWFB:
                return "新巴"
            case Language.EN, Company.KMB:
                return "KMB"
            case Language.EN, Company.MTRBUS:
                return "MTR Bus"
            case Language.EN, Company.MTRLRT:
                return "MTR LRT"
            case Language.EN, Company.MTRTRAIN:
                return "MTR Train"
            case Language.EN, Company.CTB:
                return "City Bus"
            case Language.EN, Company.NWFB:
                return "First Bus"
