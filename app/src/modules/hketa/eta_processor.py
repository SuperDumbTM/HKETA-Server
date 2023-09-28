import asyncio
import datetime
from abc import ABC, abstractmethod

try:
    from app.src.modules.hketa import api, enums, exceptions, facades, models
except (ImportError, ModuleNotFoundError):
    import api
    import enums
    import exceptions
    import facades
    import models


class EtaProcessor(ABC):
    """Public Transport ETA Retriver
    ~~~~~~~~~~~~~~~~~~~~~
    retrive, process and unify the format of ETA(s) data

    referer to `get_etas` for returns format

    ---
    during initialisation, `EtaProcessor` will check whether the route is exists
    or not.  If not exists, `exceptions.RouteNotExist` will be raised.
    """

    @property
    def details(self) -> facades.RouteDetails:
        return self._details

    @property
    def route_entry(self) -> models.RouteEntry:
        return self._details.eta_entry

    @staticmethod
    def dt_tostring(dt: datetime.datetime) -> str:
        return datetime.datetime.strftime(dt, "%H:%M")

    def __init__(self, detail: facades.RouteDetails) -> None:
        self._entry = detail.eta_entry
        self._details = detail

    @abstractmethod
    def etas(self) -> list[dict[str, str | int]]:
        """Get processed ETAs

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
    async def raw_etas(self) -> dict[str | int]:
        """Get the raw ETAs data from API with validity checking"""

    def _parse_iostime(self, iso8601time: str) -> datetime:
        """Parse iso 8601 fomated timestamp to `datetime` instance

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

    _locale_map = {enums.Locale.TC: "tc", enums.Locale.EN: "en"}

    def etas(self) -> dict:
        response = asyncio.run(self.raw_etas())
        timestamp = self._parse_iostime(response['generated_timestamp'])
        lang_code = self._locale_map[self.route_entry.lang]
        etas = []

        for stop in response['data']:
            if (stop["seq"] != super().details.stop_seq()
                    or stop["dir"] != super().route_entry.direction[0].upper()):
                continue
            elif stop["eta"] is None:
                if stop["rmk_" + lang_code] == "":
                    raise exceptions.EndOfService
                raise exceptions.ErrorReturns(stop["rmk_" + lang_code])
            eta_dt = datetime.datetime.fromisoformat(stop["eta"])

            etas.append(models.Eta(
                company=enums.Company[stop['co']],
                destination=stop[f'dest_{lang_code}'],
                is_arriving=False,
                time=self.dt_tostring(eta_dt),
                minute=int((eta_dt - timestamp).total_seconds() / 60),
                second=int((eta_dt - timestamp).total_seconds()),
                remark=stop[f'rmk_{lang_code}']
            ))

            if len(etas) == 3:
                #  NOTE: the number of ETA entry form API at the same stop may not be 3 every time.
                #  KMB only provide at most 3 upcoming ETAs
                #  (e.g. N routes may provide only 2)
                break

        return etas

    async def raw_etas(self) -> dict[str | int]:
        response = await api.kmb_eta(
            super().route_entry.name, super().route_entry.service_type)

        if len(response) == 0:
            raise exceptions.APIError
        elif response.get('data') is None:
            raise exceptions.EmptyDataError
        else:
            return response


