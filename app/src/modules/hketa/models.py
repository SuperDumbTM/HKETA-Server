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

    company: enums.Transport
    no: str
    direction: enums.Direction
    stop: str
    service_type: str
    lang: enums.Locale

    def __post_init__(self):
        self.no = str(self.no).upper()


@dataclass(slots=True)
class RouteInfo:

    company: enums.Transport
    route_no: str
    inbound: list["Detail"] = Field(default_factory=list)
    outbound: list["Detail"] = Field(default_factory=list)

    def bound(self, bound: enums.Direction) -> list["Detail"]:
        return (self.inbound
                if bound == enums.Direction.INBOUND else self.outbound)

    def service_lookup(self, bound: enums.Direction, service_type: str) -> "Detail":
        for detail in self.bound(bound):
            if detail.service_type == service_type:
                return detail
        raise KeyError(f"Invalid service type: {service_type}")

    @dataclass(slots=True, frozen=True)
    class Stop:

        stop_code: str
        seq: int
        name: dict[enums.Locale, str]

    @dataclass(slots=True, frozen=True)
    class Detail:

        service_type: str
        route_id: Optional[str] = None
        orig: Optional["RouteInfo.Stop"] = None
        dest: Optional["RouteInfo.Stop"] = None


@dataclass(slots=True, frozen=True)
class Eta:

    destination: str
    is_arriving: bool
    """Indicate whether the vehicle in the vincity of to the stop.
    """
    is_scheduled: bool
    """Indicate whether the ETA is based on realtime information or based on schedule.
    """
    eta: Optional[str] = None
    eta_minute: Optional[int] = None
    remark: Optional[str] = None
    extras: "Eta.Extras" = Field(default_factory=lambda: Eta.Extras())

    @dataclass(slots=True, frozen=True)
    class Extras:

        platform: Optional[str] = None
        car_length: Optional[int] = None
        route_variant: Optional[str] = None
        accuracy: Optional[int] = None
