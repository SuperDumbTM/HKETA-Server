import io
import os
from abc import ABC, abstractmethod

try:
    from app.modules.hketa import company_data, enums, models
except (ImportError, ModuleNotFoundError):
    import company_data
    import enums
    import models


DIRLOGO = os.path.join(os.path.dirname(__file__), "logo", "mono_neg")


def singleton(cls):
    instances = {}

    def wrapper(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return wrapper


class Transport(ABC):
    """
        Public Transport Operator
        ~~~~~~~~~~~~~~~~~~~~~
        `Operator` representing a public transport company, providing
        information related to the company, mainly operating routes information

        All child of of `Operator` is implemented as singleton.

        ---
        Language of information returns depends on the `route_entry.RouteEntry` parameter (if applicatable)

        ---
        Args:
            route_data (RouteData): RouteData instance for `Operator` retriving routes information
    """

    _rtdt: company_data.CompanyData
    _routes_dt: dict

    @property
    def data(self) -> dict:
        """routes data"""
        return self._routes_dt

    @property
    def route_data(self) -> company_data.CompanyData:
        """route data instance"""
        return self._rtdt

    def __init__(self, route_data: company_data.CompanyData) -> None:
        self._rtdt = route_data
        self._routes_dt = self._rtdt.routes()['data']

    @abstractmethod
    def logo(self) -> io.BufferedReader:
        """gets the company logo in bytes"""

    @abstractmethod
    def origin(self, entry: models.RouteEntry) -> str:
        """gets the origin stop name of the route"""

    @abstractmethod
    def orig_stopcode(self, entry: models.RouteEntry) -> str:
        """gets the origin stop code of the route"""

    @abstractmethod
    def destination(self, entry: models.RouteEntry) -> str:
        """gets the destination stop name of the route"""

    @abstractmethod
    def dest_stopcode(self, entry: models.RouteEntry) -> str:
        """gets the destination stop code of the route"""

    def stop_type(self, entry: models.RouteEntry) -> enums.StopType:
        """gets the stop type of the stop"""
        if self.orig_stopcode(entry) == entry.stop:
            return enums.StopType.ORIG
        elif self.dest_stopcode(entry) == entry.stop:
            return enums.StopType.DEST
        else:
            return enums.StopType.STOP


@singleton
class KowloonMotorBus(Transport):

    def __init__(self, route_data: company_data.KMBData) -> None:
        super().__init__(route_data)

    def logo(self) -> io.BufferedReader:
        return open(os.path.join(DIRLOGO, "kmb.bmp"), "rb")

    def origin(self, entry: models.RouteEntry):
        try:
            return super().data[entry.name][entry.direction][entry.service_type][enums.StopType.ORIG][self._rtdt.lang_key(entry.lang)]
        except KeyError:
            return "-----"

    def orig_stopcode(self, entry: models.RouteEntry):
        return super().data[entry.name][entry.direction][entry.service_type][enums.StopType.ORIG]['stop_code']

    def destination(self, entry: models.RouteEntry):
        try:
            return super().data[entry.name][entry.direction][entry.service_type][enums.StopType.DEST][self._rtdt.lang_key(entry.lang)]
        except KeyError:
            return "-----"

    def dest_stopcode(self, entry: models.RouteEntry):
        return super().data[entry.name][entry.direction][entry.service_type][enums.StopType.DEST]['stop_code']


@singleton
class MTRBus(Transport):

    def __init__(self, route_data: company_data.MTRBusData) -> None:
        super().__init__(route_data)

    def logo(self) -> io.BufferedReader:
        return open(os.path.join(DIRLOGO, "mtr_bus.bmp"), "rb")

    def origin(self, entry: models.RouteEntry):
        try:
            return super().data[entry.name][entry.direction][enums.StopType.ORIG][self._rtdt.lang_key(entry.lang)]
        except KeyError:
            return "-----"

    def orig_stopcode(self, entry: models.RouteEntry):
        return super().data[entry.name][entry.direction][enums.StopType.ORIG]['stop_code']

    def destination(self, entry: models.RouteEntry):
        try:
            return super().data[entry.name][entry.direction][enums.StopType.DEST][self._rtdt.lang_key(entry.lang)]
        except KeyError:
            return "-----"

    def dest_stopcode(self, entry: models.RouteEntry):
        return super().data[entry.name][entry.direction][enums.StopType.DEST]['stop_code']


@singleton
class MTRLightRail(Transport):

    def __init__(self, route_data: company_data.MTRLrtData) -> None:
        super().__init__(route_data)

    def logo(self) -> io.BufferedReader:
        return open(os.path.join(DIRLOGO, "mtr_lrt.bmp"), "rb")

    def origin(self, entry: models.RouteEntry):
        try:
            return super().data[entry.name][entry.direction][enums.StopType.ORIG][self._rtdt.lang_key(entry.lang)]
        except Exception:
            return "-----"

    def orig_stopcode(self, entry: models.RouteEntry):
        return super().data[entry.name][entry.direction][enums.StopType.ORIG]['stop_code']

    def destination(self, entry: models.RouteEntry):
        # NOTE: in/outbound of circular routes are NOT its destination
        # NOTE: 705, 706 return "天水圍循環綫"/'TSW Circular' instead of its destination
        try:
            if entry.name in ("705", "706"):
                return "天水圍循環綫" if entry.lang == enums.Language.TC else "TSW Circular"
            else:
                return super().data[entry.name][entry.direction][enums.StopType.DEST][self._rtdt.lang_key(entry.lang)]
        except Exception:
            return "-----"

    def dest_stopcode(self, entry: models.RouteEntry):
        return super().data[entry.name][entry.direction][enums.StopType.DEST]['stop_code']


@singleton
class MTRTrain(Transport):

    def __init__(self, route_data: company_data.MTRTrainData) -> None:
        super().__init__(route_data)

    def logo(self) -> io.BufferedReader:
        return open(os.path.join(DIRLOGO, "mtr_train.bmp"), "rb")

    def origin(self, entry: models.RouteEntry):
        try:
            return super().data[entry.name][entry.direction][enums.StopType.ORIG][self._rtdt.lang_key(entry.lang)]
        except KeyError:
            return "-----"

    def orig_stopcode(self, entry: models.RouteEntry):
        return super().data[entry.name][entry.direction][enums.StopType.ORIG]['stop_code']

    def destination(self, entry: models.RouteEntry):
        try:
            return super().data[entry.name][entry.direction][enums.StopType.DEST][self._rtdt.lang_key(entry.lang)]
        except KeyError:
            return "-----"

    def dest_stopcode(self, entry: models.RouteEntry):
        return super().data[entry.name][entry.direction][enums.StopType.DEST]['stop_code']


class BravoTransport(Transport):

    def origin(self, entry: models.RouteEntry):
        try:
            return super().data[entry.name][entry.direction][enums.StopType.ORIG][self._rtdt.lang_key(entry.lang)]
        except KeyError:
            return "-----"

    def orig_stopcode(self, entry: models.RouteEntry):
        return super().data[entry.name][entry.direction][enums.StopType.ORIG]['stop_code']

    def destination(self, entry: models.RouteEntry):
        try:
            return super().data[entry.name][entry.direction][enums.StopType.DEST][self._rtdt.lang_key(entry.lang)]
        except KeyError:
            return "-----"

    def dest_stopcode(self, entry: models.RouteEntry):
        return super().data[entry.name][entry.direction][enums.StopType.DEST]['stop_code']


@singleton
class CityBus(BravoTransport):

    def __init__(self, route_data: company_data.CityBusData) -> None:
        super().__init__(route_data)

    def logo(self) -> io.BufferedReader:
        return open(os.path.join(DIRLOGO, "ctb.bmp"), "rb")


@singleton
class NWFirstBus(BravoTransport):

    def __init__(self, route_data: company_data.NWFirstBusData) -> None:
        super().__init__(route_data)

    def logo(self) -> io.BufferedReader:
        return open(os.path.join(DIRLOGO, "nwfb.bmp"), "rb")
