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
    `Route` works with `RouteData` and `models.RouteEntry`
    to provide methods retrive details of a route (e.g. stop name, stop code etc.)


    ---
    Language of information returns depends on the `models.RouteEntry` parameter (if applicatable)
    """

    _rt: models.RouteEntry
    _route_dt: dict[str, dict]

    @property
    def route_entry(self) -> models.RouteEntry:
        return self._rt

    @route_entry.setter
    def route_entry(self, new: models.RouteEntry) -> None:
        if not isinstance(new, models.RouteEntry):
            raise TypeError(
                "new value is not a models.RouteEntry instance")
        self._rt = new

    @property
    def lang_key(self) -> str:
        """key for `data` for retriving text with consponding language setting in `route_entry`
        (`models.RouteEntry.lang`), refer to `company_data.RouteData.route()` for the format of `data`"""
        return self._lang_k

    @property
    def data(self) -> dict:
        """Raw data of the route"""
        return self._route_dt

    def __init__(self, entry: models.RouteEntry, company_data: company_data.CompanyData) -> None:
        self._rt = entry
        self._rtdt = company_data
        self._lang_k = self._rtdt.lang_key(self._rt.lang)
        self._route_dt = self._rtdt.route(self._rt)['data']

    @abstractmethod
    def lang_code(self) -> str:
        """translates the language to which the company is using

        e.g. `tc` -> `zh`"""

    def route_name(self) -> str:
        """gets the route name of the `entry`"""
        return self._rt.name

    def comanpy(self) -> str:
        """gets the company name of the `entry`"""
        return self._rt.company.description(self._rt.lang)

    @abstractmethod
    def stop_name(self) -> str:
        """gets the stop name of the `entry`"""

    @abstractmethod
    def rt_stop_name(self, stop_id: str) -> str:
        """gets the stop name by `stop_id`"""

    @abstractmethod
    def stop_seq(self) -> int:
        """gets the stop sequence of the `entry`"""

    def route_exists(self, raise_: bool = False) -> bool:
        """checks whether the route of the `entry` is exists

        Args:
            raise_ (bool, optional): raise exception when the route\
                is not exists. Defaults to False.

        Raises:
            exceptions.RouteNotExist: the route is not exists

        Returns:
            bool: `True` if exists
        """
        if raise_ and self._route_dt.get(self._rt.stop) is None:
            raise exceptions.RouteNotExist
        else:
            return self._route_dt.get(self._rt.stop) is not None


class KMBRoute(Route):

    _languages = {
        enums.Language.TC: "tc",
        enums.Language.EN: "en"
    }
    """language code translation from module standard defined in `enums` to company standard"""

    def lang_code(self) -> str:
        return self._languages[self.route_entry.lang]

    def stop_name(self):
        try:
            print(super().data[self._rt.stop])
            return super().data[self._rt.stop][self._lang_k]
        except KeyError:
            return self._rt.stop

    def rt_stop_name(self, stop_id: str) -> str:
        try:
            return super().data[stop_id][self._lang_k]
        except KeyError:
            return "-----"

    def stop_seq(self):
        return super().data[self._rt.stop]['seq']


class MTRBusRoute(Route):

    _languages = {
        enums.Language.TC: "zh",
        enums.Language.EN: "en"
    }
    """language code translation from module standard defined in `enums` to company standard"""

    def lang_code(self) -> str:
        return self._languages[self.route_entry.lang]

    def stop_name(self) -> str:
        try:
            return super().data[self._rt.stop][self._lang_k]
        except Exception:
            return self._rt.stop

    def rt_stop_name(self, stop_id: str) -> str:
        try:
            return super().data[stop_id][self._lang_k]
        except KeyError:
            return "-----"

    def stop_seq(self) -> int:
        return super().data[self._rt.stop]['seq']


class MTRLrtRoute(Route):

    _languages = {
        enums.Language.TC: "ch",
        enums.Language.EN: "en"
    }
    """language code translation from module standard defined in `enums` to company standard"""

    def lang_code(self) -> str:
        return self._languages[self.route_entry.lang]

    def stop_name(self) -> str:
        try:
            return super().data[self._rt.stop][self._lang_k]
        except Exception:
            return self._rt.stop

    def rt_stop_name(self, stop_id: str) -> str:
        try:
            return super().data[stop_id][self._lang_k]
        except KeyError:
            return "-----"

    def stop_seq(self):
        return super().data[self._rt.stop]['seq']


class MTRTrainRoute(Route):

    _languages = {
        enums.Language.TC: "zh",
        enums.Language.EN: "en"
    }
    """language code translation from module standard defined in `enums` to company standard"""

    __rt_names = {
        'AEL': {enums.Language.TC: "機場快線", enums.Language.EN: "Airport Express"},
        'TCL': {enums.Language.TC: "東涌線", enums.Language.EN: "Tung Chung Line"},
        'TML': {enums.Language.TC: "屯馬線", enums.Language.EN: "Tuen Ma Line"},
        'TKL': {enums.Language.TC: "將軍澳線", enums.Language.EN: "Tseung Kwan O Line"},
        'TKL-TKS': {enums.Language.TC: "將軍澳線", enums.Language.EN: "Tseung Kwan O Line"},
        'EAL': {enums.Language.TC: "東鐵線", enums.Language.EN: "East Rail Line"},
        'EAL-LMC': {enums.Language.TC: "東鐵線", enums.Language.EN: "East Rail Line"},
        # 'DRL': {stdk.Language.TC: "迪士尼線", stdk.Language.EN: "Disney"},
        # 'KTL': {stdk.Language.TC: "觀塘線", stdk.Language.EN: "KT Line"},
        # 'TWL': {stdk.Language.TC: "荃灣線", stdk.Language.EN: "TW Line"},
        # 'ISL': {stdk.Language.TC: "港島線", stdk.Language.EN: "Island"},
        # 'SIL': {stdk.Language.TC: "南港島線", stdk.Language.EN: "Sth Island"},
    }

    def lang_code(self) -> str:
        return self._languages[self.route_entry.lang]

    def route_name(self) -> str:
        try:
            return self.__rt_names[self._rt.name][self._rt.lang]
        except KeyError:
            return self._rt.name

    def stop_name(self) -> str:
        try:
            return super().data[self._rt.stop][self._lang_k]
        except KeyError:
            return self._rt.stop

    def rt_stop_name(self, stop_id: str) -> str:
        try:
            return super().data[stop_id][self._lang_k]
        except KeyError:
            return "-----"

    def stop_seq(self):
        return super().data[self._rt.stop]['seq']


class BravoBusRoute(Route):
    """`RouteDetail_` class for City Bus (CTB) and New World First Bus (NWFB)"""

    _languages = {
        enums.Language.TC: "tc",
        enums.Language.EN: "en"
    }
    """language code translation from module standard defined in `enums` to company standard"""

    def lang_code(self) -> str:
        return self._languages[self.route_entry.lang]

    def stop_name(self):
        try:
            return super().data[self._rt.stop][self._lang_k]
        except KeyError:
            return self._rt.stop

    def rt_stop_name(self, stop_id: str) -> str:
        try:
            return super().data[stop_id][self._lang_k]
        except KeyError:
            return "-----"

    def stop_seq(self):
        return super().data[self._rt.stop]['seq']


if __name__ == "__main__":
    entry = models.RouteEntry(
        enums.Company.KMB, "265M", enums.Direction.OUTBOUND, "1", "223DAE7E925E3BB9", enums.Language.TC)
    route = KMBRoute(entry, company_data.KMBData(
        "cachs\\transport_data", True))
    print(route.stop_name())
