# pylint: disable=unnecessary-lambda

from typing import Optional
from pydantic import Field

from pydantic.dataclasses import dataclass

try:
    from app.src.modules.hketa import enums
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


@dataclass(slots=True)
class RouteInfo:

    company: enums.Company
    name: str
    inbound: list["Detail"] = Field(default_factory=list)
    outbound: list["Detail"] = Field(default_factory=list)

    def bound_lookup(self, bound: enums.Direction) -> list["Detail"]:
        return (self.inbound
                if bound == enums.Direction.INBOUND else self.outbound)

    def service_lookup(self, bound: enums.Direction, service_type: str) -> "Detail":
        for detail in self.bound_lookup(bound):
            if detail.service_type == service_type:
                return detail
        raise KeyError(f"service_type: {service_type}")

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


@dataclass(slots=True, frozen=True)
class Eta:

    company: enums.Company
    destination: str
    is_arriving: bool
    time: Optional[str]
    minute: Optional[int]
    second: Optional[int]
    remark: Optional[str] = None
    extras: "Eta.ExtraInfo" = Field(default_factory=lambda: Eta.ExtraInfo())

    @dataclass(slots=True, frozen=True)
    class ExtraInfo:

        platform: Optional[int] = None
        car_length: Optional[int] = None
