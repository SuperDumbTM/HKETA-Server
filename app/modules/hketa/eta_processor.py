import asyncio
import datetime
from abc import ABC, abstractmethod

try:
    import api
    import exceptions as etaex
    import route_details as rtdet
    from enums.stop_type import StopType
except ImportError:
    from . import api
    from . import exceptions as etaex
    from . import route_details as rtdet
    from .enums.stop_type import StopType


class EtaProcessor(ABC):
    """Public Transport ETA Retriver
    ~~~~~~~~~~~~~~~~~~~~~
    retrive, process and unify the format of ETA(s) data

    referer to `get_etas` for returns format

    ---
    during initialisation, `EtaProcessor` will check whether the route is exists
    or not.  If not exists, `etaex.RouteNotExist` will be raised.
    """

    @property
    def details(self) -> rtdet.RouteDetails:
        return self._rtdet

    @property
    def eta_entry(self):
        return self._rtdet.eta_entry

    def __init__(self, detail: rtdet.RouteDetails) -> None:
        self._rt = detail.eta_entry
        self._rtdet = detail

    @abstractmethod
    def etas(self) -> list[dict[str, str | int]]:
        """get processed ETA(s)

        Raises:
            EmptyDataError: no eta data

        Returns:
            list: sequence of ETA(s).

            >>> example
                [{
                    'co': str,
                    'second': int | None,
                    'minute': int | None,
                    'time': str (HH:MM) | None,
                    'destination': str
                    'remark': str
                }]
        """

    @abstractmethod
    @etaex.aioex_to_etex
    def raw_etas(self) -> dict[str | int]:
        """get the raws ETA(s) data from API with validity checking"""

    def _parse_iostime(self, iso8601time: str) -> datetime:
        """parse iso 8601 fomated timestamp to `datetime` instance

        internal use for parsing ETA data timestamp

        Args:
            iso8601time (str): an string in iso 8601 format

        Returns:
            datetime: datatime instance with the input time or current time
                if invalid time string is supplied
        """
        try:
            return datetime.datetime.fromisoformat(iso8601time)
        except ValueError:
            return datetime.datetime.now()


class KmbEta(EtaProcessor):

    def etas(self) -> dict:
        apidata = asyncio.run(self.raw_etas())
        timestamp = self._parse_iostime(apidata['generated_timestamp'])
        lang_code = super().details.lang_code()
        output = []

        for stop in apidata['data']:
            if (stop["seq"] != super().details.stop_seq()
                    or stop["dir"] != super().eta_entry.direction[0].upper()):
                continue
            elif stop["eta"] is None:
                if stop["rmk_" + lang_code] == "":
                    raise etaex.EndOfService
                raise etaex.ErrorReturns(stop["rmk_" + lang_code])
            eta_dt = datetime.datetime.fromisoformat(stop["eta"])
            output.append({
                'co': stop["co"],
                'second': int((eta_dt - timestamp).total_seconds()),
                'minute': int((eta_dt - timestamp).total_seconds() / 60),
                'time': datetime.datetime.strftime(eta_dt, "%H:%M"),
                'destination': stop[f'dest_{lang_code}'],
                'remark': stop[f'rmk_{lang_code}']
            })

            if len(output) == 3:
                #  NOTE: the number of ETA entry form API at the same stop may not be 3 every time.
                #  KMB only provide at most 3 upcoming ETAs
                #  (e.g. N routes may provide only 2)
                break

        if len(output) == 0:
            raise etaex.EmptyDataError
        return output

    @etaex.aioex_to_etex
    async def raw_etas(self) -> dict[str | int]:
        apidata = await api.kmb_eta(
            super().eta_entry.name, super().eta_entry.service_type)

        if len(apidata) == 0:
            raise etaex.APIError
        elif apidata.get('data') is None:
            raise etaex.EmptyDataError
        else:
            return apidata


class MtrBusEta(EtaProcessor):

    def etas(self):
        apidata = asyncio.run(self.raw_etas())
        timestamp = datetime.datetime.strptime(
            apidata["routeStatusTime"], "%Y/%m/%d %H:%M")
        output = []

        for stop in apidata["busStop"]:
            if stop["busStopId"] != super().eta_entry.stop:
                continue

            for eta in stop["bus"]:
                if super().details.stop_type() == StopType.ORIG:
                    time_ref = "departure"
                else:
                    time_ref = "arrival"

                if (any(char.isdigit() for char in eta[f'{time_ref}TimeText'])):
                    #  eta TimeText has numbers (e.g. 3 分鐘/3 Minutes)
                    eta_sec = int(eta[f'{time_ref}TimeInSecond'])
                    output.append({
                        'second': eta_sec,
                        'minute': eta[f'{time_ref}TimeText'].split(" ")[0],
                        'time': datetime.datetime.strftime(
                            timestamp + datetime.timedelta(seconds=eta_sec), "%H:%M"),
                        'destination': super().details.destination(),
                        'remark': ""
                    })
                else:
                    output.append({
                        'second': None,
                        'minute': None,
                        'time': None,
                        'destination': super().details.destination(),
                        'remark': eta[f'{time_ref}TimeText']
                    })
            break

        if len(output) == 0:
            raise etaex.EmptyDataError
        return output

    @etaex.aioex_to_etex
    async def raw_etas(self) -> dict[str | int]:
        #  NOTE: Currently, "status" from API always is returned 0
        #    possible due to the service is in testing stage.
        #  -------------------------------------------------------
        #  if data["status"] == "0":
        #      raise APIError
        #  elif data["routeStatusRemarkTitle"] == "停止服務":
        #      raise EndOfServices
        apidata = await api.mtr_bus_eta(
            super().eta_entry.name, super().details.lang_code())

        if len(apidata) == 0:
            raise etaex.APIError
        elif apidata["routeStatusRemarkTitle"] in ("\u505c\u6b62\u670d\u52d9", "Non-service hours"):
            raise etaex.EndOfService
        elif apidata["routeStatusRemarkTitle"] is not None:
            raise etaex.ErrorReturns(apidata["routeStatusRemarkTitle"])
        else:
            return apidata


