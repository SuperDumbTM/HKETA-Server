from abc import ABC, abstractmethod

try:
    from . import enums, exceptions, models, transport
except (ImportError, ModuleNotFoundError):
    import enums
    import exceptions
    import models
    import transport


class Route(ABC):
    """
    Public Transport Route
    ~~~~~~~~~~~~~~~~~~~~~
    `Route` provides methods retrive details of a route (e.g. stop name, stop ID etc.)


    ---
    Language of information returns depends on the `models.RouteEntry` parameter (if applicatable)
    """

    _entry: models.RouteEntry
    _provider: transport.Transport
    _stop_list: dict[str, models.RouteInfo.Stop]

    @property
    def route_entry(self) -> models.RouteEntry:
        return self._entry

    @property
    def data(self) -> dict[str, models.RouteInfo.Stop]:
        """Raw data of the route
        """
        return self._stop_list

    def __init__(self, entry: models.RouteEntry, transport_: transport.Transport) -> None:
        self._entry = entry
        self._provider = transport_

        stop_list = tuple(self._provider.stop_list(self._entry))
        self._stop_list = {stop: data for stop, data in zip(
            (stop.stop_code for stop in stop_list), stop_list)}

        if (self._entry.stop not in self._stop_list.keys()):
            raise exceptions.StopNotExist

    def route_name(self) -> str:
        """Get the route name of the `entry`"""
        return self._entry.name

    def comanpy(self) -> str:
        """Get the operating company name of the route"""
        return self._entry.company.description(self.route_entry.lang)

    @abstractmethod
    def stop_name(self) -> str:
        """Get the stop name of the route"""

    @abstractmethod
    def rt_stop_name(self, stop_code: str) -> str:
        """Get the stop name by `stop_code`"""

    @abstractmethod
    def stop_seq(self) -> int:
        """Get the stop sequence of the route"""


class KMBRoute(Route):

    def stop_name(self):
        try:
            return super().data[self._entry.stop].name[self.route_entry.lang]
        except KeyError:
            return self._entry.stop

    def rt_stop_name(self, stop_code: str) -> str:
        try:
            return super().data[stop_code].name[self.route_entry.lang]
        except KeyError:
            return "-----"

    def stop_seq(self):
        return super().data[self._entry.stop].seq


class MTRBusRoute(Route):

    def stop_name(self) -> str:
        try:
            return super().data[self._entry.stop].name[self.route_entry.lang]
        except KeyError:
            return self._entry.stop

    def rt_stop_name(self, stop_id: str) -> str:
        try:
            return super().data[stop_id].name[self.route_entry.lang]
        except KeyError:
            return "-----"

    def stop_seq(self) -> int:
        return super().data[self._entry.stop].seq


class MTRLrtRoute(Route):

    def stop_name(self) -> str:
        try:
            return super().data[self._entry.stop].name[self.route_entry.lang]
        except KeyError:
            return self._entry.stop

    def rt_stop_name(self, stop_code: str) -> str:
        try:
            return super().data[stop_code].name[self.route_entry.lang]
        except KeyError:
            return "-----"

    def stop_seq(self):
        return super().data[self._entry.stop].seq


class MTRTrainRoute(Route):

    # MTR do not provide complete route name, need manual translation
    __rt_names = {
        'AEL': {enums.Locale.TC: "機場快線", enums.Locale.EN: "Airport Express"},
        'TCL': {enums.Locale.TC: "東涌線", enums.Locale.EN: "Tung Chung Line"},
        'TML': {enums.Locale.TC: "屯馬線", enums.Locale.EN: "Tuen Ma Line"},
        'TKL': {enums.Locale.TC: "將軍澳線", enums.Locale.EN: "Tseung Kwan O Line"},
        'TKL-TKS': {enums.Locale.TC: "將軍澳線", enums.Locale.EN: "Tseung Kwan O Line"},
        'EAL': {enums.Locale.TC: "東鐵線", enums.Locale.EN: "East Rail Line"},
        'EAL-LMC': {enums.Locale.TC: "東鐵線", enums.Locale.EN: "East Rail Line"},
        'DRL': {enums.Locale.TC: "迪士尼線", enums.Locale.EN: "Disney"},
        'KTL': {enums.Locale.TC: "觀塘線", enums.Locale.EN: "KT Line"},
        'TWL': {enums.Locale.TC: "荃灣線", enums.Locale.EN: "TW Line"},
        'ISL': {enums.Locale.TC: "港島線", enums.Locale.EN: "Island"},
        'SIL': {enums.Locale.TC: "南港島線", enums.Locale.EN: "Sth Island"},
    }

    def route_name(self) -> str:
        try:
            return self.__rt_names[self._entry.name][self.route_entry.lang]
        except KeyError:
            return self._entry.name

    def stop_name(self) -> str:
        try:
            return super().data[self._entry.stop].name[self.route_entry.lang]
        except KeyError:
            return self._entry.stop

    def rt_stop_name(self, stop_code: str) -> str:
        try:
            return super().data[stop_code].name[self.route_entry.lang]
        except KeyError:
            return "-----"

    def stop_seq(self):
        return super().data[self._entry.stop].seq


class BravoBusRoute(Route):

    def stop_name(self):
        try:
            return super().data[self._entry.stop].name[self.route_entry.lang]
        except KeyError:
            return self._entry.stop

    def rt_stop_name(self, stop_code: str) -> str:
        try:
            return super().data[stop_code].name[self.route_entry.lang]
        except KeyError:
            return "-----"

    def stop_seq(self):
        return super().data[self._entry.stop].seq
