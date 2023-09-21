from typing import Optional
from dataclasses import dataclass

try:
    from app.modules.hketa import enums
except (ImportError, ModuleNotFoundError):
    import enums


@dataclass(order=False, slots=True)
class RouteEntry:

    company: enums.Company
    name: str
    direction: enums.Direction
    service_type: Optional[str]
    stop: str
    lang: enums.Locale

    def __post_init__(self):
        self.name = str(self.name).upper()
        self.service_type = str(self.service_type)
        self.stop = str(self.stop)

    def as_dict(self) -> dict[str, str]:
        """get a dictionary representation"""
        return {
            'co': self.company.value,
            'name': self.name,
            'direction': self.direction.value,
            'service_type': self.service_type,
            'stop': self.stop,
            'lang': self.lang.value
        }


@dataclass(slots=True)
class Stop:

    id: str
    seq: int
    name: dict[enums.Locale, str]
