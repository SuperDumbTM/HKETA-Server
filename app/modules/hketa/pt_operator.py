import io
import os
from abc import ABC, abstractmethod

try:
    import lib.hketa.pt_operator_data as opdata
    import enums as etaenums
    from route_entry import RouteEntry
except ImportError:
    from . import pt_operator_data as opdata
    from . import enums as etaenums
    from .route_entry import RouteEntry


DIRLOGO = os.path.join(os.path.dirname(__file__), "logo", "mono_neg")


def singleton(cls):
    instances = {}

    def wrapper(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return wrapper


class Operator(ABC):
    """
        Public Transport Operator
        ~~~~~~~~~~~~~~~~~~~~~
        `Operator` representing a public transport operator, providing
        information related to the operator, mainly operating routes information

        All child of of `Operator` is implemented as singleton.

        ---
        Language of information returns depends on the `RouteEntry` parameter (if applicatable)
        
        ---
        Args:
            route_data (RouteData): RouteData instance for `Operator` retriving routes information
    """

    _rtdt: opdata.OperatorData
    _routes_dt: dict

    @property
    def data(self) -> dict:
        """routes data"""
        return self._routes_dt

    @property
    def route_data(self) -> opdata.OperatorData:
        """route data instance"""
        return self._rtdt

    def __init__(self, route_data: opdata.OperatorData) -> None:
        self._rtdt = route_data
        self._routes_dt = self._rtdt.routes()['data']

    @abstractmethod
    def logo(self) -> io.BufferedReader:
        """gets the company logo in bytes"""

    @abstractmethod
    def origin(self, entry: RouteEntry) -> str:
        """gets the origin stop name of the route"""

    @abstractmethod
    def orig_stopcode(self, entry: RouteEntry) -> str:
        """gets the origin stop code of the route"""

    @abstractmethod
    def destination(self, entry: RouteEntry) -> str:
        """gets the destination stop name of the route"""

    @abstractmethod
    def dest_stopcode(self, entry: RouteEntry) -> str:
        """gets the destination stop code of the route"""

    def stop_type(self, entry: RouteEntry) -> etaenums.StopType:
        """gets the stop type of the stop"""
        if self.orig_stopcode(entry) == entry.stop:
            return etaenums.StopType.ORIG
        elif self.dest_stopcode(entry) == entry.stop:
            return etaenums.StopType.DEST
        else:
            return etaenums.StopType.STOP


@singleton
class KowloonMotorBus(Operator):

    def __init__(self, route_data: opdata.KMBData) -> None:
        super().__init__(route_data)

    def logo(self) -> io.BufferedReader:
        return open(os.path.join(DIRLOGO, "kmb.bmp"), "rb")

    def origin(self, entry: RouteEntry):
        try:
            return super().data[entry.name][entry.direction][entry.service_type][etaenums.StopType.ORIG][self._rtdt.lang_key(entry.lang)]
        except KeyError:
            return "-----"

    def orig_stopcode(self, entry: RouteEntry):
        return super().data[entry.name][entry.direction][entry.service_type][etaenums.StopType.ORIG]['stop_code']

    def destination(self, entry: RouteEntry):
        try:
            return super().data[entry.name][entry.direction][entry.service_type][etaenums.StopType.DEST][self._rtdt.lang_key(entry.lang)]
        except KeyError:
            return "-----"

    def dest_stopcode(self, entry: RouteEntry):
        return super().data[entry.name][entry.direction][entry.service_type][etaenums.StopType.DEST]['stop_code']


@singleton
class MTRBus(Operator):

    def __init__(self, route_data: opdata.MTRBusData) -> None:
        super().__init__(route_data)

    def logo(self) -> io.BufferedReader:
        return open(os.path.join(DIRLOGO, "mtr_bus.bmp"), "rb")

    def origin(self, entry: RouteEntry):
        try:
            return super().data[entry.name][entry.direction][etaenums.StopType.ORIG][self._rtdt.lang_key(entry.lang)]
        except KeyError:
            return "-----"

    def orig_stopcode(self, entry: RouteEntry):
        return super().data[entry.name][entry.direction][etaenums.StopType.ORIG]['stop_code']

    def destination(self, entry: RouteEntry):
        try:
            return super().data[entry.name][entry.direction][etaenums.StopType.DEST][self._rtdt.lang_key(entry.lang)]
        except KeyError:
            return "-----"

    def dest_stopcode(self, entry: RouteEntry):
        return super().data[entry.name][entry.direction][etaenums.StopType.DEST]['stop_code']


@singleton
class MTRLightRail(Operator):

    def __init__(self, route_data: opdata.MTRLrtData) -> None:
        super().__init__(route_data)

    def logo(self) -> io.BufferedReader:
        return open(os.path.join(DIRLOGO, "mtr_lrt.bmp"), "rb")

    def origin(self, entry: RouteEntry):
        try:
            return super().data[entry.name][entry.direction][etaenums.StopType.ORIG][self._rtdt.lang_key(entry.lang)]
        except Exception:
            return "-----"

    def orig_stopcode(self, entry: RouteEntry):
        return super().data[entry.name][entry.direction][etaenums.StopType.ORIG]['stop_code']

    def destination(self, entry: RouteEntry):
        # NOTE: in/outbound of circular routes are NOT its destination
        # NOTE: 705, 706 return "天水圍循環綫"/'TSW Circular' instead of its destination
        try:
            if entry.name in ("705", "706"):
                return "天水圍循環綫" if entry.lang == etaenums.Language.TC else "TSW Circular"
            else:
                return super().data[entry.name][entry.direction][etaenums.StopType.DEST][self._rtdt.lang_key(entry.lang)]
        except Exception:
            return "-----"

    def dest_stopcode(self, entry: RouteEntry):
        return super().data[entry.name][entry.direction][etaenums.StopType.DEST]['stop_code']


@singleton
class MTRTrain(Operator):

    def __init__(self, route_data: opdata.MTRTrainData) -> None:
        super().__init__(route_data)

    def logo(self) -> io.BufferedReader:
        return open(os.path.join(DIRLOGO, "mtr_train.bmp"), "rb")

    def origin(self, entry: RouteEntry):
        try:
            return super().data[entry.name][entry.direction][etaenums.StopType.ORIG][self._rtdt.lang_key(entry.lang)]
        except KeyError:
            return "-----"

    def orig_stopcode(self, entry: RouteEntry):
        return super().data[entry.name][entry.direction][etaenums.StopType.ORIG]['stop_code']

    def destination(self, entry: RouteEntry):
        try:
            return super().data[entry.name][entry.direction][etaenums.StopType.DEST][self._rtdt.lang_key(entry.lang)]
        except KeyError:
            return "-----"

    def dest_stopcode(self, entry: RouteEntry):
        return super().data[entry.name][entry.direction][etaenums.StopType.DEST]['stop_code']


class BravoTransport(Operator):

    def origin(self, entry: RouteEntry):
        try:
            return super().data[entry.name][entry.direction][etaenums.StopType.ORIG][self._rtdt.lang_key(entry.lang)]
        except KeyError:
            return "-----"

    def orig_stopcode(self, entry: RouteEntry):
        return super().data[entry.name][entry.direction][etaenums.StopType.ORIG]['stop_code']

    def destination(self, entry: RouteEntry):
        try:
            return super().data[entry.name][entry.direction][etaenums.StopType.DEST][self._rtdt.lang_key(entry.lang)]
        except KeyError:
            return "-----"

    def dest_stopcode(self, entry: RouteEntry):
        return super().data[entry.name][entry.direction][etaenums.StopType.DEST]['stop_code']


@singleton
class CityBus(BravoTransport):

    def __init__(self, route_data: opdata.CityBusData) -> None:
        super().__init__(route_data)

    def logo(self) -> io.BufferedReader:
        return open(os.path.join(DIRLOGO, "ctb.bmp"), "rb")


@singleton
class NWFirstBus(BravoTransport):

    def __init__(self, route_data: opdata.NWFirstBusData) -> None:
        super().__init__(route_data)

    def logo(self) -> io.BufferedReader:
        return open(os.path.join(DIRLOGO, "nwfb.bmp"), "rb")
