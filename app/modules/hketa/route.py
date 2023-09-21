from abc import ABC, abstractmethod

try:
    from app.modules.hketa import company_data, enums, exceptions, models
except (ImportError, ModuleNotFoundError):
    import company_data
    import enums
    import exceptions
    import models


class Route(ABC):
    """
    Public Transport Route
    ~~~~~~~~~~~~~~~~~~~~~
    `Route` provides methods retrive details of a route (e.g. stop name, stop ID etc.)


    ---
    Language of information returns depends on the `models.RouteEntry` parameter (if applicatable)
    """

    _entry: models.RouteEntry
    _provider: company_data.CompanyData
    _data: dict[str, dict]
    """Route details (stop name, ID)"""

    @property
    def route_entry(self) -> models.RouteEntry:
        return self._entry

    @property
    def data(self) -> dict:
        """Raw data of the route
        """
        return self._data

    def __init__(self, entry: models.RouteEntry, company_data: company_data.CompanyData) -> None:
        self._entry = entry
        self._provider = company_data
        self._data = self._provider.route(self._entry)['data']

        if self._data.get(self._entry.stop) is None:
            raise exceptions.RouteNotExist

    def route_name(self) -> str:
        """Get the route name of the `entry`"""
        return self._entry.name

    def comanpy(self) -> str:
        """Get the operating company name of the route"""
        return self._entry.company.description(self._name_key())

    @abstractmethod
    def stop_name(self) -> str:
        """Get the stop name of the route"""

    @abstractmethod
    def rt_stop_name(self, stop_id: str) -> str:
        """Get the stop name by `stop_id`"""

    @abstractmethod
    def stop_seq(self) -> int:
        """Get the stop sequence of the route"""

    def _name_key(self) -> str:
        return f"name_{self._entry.lang.value}"


class KMBRoute(Route):

    def stop_name(self):
        try:
            print(super().data[self._entry.stop])
            return super().data[self._entry.stop][self._name_key()]
        except KeyError:
            return self._entry.stop

    def rt_stop_name(self, stop_id: str) -> str:
        try:
            return super().data[stop_id][self._name_key()]
        except KeyError:
            return "-----"

    def stop_seq(self):
        return super().data[self._entry.stop]['seq']


class MTRBusRoute(Route):

    def stop_name(self) -> str:
        try:
            return super().data[self._entry.stop][self._name_key()]
        except KeyError:
            return self._entry.stop

    def rt_stop_name(self, stop_id: str) -> str:
        try:
            return super().data[stop_id][self._name_key()]
        except KeyError:
            return "-----"

    def stop_seq(self) -> int:
        return super().data[self._entry.stop]['seq']


class MTRLrtRoute(Route):

    def stop_name(self) -> str:
        try:
            return super().data[self._entry.stop][self._name_key()]
        except KeyError:
            return self._entry.stop

    def rt_stop_name(self, stop_id: str) -> str:
        try:
            return super().data[stop_id][self._name_key()]
        except KeyError:
            return "-----"

    def stop_seq(self):
        return super().data[self._entry.stop]['seq']


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
            return self.__rt_names[self._entry.name][self._name_key()]
        except KeyError:
            return self._entry.name

    def stop_name(self) -> str:
        try:
            return super().data[self._entry.stop][self._name_key()]
        except KeyError:
            return self._entry.stop

    def rt_stop_name(self, stop_id: str) -> str:
        try:
            return super().data[stop_id][self._name_key()]
        except KeyError:
            return "-----"

    def stop_seq(self):
        return super().data[self._entry.stop]['seq']


class BravoBusRoute(Route):

    def stop_name(self):
        try:
            return super().data[self._entry.stop][self._name_key()]
        except KeyError:
            return self._entry.stop

    def rt_stop_name(self, stop_id: str) -> str:
        try:
            return super().data[stop_id][self._name_key()]
        except KeyError:
            return "-----"

    def stop_seq(self):
        return super().data[self._entry.stop]['seq']


if __name__ == "__main__":
    entry = models.RouteEntry(
        enums.Company.MTRTRAIN, "TML", enums.Direction.OUTBOUND, "1", "TIS", enums.Locale.TC)
    route = MTRTrainRoute(entry, company_data.MTRTrainData(
        "caches\\transport_data", True))
    print(route.stop_name())
