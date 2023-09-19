from abc import ABC, abstractmethod

try:
    import lib.hketa.pt_operator_data as opdata
    import enums as etaenums
    import exceptions as etaex
    from route_entry import RouteEntry
except ImportError:
    from . import pt_operator_data as opdata
    from . import enums as etaenums
    from . import exceptions as etaex
    from .route_entry import RouteEntry


class Route(ABC):
    """
    Public Transport Route
    ~~~~~~~~~~~~~~~~~~~~~
    `Route` works with `RouteData` and `RouteEntry`
    to provide methods retrive details of a route (e.g. stop name, stop code etc.)

    
    ---
    Language of information returns depends on the `RouteEntry` parameter (if applicatable)
    """

    _rt: RouteEntry
    _route_dt: dict[str, dict]

    @property
    def route_entry(self) -> RouteEntry:
        return self._rt

    @route_entry.setter
    def route_entry(self, new: RouteEntry) -> None:
        if not isinstance(new, RouteEntry):
            raise TypeError("new value is not a RouteEntry instance")
        self._rt = new

    @property
    def lang_key(self) -> str:
        """key for `data` for retriving text with consponding language setting in `route_entry`
        (`RouteEntry.lang`), refer to `route_data.RouteData.route()` for the format of `data`"""
        return self._lang_k

    @property
    def data(self) -> dict:
        """route data"""
        return self._route_dt

    def __init__(self, entry: RouteEntry, route_data: opdata.OperatorData) -> None:
        self._rt = entry
        self._rtdt = route_data
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
        return self._rt.co.description(self._rt.lang)

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
            raise_ (bool, optional): raise exception when the route is not exists. Defaults to False.

        Raises:
            etaex.RouteNotExist: the route is not exists

        Returns:
            bool: `True` if exists
        """
        if raise_ and self._route_dt.get(self._rt.stop) is None:
            raise etaex.RouteNotExist
        else:
            return self._route_dt.get(self._rt.stop) is not None


class KMBRoute(Route):

    _languages = {
        etaenums.Language.TC: "tc",
        etaenums.Language.EN: "en"
    }
    """language code translation from module standard defined in `enums` to company standard"""

    def __init__(self,
                 entry: RouteEntry,
                 route_data: opdata.KMBData) -> None:
        super().__init__(entry, route_data)

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


class MTRBusRoute(Route):

    _languages = {
        etaenums.Language.TC: "zh",
        etaenums.Language.EN: "en"
    }
    """language code translation from module standard defined in `enums` to company standard"""

    def __init__(self,
                 entry: RouteEntry,
                 route_data: opdata.MTRBusData) -> None:
        super().__init__(entry, route_data)

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
        etaenums.Language.TC: "ch",
        etaenums.Language.EN: "en"
    }
    """language code translation from module standard defined in `enums` to company standard"""

    def __init__(self,
                 entry: RouteEntry,
                 route_data: opdata.MTRLrtData) -> None:
        super().__init__(entry, route_data)

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
        etaenums.Language.TC: "zh",
        etaenums.Language.EN: "en"
    }
    """language code translation from module standard defined in `enums` to company standard"""

    __rt_names = {
        'AEL': {etaenums.Language.TC: "機場快線", etaenums.Language.EN: "Airport Express"},
        'TCL': {etaenums.Language.TC: "東涌線", etaenums.Language.EN: "Tung Chung Line"},
        'TML': {etaenums.Language.TC: "屯馬線", etaenums.Language.EN: "Tuen Ma Line"},
        'TKL': {etaenums.Language.TC: "將軍澳線", etaenums.Language.EN: "Tseung Kwan O Line"},
        'TKL-TKS': {etaenums.Language.TC: "將軍澳線", etaenums.Language.EN: "Tseung Kwan O Line"},
        'EAL': {etaenums.Language.TC: "東鐵線", etaenums.Language.EN: "East Rail Line"},
        'EAL-LMC': {etaenums.Language.TC: "東鐵線", etaenums.Language.EN: "East Rail Line"},
        # 'DRL': {stdk.Language.TC: "迪士尼線", stdk.Language.EN: "Disney"},
        # 'KTL': {stdk.Language.TC: "觀塘線", stdk.Language.EN: "KT Line"},
        # 'TWL': {stdk.Language.TC: "荃灣線", stdk.Language.EN: "TW Line"},
        # 'ISL': {stdk.Language.TC: "港島線", stdk.Language.EN: "Island"},
        # 'SIL': {stdk.Language.TC: "南港島線", stdk.Language.EN: "Sth Island"},
    }

    def __init__(self,
                 entry: RouteEntry,
                 route_data: opdata.MTRTrainData) -> None:
        super().__init__(entry, route_data)

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
        etaenums.Language.TC: "tc",
        etaenums.Language.EN: "en"
    }
    """language code translation from module standard defined in `enums` to company standard"""

    def __init__(self,
                 entry: RouteEntry,
                 route_data: opdata.CityBusData | opdata.NWFirstBusData) -> None:
        super().__init__(entry, route_data)

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