class MtrBusEta(EtaProcessor):

    _locale_map = {enums.Locale.TC: "zh", enums.Locale.EN: "en"}

    def etas(self):
        response = asyncio.run(self.raw_etas())
        timestamp = datetime.datetime.strptime(
            response["routeStatusTime"], "%Y/%m/%d %H:%M")
        etas = []

        for stop in response["busStop"]:
            if stop["busStopId"] != super().route_entry.stop:
                continue

            for eta in stop["bus"]:
                if super().details.stop_type() == enums.StopType.ORIG:
                    time_ref = "departure"
                else:
                    time_ref = "arrival"

                if (any(char.isdigit() for char in eta[f'{time_ref}TimeText'])):
                    #  eta TimeText has numbers (e.g. 3 分鐘/3 Minutes)
                    eta_sec = int(eta[f'{time_ref}TimeInSecond'])
                    etas.append(models.Eta(
                        company=enums.Company.MTRBUS,
                        destination=super().details.destination(),
                        is_arriving=False,
                        time=self.dt_tostring(
                            timestamp + datetime.timedelta(seconds=eta_sec)),
                        minute=eta[f'{time_ref}TimeText'].split(" ")[0],
                        second=eta_sec,
                    ))
                else:
                    etas.append(models.Eta(
                        company=enums.Company.MTRBUS,
                        destination=super().details.destination(),
                        is_arriving=False,
                        time=self.dt_tostring(datetime.datetime.now()),
                        minute=0,
                        second=0,
                        remark=eta[f'{time_ref}TimeText']
                    ))
            break

        return etas

    async def raw_etas(self) -> dict[str | int]:
        #  NOTE: Currently, "status" from API always is returned 0
        #    possible due to the service is in testing stage.
        #  -------------------------------------------------------
        #  if data["status"] == "0":
        #      raise APIError
        #  elif data["routeStatusRemarkTitle"] == "停止服務":
        #      raise EndOfServices
        response = await api.mtr_bus_eta(
            super().route_entry.name, self._locale_map[self.route_entry.lang])

        if len(response) == 0:
            raise exceptions.APIError
        elif response["routeStatusRemarkTitle"] in ("\u505c\u6b62\u670d\u52d9", "Non-service hours"):
            raise exceptions.EndOfService
        elif response["routeStatusRemarkTitle"] is not None:
            raise exceptions.ErrorReturns(response["routeStatusRemarkTitle"])
        else:
            return response


class MtrLrtEta(EtaProcessor):

    _locale_map = {enums.Locale.TC: "ch", enums.Locale.EN: "en"}

    def etas(self):
        response = asyncio.run(self.raw_etas())
        timestamp = self._parse_iostime(response['system_time'])
        lang_code = self._locale_map[self.route_entry.lang]
        etas = []

        for platform in response['platform_list']:
            # the platform may ended service
            for eta in platform.get("route_list", []):
                # 751P have no destination and eta
                destination = eta.get(f'dest_{lang_code}')
                if (eta['route_no'] != super().route_entry.name
                        or destination != super().details.destination()):
                    continue

                # e.g. 3 分鐘 / 即將抵達
                eta_min = eta[f'time_{lang_code}'].split(" ")[0]
                if eta_min.isnumeric():
                    eta_min = int(eta_min)
                    eta_dt = timestamp + datetime.timedelta(minutes=eta_min)

                    etas.append(models.Eta(
                        company=enums.Company.MTRLRT,
                        destination=destination,
                        is_arriving=False,
                        time=self.dt_tostring(eta_dt),
                        minute=eta_min,
                        second=int(
                            (eta_dt - datetime.datetime.now(timestamp.tzinfo)).total_seconds()),
                        extras=models.Eta.ExtraInfo(
                            platform=platform['platform_id'],
                            car_length=eta['train_length']
                        )
                    ))
                else:
                    etas.append(models.Eta(
                        company=enums.Company.MTRLRT,
                        destination=destination,
                        is_arriving=True,
                        time=self.dt_tostring(datetime.datetime.now()),
                        minute=0,
                        second=0,
                        remark=eta_min,
                        extras=models.Eta.ExtraInfo(
                            platform=platform['platform_id'],
                            car_length=eta['train_length']
                        )
                    ))

        return etas

    async def raw_etas(self) -> dict[str | int]:
        response = await api.mtr_lrt_eta(super().route_entry.stop)

        if len(response) == 0 or response.get('status', 0) == 0:
            raise exceptions.APIError
        elif all(platform.get("end_service_status", False)
                 for platform in response['platform_list']):
            raise exceptions.EndOfService
        else:
            return response