class MtrLrtEta(EtaProcessor):

    def etas(self):
        apidata = asyncio.run(self.raw_etas())
        timestamp = self._parse_iostime(apidata['system_time'])
        lang_code = super().details.lang_code()
        output = []

        for platform in apidata['platform_list']:
            # the platform may ended service
            for eta in platform.get("route_list", []):
                # 751P have no destination and eta
                destination = eta.get(f'dest_{lang_code}')
                if (eta['route_no'] != super().eta_entry.name
                        or destination != super().details.destination()):
                    continue

                # e.g. 3 分鐘 / 即將抵達
                eta_min = eta[f'time_{lang_code}'].split(" ")[0]
                if eta_min.isnumeric():
                    eta_min = int(eta_min)
                    eta_dt = timestamp + datetime.timedelta(minutes=eta_min)
                    output.append({
                        'second': int(
                            (eta_dt - datetime.datetime.now(timestamp.tzinfo)).total_seconds()),
                        'minute': eta_min,
                        'time': datetime.datetime.strftime(eta_dt, "%H:%M"),
                        'destination': destination,
                        'remark': ""
                    })
                else:
                    output.append({
                        'second': None,
                        'minute': None,
                        'time': None,
                        'destination': destination,
                        'remark': eta_min
                    })

        if len(output) == 0:
            raise etaex.EmptyDataError
        return output

    @etaex.aioex_to_etex
    async def raw_etas(self) -> dict[str | int]:
        apidata = await api.mtr_lrt_eta(super().eta_entry.stop)

        if len(apidata) == 0 or apidata.get('status', 0) == 0:
            raise etaex.APIError
        elif all(platform.get("end_service_status", False)
                 for platform in apidata['platform_list']):
            raise etaex.EndOfService
        else:
            return apidata


class MtrTrainEta(EtaProcessor):

    __dir = {"inbound": "UP", "outbound": "DOWN"}

    def __init__(self, detail: rtdet.RouteDetails) -> None:
        super().__init__(detail)
        self.linename = super().eta_entry.name.split("-")[0]
        self.direction = self.__dir[super().eta_entry.direction]

    def etas(self) -> dict:
        apidata = asyncio.run(self.raw_etas())
        timestamp = self._parse_iostime(apidata["curr_time"])
        output = []

        etadata = apidata['data'][
            f'{self.linename}-{super().eta_entry.stop}'].get(
                self.direction, [])
        for entry in etadata:
            eta_dt = datetime.datetime.fromisoformat(entry["time"])
            output.append({
                'second': int((eta_dt - timestamp).total_seconds()),
                'minute': int((eta_dt - timestamp).total_seconds() / 60),
                'time': datetime.datetime.strftime(eta_dt, "%H:%M"),
                'destination': super().details.rt_stop_name(entry['dest']),
                'remark': ""
            })

        if len(output) == 0:
            raise etaex.EmptyDataError
        return output

    @etaex.aioex_to_etex
    async def raw_etas(self) -> dict[str | int]:
        apidata = await api.mtr_train_eta(
            self.linename, super().eta_entry.stop, super().eta_entry.lang)

        if len(apidata) == 0:
            raise etaex.APIError
        elif apidata.get('status', 0) == 0:
            if "suspended" in apidata['message']:
                raise etaex.StationClosed
            elif apidata.get('url') is not None:
                raise etaex.AbnormalService
            else:
                raise etaex.APIError
        elif apidata['data'][f'{self.linename}-{super().eta_entry.stop}'].get(
                self.direction) is None:
            raise etaex.EmptyDataError
        else:
            return apidata


class BravoBusEta(EtaProcessor):

    def etas(self) -> dict:
        apidata = asyncio.run(self.raw_etas())
        timestamp = self._parse_iostime(apidata['generated_timestamp'])
        lang_code = super().details.lang_code()
        output = []

        for eta in apidata['data']:
            if eta['dir'] != super().eta_entry.direction[0].upper():
                continue
            elif eta['eta'] == "":  # 九巴時段
                output.append({
                    'co': eta['co'],
                    'second': None,
                    'minute': None,
                    'time': None,
                    'destination': eta[f"dest_{lang_code}"],
                    'remark': eta[f"rmk_{lang_code}"]
                })
            else:
                eta_dt = datetime.datetime.fromisoformat(eta['eta'])
                output.append({
                    'co': eta['co'],
                    'second': int((eta_dt - timestamp).total_seconds()),
                    'minute': int((eta_dt - timestamp).total_seconds() / 60),
                    'time': datetime.datetime.strftime(eta_dt, "%H:%M"),
                    'destination': eta[f"dest_{lang_code}"],
                    'remark': eta[f"rmk_{lang_code}"]
                })

        if len(output) == 0:
            raise etaex.EmptyDataError
        return output

    @etaex.aioex_to_etex
    async def raw_etas(self) -> dict[str | int]:
        apidata = await api.bravobus_eta(
            super().eta_entry.co, super().eta_entry.stop, super().eta_entry.name)

        if len(apidata) == 0 or apidata.get('data') is None:
            raise etaex.APIError
        elif len(apidata['data']) == 0:
            raise etaex.EmptyDataError
        else:
            return apidata
