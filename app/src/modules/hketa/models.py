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
    service_type: str
    lang: enums.Locale

    def __post_init__(self):
        self.name = str(self.name).upper()


@dataclass(slots=True)
class RouteInfo:

    company: enums.Company
    name: str
    inbound: list["Detail"] = Field(default_factory=list)
    outbound: list["Detail"] = Field(default_factory=list)

    def bound(self, bound: enums.Direction) -> list["Detail"]:
        return (self.inbound
                if bound == enums.Direction.INBOUND else self.outbound)

    def service_lookup(self, bound: enums.Direction, service_type: str) -> "Detail":
        for detail in self.bound(bound):
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

        service_type: str
        orig: Optional["RouteInfo.Stop"]
        dest: Optional["RouteInfo.Stop"]


@dataclass(slots=True, frozen=True)
class Eta:

    company: enums.Company
    destination: str
    is_arriving: bool
    eta: Optional[str]
    eta_minute: Optional[int]
    remark: Optional[str] = None
    extras: "Eta.ExtraInfo" = Field(default_factory=lambda: Eta.ExtraInfo())

    @dataclass(slots=True, frozen=True)
    class ExtraInfo:

        platform: Optional[int] = None
        car_length: Optional[int] = None
