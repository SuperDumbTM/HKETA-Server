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

    entry: models.RouteEntry
    provider: transport.Transport
    _stop_list: dict[str, models.RouteInfo.Stop]

    def __init__(self, entry: models.RouteEntry, transport_: transport.Transport) -> None:
        self.entry = entry
        self.provider = transport_
        self._stop_list = {
            stop.stop_code: stop
            for stop in self.provider.stop_list(entry.no, entry.direction, entry.service_type)
        }

        if (self.entry.stop not in self._stop_list.keys()):
            raise exceptions.StopNotExist(self.entry.stop)

    def comanpy(self) -> str:
        """Get the operating company name of the route"""
        return self.entry.company.description(self.entry.lang)

    def name(self) -> str:
        """Get the route name of the `entry`"""
        if isinstance(self.provider, type(transport.MTRTrain)):
            return MTR_TRAIN_NAMES.get(self.entry.stop, self.entry.stop)
        return self.entry.no

    def stop_name(self) -> str:
        """Get the stop name of the route"""
        return self._stop_list[self.entry.stop].name[self.entry.lang]

    def stop_seq(self) -> int:
        """Get the stop sequence of the route"""
        return self._stop_list[self.entry.stop].seq

    def stop_details(self, stop_code: str) -> models.RouteInfo.Stop:
        return self._stop_list[stop_code]

    def origin(self) -> models.RouteInfo.Stop:
        return list(self._stop_list.values())[0]

    def destination(self) -> models.RouteInfo.Stop:
        stop = list(self._stop_list.values())[-1]

        # NOTE: in/outbound of circular routes are NOT its destination
        # NOTE: 705, 706 return "天水圍循環綫"/'TSW Circular' instead of its destination
        if self.entry.company == enums.Transport.MTRLRT and self.entry.no in ("705", "706"):
            return models.RouteInfo.Stop(stop_code=stop.stop_code,
                                         seq=stop.seq,
                                         name={
                                             enums.Locale.EN: "TSW Circular",
                                             enums.Locale.TC: "天水圍循環綫"
                                         })
        else:
            return stop

    def stop_type(self) -> enums.StopType:
        """Get the stop type of the stop"""
        if self.origin().stop_code == self.entry.stop:
            return enums.StopType.ORIG
        if self.destination().stop_code == self.entry.stop:
            return enums.StopType.DEST
        return enums.StopType.STOP
