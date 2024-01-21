try:
    from . import enums, exceptions, models, transport
except (ImportError, ModuleNotFoundError):
    import enums
    import exceptions
    import models
    import transport

# MTR do not provide complete route name, need manual translation
MTR_TRAIN_NAMES = {
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


class Route:
    """
    Public Transport Route
    ~~~~~~~~~~~~~~~~~~~~~
    `Route` provides methods retrive details of a route (e.g. stop name, stop ID etc.)


    ---
    Language of information returns depends on the `models.RouteEntry` parameter (if applicatable)
    """

    _provider: transport.Transport
    _stop_list: dict[str, models.RouteInfo.Stop]

    @property
    def entry(self):
        return self._entry

    def __init__(self, entry: models.RouteEntry, transport_: transport.Transport) -> None:
        self._entry = entry
        self._provider = transport_

        stop_list = tuple(self._provider.stop_list(self._entry))
        self._stop_list = {
            stop: data
            for stop, data in zip((stop.stop_code for stop in stop_list),
                                  stop_list)
        }

        if (self._entry.stop not in self._stop_list.keys()):
            raise exceptions.StopNotExist(self._entry.stop)

    def comanpy(self) -> str:
        """Get the operating company name of the route"""
        return self._entry.company.description(self._entry.lang)

    def name(self) -> str:
        """Get the route name of the `entry`"""
        if isinstance(self._provider, transport.MTRTrain):
            return MTR_TRAIN_NAMES.get(self._entry.stop, self._entry.stop)
        return self._entry.name

    def stop_name(self) -> str:
        """Get the stop name of the route"""
        return self._stop_list[self._entry.stop].name[self._entry.lang]

    def stop_seq(self) -> int:
        """Get the stop sequence of the route"""
        return self._stop_list[self._entry.stop].seq

    def stop_name_by_code(self, stop_code: str) -> str:
        """Get the stop name by `stop_code`"""
        return self._stop_list[stop_code].name[self._entry.lang]

    def origin(self):
        try:
            return list(self._stop_list.values())[0].name[self._entry.lang]
        except KeyError:
            return "-----"

    def orig_stopcode(self):
        return list(self._stop_list.values())[0].name

    def destination(self):
        try:
            return list(self._stop_list.values())[-1].name[self._entry.lang]
        except KeyError:
            return "-----"

    def dest_stopcode(self):
        return list(self._stop_list.values())[-1].name

    def stop_type(self) -> enums.StopType:
        """Get the stop type of the stop"""
        if self.orig_stopcode() == self._entry.stop:
            return enums.StopType.ORIG
        if self.dest_stopcode() == self._entry.stop:
            return enums.StopType.DEST
        return enums.StopType.STOP
