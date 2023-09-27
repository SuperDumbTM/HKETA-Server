from typing import Optional

from pydantic.dataclasses import dataclass

try:
    from app.modules.hketa import enums
except (ImportError, ModuleNotFoundError):
    import enums


@dataclass(slots=True)
class RouteEntry:

    company: enums.Company
    name: str
    direction: enums.Direction
    stop: str
    service_type: Optional[str]
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


@dataclass(slots=True, frozen=True)
class RouteInfo:

    inbound: Optional[list["Detail"]]
    outbound: Optional[list["Detail"]]

    @dataclass(slots=True, frozen=True)
    class Stop:

        stop_code: str
        seq: int
        name: dict[enums.Locale, str]

    @dataclass(slots=True, frozen=True)
    class Detail:

        service_type: Optional[str]
        orig: Optional["RouteInfo.Stop"]
        dest: Optional["RouteInfo.Stop"]
