import asyncio
import csv
import io
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Generator, Optional

import aiohttp

try:
    from . import api_async, enums, exceptions, models
except ImportError:
    import api_async
    import enums
    import exceptions
    import models

_DIRLOGO = os.path.join(os.path.dirname(__file__), "logo", "mono_neg")
_TODAY = datetime.utcnow().isoformat(timespec="seconds")
"""Today's date (ISO-8601 datetime)"""


def singleton(cls):
    instances = {}

    def wrapper(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return wrapper


class _DataclassJSONEncoder(json.JSONEncoder):
    """Encoder with dataclass support

    Reference: https://stackoverflow.com/a/51286749
    """

    def default(self, o):
        if is_dataclass(o):
            return asdict(o)
        return super().default(o)


class Transport(ABC):
    """
        Public Transport
        ~~~~~~~~~~~~~~~~~~~~~
        `Transport` representing a public transport company, providing
        information related to the company, mainly operating routes' information

        All child of of `Transport` is implemented as singleton.

        ---
        Language of information returns depends on the `RouteEntry` (if applicatable)

        ---
        Args:
            route_data (RouteData): RouteData instance for `Transport` retriving routes information
    """

    __path_prefix__: Optional[str]

    @property
    @abstractmethod
    def company(self) -> enums.Company:
        pass

    @property
    def route_list_path(self) -> Path:
        """Path to \"routes\" data file name"""
        return self._root.joinpath('routes.json')

    @property
    def stops_list_dir(self) -> Path:
        """Path to \"route\" data directory"""
        return self._root.joinpath('routes')

    @classmethod
    def _put_data_file(cls, path: os.PathLike, data) -> None:
        """Write `data` to local file system.
        """
        path = Path(str(path))
        if not path.parent.exists():
            os.makedirs(path.parent)

        with open(path, "w", encoding="utf-8") as f:
            logging.info("Saving %s data to %s", type(cls).__name__, path)
            json.dump({'last_update': _TODAY, 'data': data},
                      f,
                      indent=4,
                      cls=_DataclassJSONEncoder)

    def __init__(self,
                 root: os.PathLike[str] = None,
                 store_local: bool = False,
                 threshold: int = 30) -> None:
        if store_local and root is None:
            raise TypeError("No directory is provided for storing data files.")

        logging.debug(
            "Expiry threshold:\t%d\nStore to local:\t%s\nDirectory:\t%s",
            threshold, 'yes' if store_local else 'no', root)

        self._root = Path(str(root)).joinpath(self.__path_prefix__)
        self.is_store = store_local
        self.threshold = threshold

        if store_local and not self._root.exists():
            logging.info("'%s' does not exists, creating...", root)
            os.makedirs(self.stops_list_dir)

        self.routes = self.route_list()

    @abstractmethod
    def logo(self) -> io.BufferedReader:
        """Get the company logo in bytes"""

    @abstractmethod
    async def fetch_route_list(self) -> dict[str, dict[str, list]]:
        """Fetch the route list and route details from API

        Returns:
            >>> example
            {
                '<route name>': {
                    'inbound': [{
                        'service_type': str,
                        'seq': int,
                        'name': {
                            '<locale>': str
                        }    
                    }],
                    'outbound': list
                }
            }
        """

    @abstractmethod
    async def fetch_stop_list(self, entry: models.RouteEntry) -> list[dict[str, Any]]:
        """Fetch the stop list of a the `entry` and stop details from API

        Returns:
            >>> example
                [{
                    'stop_code': str
                    'seq': int,
                    'name': {
                        '<locale>': str
                    }
                }]

        """

    def stop_list(self, entry: models.RouteEntry) -> Generator[models.RouteInfo.Stop, None, None]:
        """Retrive stop list and data of the `route`.

        Create/update local cache when necessary.

        Args:
            entry (route_entry.RouteEntry): Target route
        """
        fpath = os.path.join(self.stops_list_dir, self.route_fname(entry))

        if not self.is_store:
            logging.info("Retiving %s route data (no store is set)",
                         entry.name)
            stops = asyncio.run(self.fetch_stop_list(entry))
        elif self._is_outdated(fpath):
            logging.info("%s stop list cache is outdated, updating...",
                         entry.name)

            stops = asyncio.run(self.fetch_stop_list(entry))
            self._put_data_file(self.stops_list_dir.joinpath(self.route_fname(entry)),
                                stops)
        else:
            with open(fpath, "r", encoding="utf-8") as f:
                logging.debug("Loading %s stop list from %s",
                              entry.name,
                              fpath)
                stops = json.load(f)['data']
        return (models.RouteInfo.Stop(**stop) for stop in stops)

    def route_list(self) -> dict[str, models.RouteInfo]:
        """Retrive all route list and data operating by the operator.

        Create/update local cache when necessary.
        """
        if not self.is_store:
            logging.info("retiving %s routes data (no store is set)",
                         type(self).__name__)
            routes = asyncio.run(self.fetch_route_list())
        elif self._is_outdated(self.route_list_path):
            logging.info("%s route list cache is outdated or not exists, updating...",
                         type(self).__name__)

            routes = asyncio.run(self.fetch_route_list())
            self._put_data_file(self.route_list_path, routes)
        else:
            with open(self.route_list_path, "r", encoding="utf-8") as f:
                logging.debug("Loading route list stop list from %s",
                              self.route_list_path)
                routes = json.load(f)['data']

        return {
            route: models.RouteInfo(
                company=self.company,
                name=route,
                inbound=[
                    models.RouteInfo.Detail(
                        service_type=rt_type['service_type'],
                        orig=models.RouteInfo.Stop(
                            stop_code=rt_type['orig']['stop_code'],
                            seq=rt_type['orig']['seq'],
                            name={
                                enums.Locale[locale.upper()]: text for locale, text in rt_type['orig']['name'].items()}
                        ),
                        dest=models.RouteInfo.Stop(
                            stop_code=rt_type['dest']['stop_code'],
                            seq=rt_type['dest']['seq'],
                            name={
                                enums.Locale[locale.upper()]: text for locale, text in rt_type['dest']['name'].items()}
                        ) if rt_type['dest'] else None
                    ) for rt_type in direction['inbound']
                ],
                outbound=[
                    models.RouteInfo.Detail(
                        service_type=rt_type['service_type'],
                        orig=models.RouteInfo.Stop(
                            stop_code=rt_type['orig']['stop_code'],
                            seq=rt_type['orig']['seq'],
                            name={
                                enums.Locale[locale.upper()]: text for locale, text in rt_type['orig']['name'].items()}
                        ),
                        dest=models.RouteInfo.Stop(
                            stop_code=rt_type['dest']['stop_code'],
                            seq=rt_type['dest']['seq'],
                            name={
                                enums.Locale[locale.upper()]: text for locale, text in rt_type['dest']['name'].items()}
                        )
                    ) for rt_type in direction['outbound']
                ]
            ) for route, direction in routes.items()
        }

    def route_fname(self, entry: models.RouteEntry) -> str:
        """Get file name of target `entry` stop data

        Args:
            entry (route_entry.RouteEntry): Target route

        Returns:
            str: Name of the route data file 
                (e.g. "1A-outbound-1.json", "TML-outbound.json")
        """
        return f"{entry.name}-{entry.direction.value}-{entry.service_type}.json"

    def _is_outdated(self, fpath: os.PathLike) -> bool:
        """Determine whether a data file is outdated.

        Args:
            fpath (str): File path

        Returns:
            bool: `true` if file not exists or outdated
        """
        fpath = Path(str(fpath))
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                lastupd = datetime.fromisoformat(json.load(f)['last_update'])
                return (datetime.utcnow() - lastupd).days > self.threshold
        else:
            return True


@singleton
class KowloonMotorBus(Transport):
    __path_prefix__ = "kmb"

    _bound_map = {
        'O': enums.Direction.OUTBOUND.value,
        'I': enums.Direction.INBOUND.value,
    }
    """Direction mapping to `hketa.enums.Direction`"""

    @property
    def company(self) -> enums.Company:
        return enums.Company.KMB

    async def fetch_route_list(self) -> dict:
        async def fetch_route_details(session: aiohttp.ClientSession,
                                      stop: dict) -> dict:
            """Fetch the terminal stops details (all direction) for the `stop`
            """
            direction = self._bound_map[stop['bound']]
            stop_list = (await api_async.kmb_route_stop_list(
                stop['route'], direction, stop['service_type'], session))['data']
            return {
                'name': stop['route'],
                'direction': direction,
                'terminal': {
                    'service_type': stop['service_type'],
                    'orig': {
                        'stop_code': stop_list[0]['stop'],
                        'seq': int(stop_list[0]['seq']),
                        'name': {
                            enums.Locale.EN.value: stop.get('orig_en', "N/A"),
                            enums.Locale.TC.value:  stop.get('orig_tc', "未有資料"),
                        }
                    },
                    'dest': {
                        'stop_code': stop_list[-1]['stop'],
                        'seq': int(stop_list[-1]['seq']),
                        'name': {
                            enums.Locale.EN.value: stop.get('dest_en', "N/A"),
                            enums.Locale.TC.value:  stop.get('dest_tc', "未有資料"),
                        }
                    }
                }
            }

        route_list = {}
        async with aiohttp.ClientSession() as session:
            tasks = (fetch_route_details(session, stop)
                     for stop in (await api_async.kmb_route_list(session))['data'])

            for route in await asyncio.gather(*tasks):
                # route name
                route_list.setdefault(
                    route['name'], {'inbound': [], 'outbound': []})
                # service type
                route_list[route['name']][route['direction']].append(
                    route['terminal'])
        return route_list

    async def fetch_stop_list(self, entry: models.RouteEntry) -> dict:
        async def fetch_stop_details(session: aiohttp.ClientSession, stop: dict):
            """Fetch `stop_code`, `seq`, `name` of the 'stop'
            """
            dets = (await api_async.kmb_stop_details(stop['stop'], session))['data']
            return {
                'stop_code': stop['stop'],
                'seq': stop['seq'],
                'name': {
                    enums.Locale.TC.value: dets.get('name_tc'),
                    enums.Locale.EN.value: dets.get('name_en'),
                }
            }

        async with aiohttp.ClientSession() as session:
            stop_list = await api_async.kmb_route_stop_list(
                entry.name, entry.direction.value, entry.service_type, session)

            stops = await asyncio.gather(
                *[fetch_stop_details(session, stop) for stop in stop_list['data']])

            if len(stops) == 0:
                raise exceptions.RouteNotExist()
            return stops

    def route_fname(self, entry: models.RouteEntry):
        return f"{entry.name}-{entry.direction.value}-{entry.service_type}.json"

    def logo(self) -> io.BufferedReader:
        return open(os.path.join(_DIRLOGO, "kmb.bmp"), "rb")

    def origin(self, entry: models.RouteEntry):
        try:
            return self.routes[entry.name] \
                .service_lookup(entry.direction, entry.service_type) \
                .orig.name[entry.lang]
        except KeyError:
            return "-----"

    def orig_stopcode(self, entry: models.RouteEntry):
        return self.routes[entry.name] \
            .service_lookup(entry.direction, entry.service_type) \
            .orig.stop_code

    def destination(self, entry: models.RouteEntry):
        try:
            return self.routes[entry.name] \
                .service_lookup(entry.direction, entry.service_type) \
                .dest.name[entry.lang]
        except KeyError:
            return "-----"

    def dest_stopcode(self, entry: models.RouteEntry):
        return self.routes[entry.name] \
            .service_lookup(entry.direction, entry.service_type) \
            .dest.stop_code


@singleton
class MTRBus(Transport):
    __path_prefix__ = "mtr_bus"

    _bound_map = {
        'O': enums.Direction.OUTBOUND.value,
        'I': enums.Direction.INBOUND.value,
    }
    """Direction mapping to `hketa.enums.Direction`"""

    @property
    def company(self) -> enums.Company:
        return enums.Company.MTRBUS

    async def fetch_route_list(self) -> dict:
        route_list = {}
        apidata = csv.reader(await api_async.mtr_bus_stop_list())
        next(apidata)  # ignore header line

        for row in apidata:
            # column definition:
            # route, direction, seq, stopID, stopLAT, stopLONG, stopTCName, stopENName
            direction = self._bound_map[row[1]]
            route_list.setdefault(row[0], {'inbound': [], 'outbound': []})

            if row[2] == "1.00":
                # orignal
                route_list[row[0]][direction].append(
                    {
                        'service_type': "default",
                        'orig': {
                            'stop_code': row[3],
                            'seq': int(row[2].strip(".00")),
                            'name': {enums.Locale.EN: row[7], enums.Locale.TC: row[6]}
                        },
                        'dest': {}
                    }
                )
            else:
                # destination
                route_list[row[0]][direction][0]['dest'] = {
                    'stop_code': row[3],
                    'seq': int(row[2].strip(".00")),
                    'name': {enums.Locale.EN: row[7], enums.Locale.TC: row[6]}
                }
        return route_list

    async def fetch_stop_list(self, entry: models.RouteEntry) -> dict:
        if (entry.service_type != "default"):
            raise exceptions.RouteNotExist(
                f"Invalid service type: {entry.service_type}")

        async with aiohttp.ClientSession() as session:
            apidata = csv.reader(await api_async.mtr_bus_stop_list(session))

        stops = [stop for stop in apidata
                 if stop[0] == str(entry.name) and self._bound_map[stop[1]] == entry.direction]

        if len(stops) == 0:
            raise exceptions.RouteNotExist()
        return [{'stop_code': stop[3],
                 'seq': int(stop[2].strip(".00")),
                 'name': {enums.Locale.TC: stop[6], enums.Locale.EN: stop[7]}
                 } for stop in stops]

    def logo(self) -> io.BufferedReader:
        return open(os.path.join(_DIRLOGO, "mtr_bus.bmp"), "rb")


@singleton
class MTRLightRail(Transport):
    __path_prefix__ = 'mtr_lrt'

    _bound_map = {
        '1': enums.Direction.OUTBOUND.value,
        '2': enums.Direction.INBOUND.value
    }
    """Direction mapping to `hketa.enums.Direction`"""

    @property
    def company(self) -> enums.Company:
        return enums.Company.MTRLRT

    async def fetch_route_list(self) -> dict:
        route_list = {}
        apidata = csv.reader(await api_async.mtr_lrt_route_stop_list())
        next(apidata)  # ignore the header line

        for row in apidata:
            # column definition:
            # route, direction , stopCode, stopID, stopTCName, stopENName, seq
            direction = self._bound_map[row[1]]
            route_list.setdefault(row[0], {'inbound': [], 'outbound': []})

            if (row[6] == "1.00"):
                # original
                route_list[row[0]][direction].append(
                    {'service_type': "default"})
                route_list[row[0]][direction][0]['orig'] = {
                    'stop_code': row[3],
                    'seq': row[6],
                    'name': {enums.Locale.EN: row[5], enums.Locale.TC: row[4]}
                }
            else:
                # destination
                route_list[row[0]][direction][0]['dest'] = {
                    'stop_code': row[3],
                    'seq': row[6],
                    'name': {enums.Locale.EN.value: row[5], enums.Locale.TC.value: row[4]}
                }
        return route_list

    async def fetch_stop_list(self, entry: models.RouteEntry) -> dict:
        if (entry.service_type != "default"):
            raise exceptions.RouteNotExist(
                f"Invalid service type: {entry.service_type}")

        apidata = csv.reader(await api_async.mtr_lrt_route_stop_list())
        stops = [stop for stop in apidata
                 if stop[0] == str(entry.name)
                 and self._bound_map[stop[1]] == entry.direction]

        if len(stops) == 0:
            raise exceptions.RouteNotExist()
        return [{'stop_code': stop[3],
                 'seq': int(stop[6].strip('.00')),
                 'name': {enums.Locale.TC.value: stop[4], enums.Locale.EN.value: stop[5]}
                 } for stop in stops]

    def logo(self) -> io.BufferedReader:
        return open(os.path.join(_DIRLOGO, "mtr_lrt.bmp"), "rb")

    def destination(self, entry: models.RouteEntry):
        # NOTE: in/outbound of circular routes are NOT its destination
        # NOTE: 705, 706 return "天水圍循環綫"/'TSW Circular' instead of its destination
        try:
            if entry.name in ("705", "706"):
                return "天水圍循環綫" if entry.lang == enums.Locale.TC else "TSW Circular"
            else:
                return self.routes[entry.name].bound(entry.direction)[0].dest.name[entry.lang]
        except KeyError:
            return "-----"


@singleton
class MTRTrain(Transport):
    __path_prefix__ = 'mtr_train'

    _bound_map = {
        'DT': enums.Direction.DOWNLINK.value,
        'UT': enums.Direction.UPLINK.value,
    }
    """Direction mapping to `hketa.enums.Direction`"""

    @property
    def company(self) -> enums.Company:
        return enums.Company.MTRTRAIN

    async def fetch_route_list(self) -> dict:
        route_list = {}
        apidata = csv.reader(await api_async.mtr_train_route_stop_list())
        next(apidata)  # ignore header line

        for row in apidata:
            # column definition:
            # Line Code, Direction, Station Code, Station ID, Chinese Name, English Name, Sequence
            if not any(row):  # skip empty row
                continue

            direction, _, rt_type = row[1].partition("-")
            if rt_type:
                # route with multiple origin/destination
                direction, rt_type = rt_type, direction  # e.g. LMC-DT
                # make a "new line" for these type of route
                row[0] += f"-{rt_type}"
            direction = self._bound_map[direction]
            route_list.setdefault(row[0], {'inbound': [], 'outbound': []})

            if (row[6] == "1.00"):
                # origin
                route_list[row[0]][direction].append(
                    {
                        'service_type': "default",
                        'orig': {
                            'stop_code': row[2],
                            'seq': int(row[6].strip(".00")),
                            'name': {enums.Locale.EN.value: row[5], enums.Locale.TC.value: row[4]}
                        },
                        'dest': {}
                    }
                )
            else:
                # destination
                route_list[row[0]][direction][0]['dest'] = {
                    'stop_code': row[2],
                    'seq': int(row[6].strip(".00")),
                    'name': {enums.Locale.EN.value: row[5], enums.Locale.TC.value: row[4]}
                }
        return route_list

    async def fetch_stop_list(self, entry: models.RouteEntry) -> dict:
        if (entry.service_type != "default"):
            raise exceptions.RouteNotExist(
                f"Invalid service type: {entry.service_type}")

        apidata = csv.reader(await api_async.mtr_train_route_stop_list())

        if "-" in entry.name:
            # route with multiple origin/destination (e.g. EAL-LMC)
            rt_name, rt_type = entry.name.split("-")
            stops = [stop for stop in apidata
                     if stop[0] == rt_name and rt_type in stop[1]]
        else:
            stops = [stop for stop in apidata
                     if stop[0] == str(entry.name)
                     and self._bound_map[stop[1].split("-")[-1]] == entry.direction]
            # stop[1] (direction) could contain not just the direction (e.g. LMC-DT)

        if len(stops) == 0:
            raise exceptions.StopNotExist(entry.stop)
        return [{'stop_code': stop[2],
                 'seq': int(stop[-1].strip('.00')),
                 'name': {enums.Locale.TC.value: stop[4], enums.Locale.EN.value: stop[5]}
                 } for stop in stops]

    def logo(self) -> io.BufferedReader:
        return open(os.path.join(_DIRLOGO, "mtr_train.bmp"), "rb")


class CityBus(Transport):
    __path_prefix__ = 'ctb'

    @property
    def company(self) -> enums.Company:
        return enums.Company.CTB

    async def fetch_route_list(self) -> dict:
        async def fetch_route_details(session: aiohttp.ClientSession,
                                      route: dict) -> dict:
            """Fetch the terminal stops details (all direction) for the `route`
            """
            directions = {
                'inbound': (await api_async.bravobus_route_stop_list(
                    "ctb", route['route'], "inbound", session))['data'],
                'outbound': (await api_async.bravobus_route_stop_list(
                    "ctb", route['route'], "outbound", session))['data']
            }

            routes = {route['route']: {'inbound': [], 'outbound': []}}
            for direction, stop_list in directions.items():
                if len(stop_list) == 0:
                    continue

                ends = await asyncio.gather(*[
                    api_async.bravobus_stop_details(stop_list[0]['stop']),
                    api_async.bravobus_stop_details(stop_list[-1]['stop'])
                ])

                routes[route['route']][direction] = [{
                    'service_type': "default",
                    'orig': {
                        'stop_code': stop_list[0]['stop'],
                        'seq': stop_list[0]['seq'],
                        'name': {
                            enums.Locale.EN.value: ends[0]['data'].get('name_en', "N/A"),
                            enums.Locale.TC.value:  ends[0]['data'].get('name_tc', "未有資料"),
                        }
                    },
                    'dest': {
                        'stop_code': stop_list[-1]['stop'],
                        'seq': stop_list[-1]['seq'],
                        'name': {
                            enums.Locale.EN.value: ends[-1]['data'].get('name_en', "N/A"),
                            enums.Locale.TC.value:  ends[-1]['data'].get('name_tc', "未有資料"),
                        }
                    }
                }]
            return routes

        async with aiohttp.ClientSession() as session:
            tasks = [fetch_route_details(session, stop) for stop in
                     (await api_async.bravobus_route_list("ctb", session))['data']]

            # keys()[0] = route name
            return {list(route.keys())[0]: route[list(route.keys())[0]]
                    for route in await asyncio.gather(*tasks)}

    async def fetch_stop_list(self, entry: models.RouteEntry) -> dict:
        if (entry.service_type != "default"):
            raise exceptions.RouteNotExist(
                f"Invalid service type: {entry.service_type}")

        async def fetch_stop_details(session: aiohttp.ClientSession, stop: dict):
            """Fetch `stop_code`, `seq`, `name` of the 'stop'"""
            dets = (await api_async.bravobus_stop_details(stop['stop'], session))['data']
            return {
                'stop_code': stop['stop'],
                'seq': int(stop['seq']),
                'name': {
                    enums.Locale.EN.value: dets.get('name_en', "N/A"),
                    enums.Locale.TC.value: dets.get('name_tc', "未有資料")
                }
            }

        async with aiohttp.ClientSession() as session:
            stop_list = await api_async.bravobus_route_stop_list(
                "ctb", entry.name, entry.direction.value, session)

            stop_list = await asyncio.gather(
                *[fetch_stop_details(session, stop) for stop in stop_list['data']])

            if len(stop_list) == 0:
                raise exceptions.RouteNotExist()
            return stop_list

    def logo(self) -> io.BufferedReader:
        return open(os.path.join(_DIRLOGO, "ctb.bmp"), "rb")