class MtrTrainEta(EtaProcessor):

    _bound_map = {"inbound": "UP", "outbound": "DOWN"}

    def __init__(self, detail: facades.RouteDetails) -> None:
        super().__init__(detail)
        self.linename = super().route_entry.name.split("-")[0]
        self.direction = self._bound_map[super().route_entry.direction]

    def etas(self) -> dict:
        response = asyncio.run(self.raw_etas())
        timestamp = self._parse_iostime(response["curr_time"])
        etas = []

        etadata = response['data'][
            f'{self.linename}-{super().route_entry.stop}'].get(
                self.direction, [])
        for entry in etadata:
            eta_dt = datetime.datetime.fromisoformat(entry["time"])

            etas.append(models.Eta(
                company=enums.Company.MTRTRAIN,
                destination=super().details.rt_stop_name(
                    entry['dest']),
                is_arriving=False,
                time=self.dt_tostring(eta_dt),
                minute=int((eta_dt - timestamp).total_seconds() / 60),
                second=int((eta_dt - timestamp).total_seconds()),
                extras=models.Eta.ExtraInfo(platform=entry['plat'])
            ))

        return etas

    async def raw_etas(self) -> dict[str | int]:
        response = await api.mtr_train_eta(
            self.linename, super().route_entry.stop, super().route_entry.lang)

        if len(response) == 0:
            raise exceptions.APIError
        elif response.get('status', 0) == 0:
            if "suspended" in response['message']:
                raise exceptions.StationClosed
            elif response.get('url') is not None:
                raise exceptions.AbnormalService
            else:
                raise exceptions.APIError
        elif response['data'][f'{self.linename}-{super().route_entry.stop}'].get(
                self.direction) is None:
            raise exceptions.EmptyDataError
        else:
            return response


class BravoBusEta(EtaProcessor):

    _locale_map = {enums.Locale.TC: "tc", enums.Locale.EN: "en"}

    def etas(self) -> dict:
        response = asyncio.run(self.raw_etas())
        timestamp = self._parse_iostime(response['generated_timestamp'])
        lang_code = self._locale_map[self.route_entry.lang]
        etas = []

        for eta in response['data']:
            if eta['dir'] != super().route_entry.direction[0].upper():
                continue
            elif eta['eta'] == "":
                # 九巴時段
                etas.append(models.Eta(
                    company=enums.Company[eta['co']],
                    destination=eta[f"dest_{lang_code}"],
                    is_arriving=False,
                    time=None,
                    minute=None,
                    second=None,
                    remark=eta[f"rmk_{lang_code}"]
                ))
            else:
                eta_dt = datetime.datetime.fromisoformat(eta['eta'])

                etas.append(models.Eta(
                    company=enums.Company[eta['co']],
                    destination=eta[f"dest_{lang_code}"],
                    is_arriving=False,
                    time=self.dt_tostring(eta_dt),
                    minute=int((eta_dt - timestamp).total_seconds() / 60),
                    second=int((eta_dt - timestamp).total_seconds()),
                    remark=eta[f"rmk_{lang_code}"]
                ))

        return etas

    async def raw_etas(self) -> dict[str | int]:
        response = await api.bravobus_eta(
            super().route_entry.company.value, super().route_entry.stop, super().route_entry.name)

        if len(response) == 0 or response.get('data') is None:
            raise exceptions.APIError
        elif len(response['data']) == 0:
            raise exceptions.EmptyDataError
        else:
            return response


if __name__ == "__main__":
    import os
    import pprint

    import factories

    factory = factories.EtaFactory(os.path.join(
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "caches", "transport_data"),
        True
    )

    mtb_entry = entry = models.RouteEntry(
        enums.Company.MTRBUS,
        "K76",
        enums.Direction.INBOUND,
        "K76-D020",
        None,
        enums.Locale.TC
    )

    lrt_entry = models.RouteEntry(
        enums.Company.MTRLRT,
        "705",
        enums.Direction.INBOUND,
        "510",
        "1",
        enums.Locale.TC
    )

    lrt_entry = models.RouteEntry(
        enums.Company.MTRTRAIN,
        "TML",
        enums.Direction.INBOUND,
        "TIS",
        None,
        enums.Locale.TC
    )

    ctb_entry = models.RouteEntry(
        enums.Company.CTB,
        "948",
        enums.Direction.INBOUND,
        "001193",
        "1",
        enums.Locale.TC
    )

    pprint.pprint(factory.create_eta_processor(mtb_entry).etas())
