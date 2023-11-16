import io
import os
from abc import ABC, abstractmethod

try:
    from app.src.modules.hketa import company_data, enums, models
except (ImportError, ModuleNotFoundError):
    import company_data
    import enums
    import models


_DIRLOGO = os.path.join(os.path.dirname(__file__), "logo", "mono_neg")


def singleton(cls):
    instances = {}

    def wrapper(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return wrapper


class Transport(ABC):
    """
        Public Transport
        ~~~~~~~~~~~~~~~~~~~~~
        `Transport` representing a public transport company, providing
        information related to the company, mainly operating routes' information

        All child of of `Transport` is implemented as singleton.

        ---
        Language of information returns depends on the `RouteEntry` (if applicatable)

        ---
        Args:
            route_data (RouteData): RouteData instance for `Transport` retriving routes information
    """

    _provider: company_data.CompanyData
    # _data: dict
    """All routes data of the transport company"""

    @property
    def data(self) -> dict[str, models.RouteInfo]:
        return self._route_list

    @property
    def route_data(self) -> company_data.CompanyData:
        """route data instance"""
        return self._provider

    def __init__(self, route_data: company_data.CompanyData) -> None:
        self._provider = route_data
        self._route_list = self._provider.route_list()

    @abstractmethod
    def logo(self) -> io.BufferedReader:
        """Get the company logo in bytes"""

    def origin(self, entry: models.RouteEntry):
        try:
            return self.data[entry.name].bound_lookup(entry.direction)[0].orig.name[entry.lang]
        except KeyError:
            return "-----"

    def orig_stopcode(self, entry: models.RouteEntry):
        return self.data[entry.name].bound_lookup(entry.direction)[0].orig.stop_code

    def destination(self, entry: models.RouteEntry):
        try:
            return self.data[entry.name].bound_lookup(entry.direction)[0].dest.name[entry.lang]
        except KeyError:
            return "-----"

    def dest_stopcode(self, entry: models.RouteEntry):
        return self.data[entry.name].bound_lookup(entry.direction)[0].dest.stop_code

    def stop_type(self, entry: models.RouteEntry) -> enums.StopType:
        """Get the stop type of the stop"""
        if self.orig_stopcode(entry) == entry.stop:
            return enums.StopType.ORIG
        elif self.dest_stopcode(entry) == entry.stop:
            return enums.StopType.DEST
        else:
            return enums.StopType.STOP


@singleton
class KowloonMotorBus(Transport):

    def logo(self) -> io.BufferedReader:
        return open(os.path.join(_DIRLOGO, "kmb.bmp"), "rb")

    def origin(self, entry: models.RouteEntry):
        try:
            return super().data[entry.name].service_lookup(entry.direction, entry.service_type).orig.name[entry.lang]
        except KeyError:
            return "-----"

    def orig_stopcode(self, entry: models.RouteEntry):
        return super().data[entry.name].service_lookup(entry.direction, entry.service_type).orig.stop_code

    def destination(self, entry: models.RouteEntry):
        try:
            return super().data[entry.name].service_lookup(entry.direction, entry.service_type).dest.name[entry.lang]
        except KeyError:
            return "-----"

    def dest_stopcode(self, entry: models.RouteEntry):
        return super().data[entry.name].service_lookup(entry.direction, entry.service_type).dest.stop_code


@singleton
class MTRBus(Transport):

    def logo(self) -> io.BufferedReader:
        return open(os.path.join(_DIRLOGO, "mtr_bus.bmp"), "rb")


@singleton
class MTRLightRail(Transport):

    def logo(self) -> io.BufferedReader:
        return open(os.path.join(_DIRLOGO, "mtr_lrt.bmp"), "rb")

    def destination(self, entry: models.RouteEntry):
        # NOTE: in/outbound of circular routes are NOT its destination
        # NOTE: 705, 706 return "天水圍循環綫"/'TSW Circular' instead of its destination
        try:
            if entry.name in ("705", "706"):
                return "天水圍循環綫" if entry.lang == enums.Locale.TC else "TSW Circular"
            else:
                return super().data[entry.name].bound_lookup(entry.direction)[0].dest.name[entry.lang]
        except KeyError:
            return "-----"


@singleton
class MTRTrain(Transport):

    def logo(self) -> io.BufferedReader:
        return open(os.path.join(_DIRLOGO, "mtr_train.bmp"), "rb")


class CityBus(Transport):

    def logo(self) -> io.BufferedReader:
        return open(os.path.join(_DIRLOGO, "ctb.bmp"), "rb")
