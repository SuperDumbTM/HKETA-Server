import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path

import pytz

try:
    from . import api_async, enums, exceptions, models, predictor, transport
    from .route import Route
except (ImportError, ModuleNotFoundError):
    import api_async
    import enums
    import exceptions
    import models
    import predictor
    import transport
    from route import Route

_GMT8_TZ = pytz.timezone('Asia/Hong_kong')


def _8601str(dt: datetime) -> str:
    """Convert a `datetime` instance to ISO-8601 formatted string."""
    return dt.isoformat(sep='T', timespec='seconds')


class EtaProcessor(ABC):
    """Public Transport ETA Retriver
    ~~~~~~~~~~~~~~~~~~~~~
    Retrive, process and unify the format of ETA(s) data
    """

    @property
    def route(self) -> Route:
        return self._route

    @route.setter
    def route(self, val):
        if not isinstance(val, Route):
            raise TypeError
        self._route = val

    def __init__(self, route: Route) -> None:
        self._route = route

    @abstractmethod
    def etas(self) -> list[dict[str, str | int]]:
        """Return processed ETAs

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


class KmbEta(EtaProcessor):

    _locale_map = {enums.Locale.TC: "tc", enums.Locale.EN: "en"}

    def etas(self):
        # [API Responses Remark]
        #   Timestamps include tzinfo (GMT+8)

        predictor_ = predictor.KmbPredictor(
            Path(__file__).parents[2].joinpath('datasets', 'kmb'),
            transport.KowloonMotorBus()
        )

        response = asyncio.run(self.raw_etas())
        timestamp = datetime.fromisoformat(response['generated_timestamp'])
        locale = self._locale_map[self.route.entry.lang]
        etas = []

        for stop in response['data']:
            if (stop["seq"] != self.route.stop_seq()
                    or stop["dir"] != self.route.entry.direction[0].upper()):
                continue
            if stop["eta"] is None:
                if stop[f'rmk_{locale}'] == "":
                    raise exceptions.EndOfService
                raise exceptions.ErrorReturns(stop[f'rmk_{locale}'])

            eta_dt = datetime.fromisoformat(stop["eta"])
            etas.append(models.Eta(
                destination=stop[f'dest_{locale}'],
                is_arriving=(eta_dt - timestamp).total_seconds() < 60,
                is_scheduled=stop.get('rmk_') in ('原定班次', 'Scheduled Bus'),
                eta=_8601str(eta_dt),
                eta_minute=int((eta_dt - timestamp).total_seconds() / 60),
                remark=stop[f'rmk_{locale}'],
                extras=models.Eta.Extras(accuracy=predictor_.predict(self.route.entry.no,
                                                                     self.route.entry.direction,
                                                                     self.route.stop_seq(),
                                                                     stop['data_timestamp'],
                                                                     stop['eta']
                                                                     )[0])
            ))

            if len(etas) == 3:
                #  NOTE: the number of ETA entry form API at the same stop may not be 3 every time.
                #  KMB only provide at most 3 upcoming ETAs
                #  (e.g. N- routes may provide only 2)
                break

        return etas

    async def raw_etas(self) -> dict[str | int]:
        response = await api_async.kmb_eta(
            self.route.entry.no, self.route.entry.service_type)

        if len(response) == 0:
            raise exceptions.APIError
        elif response.get('data') is None:
            raise exceptions.EmptyEta
        else:
            return response


class MtrBusEta(EtaProcessor):

    _locale_map = {enums.Locale.TC: "zh", enums.Locale.EN: "en"}

    def etas(self):
        # [API Responses Remark]
        #   Timestamps do not include tzinfo (GMT+8)

        response = asyncio.run(self.raw_etas())
        timestamp = datetime.strptime(response["routeStatusTime"], "%Y/%m/%d %H:%M") \
            .astimezone(_GMT8_TZ)
        etas = []

        for stop in response["busStop"]:
            if stop["busStopId"] != self.route.entry.stop:
                continue

            for eta in stop["bus"]:
                time_ref = "departure" \
                    if self.route.stop_type() == enums.StopType.ORIG \
                    else "arrival"

                if (any(char.isdigit() for char in eta[f'{time_ref}TimeText'])):
                    # eta TimeText has numbers (e.g. 3 分鐘/3 Minutes)
                    eta_sec = int(eta[f'{time_ref}TimeInSecond'])
                    etas.append(models.Eta(
                        destination=self.route.destination().name.get(self.route.entry.lang),
                        is_arriving=False,
                        is_scheduled=eta['busLocation']['longitude'] == 0,
                        eta=_8601str(timestamp + timedelta(seconds=eta_sec)),
                        eta_minute=eta[f'{time_ref}TimeText'].split(" ")[0],
                    ))
                else:
                    etas.append(models.Eta(
                        destination=self.route.destination().name.get(self.route.entry.lang),
                        is_arriving=True,
                        is_scheduled=eta['busLocation']['longitude'] == 0,
                        eta=_8601str(datetime.now().astimezone(_GMT8_TZ)),
                        eta_minute=0,
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
        response = await api_async.mtr_bus_eta(
            self.route.name(), self._locale_map[self.route.entry.lang])

        if len(response) == 0:
            raise exceptions.APIError
        elif response["routeStatusRemarkTitle"] is not None:
            if response["routeStatusRemarkTitle"] in ("\u505c\u6b62\u670d\u52d9", "Non-service hours"):
                raise exceptions.EndOfService(
                    response["routeStatusRemarkTitle"])
            raise exceptions.ErrorReturns(response["routeStatusRemarkTitle"])
        else:
            return response


class MtrLrtEta(EtaProcessor):

    _locale_map = {enums.Locale.TC: "ch", enums.Locale.EN: "en"}

    def etas(self):
        # [API Responses Remark]
        #   Timestamps do not include tzinfo (GMT+8)

        response = asyncio.run(self.raw_etas())
        timestamp = datetime.fromisoformat(response['system_time']) \
            .astimezone(_GMT8_TZ)
        lang_code = self._locale_map[self.route.entry.lang]
        etas = []

        for platform in response['platform_list']:
            # the platform may ended service
            for eta in platform.get("route_list", []):
                # 751P have no destination and eta
                destination = eta.get(f'dest_{lang_code}')
                if (eta['route_no'] != self.route.entry.no
                        or destination != self.route.destination().name.get(self.route.entry.lang)):
                    continue

                # e.g. 3 分鐘 / 即將抵達
                eta_min = eta[f'time_{lang_code}'].split(" ")[0]
                if eta_min.isnumeric():
                    eta_min = int(eta_min)

                    etas.append(models.Eta(
                        destination=destination,
                        is_arriving=False,
                        is_scheduled=False,
                        eta=_8601str(timestamp + timedelta(minutes=eta_min)),
                        eta_minute=eta_min,
                        extras=models.Eta.Extras(
                            platform=str(platform['platform_id']),
                            car_length=eta['train_length']
                        )
                    ))
                else:
                    etas.append(models.Eta(
                        destination=destination,
                        is_arriving=True,
                        is_scheduled=False,
                        eta=_8601str(datetime.now().astimezone(_GMT8_TZ)),
                        eta_minute=0,
                        remark=eta_min,
                        extras=models.Eta.Extras(
                            platform=str(platform['platform_id']),
                            car_length=eta['train_length']
                        )
                    ))

        return etas

    async def raw_etas(self) -> dict[str | int]:
        response = await api_async.mtr_lrt_eta(self.route.entry.stop)

        if len(response) == 0 or response.get('status', 0) == 0:
            raise exceptions.APIError
        elif all(platform.get("end_service_status", False)
                 for platform in response['platform_list']):
            raise exceptions.EndOfService
        else:
            return response


class MtrTrainEta(EtaProcessor):

    _bound_map = {"inbound": "UP", "outbound": "DOWN"}

    def __init__(self, route: Route) -> None:
        super().__init__(route)
        self.linename = self.route.entry.no.split("-")[0]
        self.direction = self._bound_map[self.route.entry.direction]

    def etas(self) -> dict:
        # [API Responses Remark]
        #   Timestamps do not include tzinfo (GMT+8)

        response = asyncio.run(self.raw_etas())
        timestamp = datetime.fromisoformat(response["curr_time"]) \
            .astimezone(_GMT8_TZ)
        etas = []

        etadata = response['data'][f'{self.linename}-{self.route.entry.stop}'].get(
            self.direction, [])
        for entry in etadata:
            eta_dt = datetime.fromisoformat(entry["time"]) \
                .astimezone(_GMT8_TZ)
            etas.append(models.Eta(
                destination=(self.route.stop_details(entry['dest'])
                             .name
                             .get(self.route.entry.lang)),
                is_arriving=(eta_dt - timestamp).total_seconds() < 90,
                is_scheduled=False,
                eta=_8601str(eta_dt),
                eta_minute=int((eta_dt - timestamp).total_seconds() / 60),
                extras=models.Eta.Extras(platform=entry['plat'])
            ))

        return etas

    async def raw_etas(self) -> dict[str | int]:
        response = await api_async.mtr_train_eta(self.linename,
                                                 self.route.entry.stop,
                                                 self.route.entry.lang)
        if len(response) == 0:
            raise exceptions.APIError
        if response.get('status', 0) == 0:
            if "suspended" in response['message']:
                raise exceptions.StationClosed(response['message'])
            if response.get('url') is not None:
                raise exceptions.AbnormalService(response['message'])
            raise exceptions.APIError

        if response['data'][f'{self.linename}-{self.route.entry.stop}'].get(self.direction) is None:
            raise exceptions.EmptyEta
        else:
            return response


class BravoBusEta(EtaProcessor):

    _locale_map = {enums.Locale.TC: "tc", enums.Locale.EN: "en"}

    def etas(self) -> dict:
        # [API Responses Remark]
        #   Timestamps include tzinfo (GMT+8)

        response = asyncio.run(self.raw_etas())
        timestamp = datetime.fromisoformat(response['generated_timestamp'])
        lang_code = self._locale_map[self.route.entry.lang]
        etas = []

        for eta in response['data']:
            if eta['dir'] != self.route.entry.direction[0].upper():
                continue
            if eta['eta'] == "":
                # 九巴時段
                etas.append(models.Eta(
                    destination=eta[f"dest_{lang_code}"],
                    is_arriving=False,
                    is_scheduled=True,
                    eta=None,
                    eta_minute=None,
                    remark=eta[f"rmk_{lang_code}"]
                ))
            else:
                eta_dt = datetime.fromisoformat(eta['eta'])
                etas.append(models.Eta(
                    destination=eta[f"dest_{lang_code}"],
                    is_arriving=(eta_dt - timestamp).total_seconds() < 60,
                    is_scheduled=False,
                    eta=_8601str(eta_dt),
                    eta_minute=int((eta_dt - timestamp).total_seconds() / 60),
                    remark=eta[f"rmk_{lang_code}"]
                ))

        return etas

    async def raw_etas(self) -> dict[str | int]:
        response = await api_async.bravobus_eta(self.route.entry.company.value,
                                                self.route.entry.stop,
                                                self.route.entry.no)
        if len(response) == 0 or response.get('data') is None:
            raise exceptions.APIError
        if len(response['data']) == 0:
            raise exceptions.EmptyEta
        return response


class NlbEta(EtaProcessor):

    _bound_map = {"inbound": "UP", "outbound": "DOWN"}
    _lang_map = {enums.Locale.TC: 'zh', enums.Locale.EN: 'en', }

    def __init__(self, route: Route) -> None:
        super().__init__(route)
        self.linename = self.route.entry.no.split("-")[0]
        self.direction = self._bound_map[self.route.entry.direction]

    def etas(self) -> dict:
        # [API Responses Remark]
        #   Timestamps do not tzinfo (GMT+8)

        response = asyncio.run(self.raw_etas())
        timestamp = datetime.now().astimezone(_GMT8_TZ)
        etas = []

        for eta in response['estimatedArrivals']:
            eta_dt = datetime.fromisoformat(eta['estimatedArrivalTime']) \
                .astimezone(_GMT8_TZ)

            etas.append(models.Eta(
                destination=(
                    self.route.destination().name.get(self.route.entry.lang)),
                is_arriving=(eta_dt - timestamp).total_seconds() < 60,
                is_scheduled=not (eta.get('departed') == '1'
                                  and eta.get('noGPS') == '1'),
                eta=_8601str(eta_dt),
                eta_minute=int((eta_dt - timestamp).total_seconds() / 60),
                extras=models.Eta.Extras(
                    route_variant=eta.get('routeVariantName'),)
            ))

        return etas

    async def raw_etas(self) -> dict[str | int]:
        route_id = self.route.provider.routes[self.route.entry.no] \
            .service_lookup(self.route.entry.direction,
                            self.route.entry.service_type) \
            .route_id
        response = await api_async.nlb_eta(route_id,
                                           self.route.entry.stop,
                                           self._lang_map[self.route.entry.lang])

        if len(response) == 0:
            # incorrect parameter will result in a empty json response
            raise exceptions.APIError
        if not response.get('estimatedArrivals', []):
            raise exceptions.EmptyEta(response.get('message'))
        return response
