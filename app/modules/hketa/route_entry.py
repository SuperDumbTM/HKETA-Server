from typing import Optional
from dataclasses import dataclass

try:
    import enums as etaenums
except ImportError:
    from . import enums as etaenums


@dataclass(order=False, slots=True)
class RouteEntry:

    co: etaenums.Company
    name: str
    direction: etaenums.Direction
    service_type: Optional[str]
    stop: str
    lang: etaenums.Language

    def __post_init__(self):
        self.name = str(self.name).upper()
        self.service_type = str(self.service_type)
        self.stop = str(self.stop)

    def as_dict(self) -> dict[str, str]:
        """get a dictionary representation"""
        return {
            'co': self.co.value,
            'name': self.name,
            'direction': self.direction.value,
            'service_type': self.service_type,
            'stop': self.stop,
            'lang': self.lang.value
        }
