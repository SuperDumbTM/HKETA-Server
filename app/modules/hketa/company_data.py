import asyncio
import csv
import datetime
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any, Mapping

import aiohttp

try:
    from app.modules.hketa import api, enums, models
except ImportError:
    import api
    import enums
    import models

_TODAY = datetime.date.today().strftime('%Y%m%d')
"""Today's date (YYYYMMDD)"""


class CompanyData(ABC):
    """
        # Public Transport Operation Data Retriver
        ~~~~~~~~~~~~~~~~~~~~~
        `OperatorData` is designed to retrive and store the data to local file system.

        It can work without storing the data to local.
        However, it will takes much longer time to retrive data and may fails due to API rate limit

        ---
        `fetch_route(...)` and `fetch_routes(...)` function are async functions.
        If you call those function, please call it in async fashion.

        Alternatively, `route(...)` and `routes(...)` function will handle the async call for you with additional logic
    """

    threshold: int
    """threshold to determine an file is outdated (in day)"""

    is_store: bool
    """indicator of storing routes data to local or not"""

    _root: os.PathLike
    """root directory of the respective class (company/transportation)."""

    @property
    def routes_json(self) -> os.PathLike:
        """Path to \"routes\" data file name"""
        return os.path.join(self._root, "routes.json")

    @property
    def route_directory(self) -> os.PathLike:
        """Path to \"route\" data directory"""
        return os.path.join(self._root, "routes")

    @staticmethod
    def lang_key(locale: enums.Language):
        match locale:
            case enums.Language.TC:
                return "name_tc"
            case enums.Language.EN:
                return "name_en"
            case _:
                raise KeyError(f"Undefined locale: {locale}.")

    def __init__(self, root: os.PathLike = None, store_local: bool = False, threshold: int = 30) -> None:
        if store_local and root is None:
            logging.error("No directory is provided for storing data files.")
            raise TypeError(
                "'store_local' is set to True but argument 'root' is missing")

        logging.debug(
            "Expiry threshold:\t%d\nStore to local:\t%s\nDirectory:\t%s",
            threshold, 'yes' if store_local else 'no', root)
        self.threshold = threshold
        self.is_store = store_local
        self._root = root

        if store_local and not os.path.exists(root):
            logging.info("'%s' does not exists, creating...", root)
            os.makedirs(os.path.join(root, "routes"))

    def is_outdated(self, fpath: str) -> bool:
        """Determine whether a data file is outdated.

        Args:
            fpath (str): File path

        Returns:
            bool: `true` if file not exists or outdated
        """
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                lastupd = json.load(f)['last_update']
                lastupd_unix = time.mktime(
                    datetime.datetime.strptime(lastupd, "%Y%m%d").timetuple())

                return (time.time() - lastupd_unix) > self.threshold * 24 * 60 * 60
        else:
            return True

    @abstractmethod
    async def fetch_route(self, route: models.RouteEntry) -> dict[str, Any]:
        """Retrive stop list and data of the `route`

        Returns:
            >>> example
            {
                'last_update': "YYYYMMDD",
                'data': {
                    '<stop code>': {
                        'seq': int,
                        'name_tc': str,
                        'name_en': str
                    }
                }
            }

        """

    @abstractmethod
    async def fetch_routes(self) -> dict[str, Any]:
        """Retrive all route list and data operating by the operator

        Returns:
            >>> example
            {
                'last_update': "YYYYMMDD",
                'data': {
                    '<stop code>': {
                        'seq': int,
                        'name_tc': str,
                        'name_en': str
                    }
                }
            }
        """

    def route(self, entry: models.RouteEntry) -> dict[str, Any]:
        """Retrive stop list and data of the `route`. Create/update the data file if necessary

        Args:
            entry (route_entry.RouteEntry): Target route
        """
        fpath = os.path.join(self.route_directory, self.route_fname(entry))

        if not self.is_store:
            logging.info(
                "Retiving %s route data (no store is set)", entry.name)
            return asyncio.run(self.fetch_route(entry))

        if self.is_outdated(fpath):
            logging.info(
                "%s local route data is outdated, refetching...", entry.name)

            data = asyncio.run(self.fetch_route(entry))
            self._write_route(entry, data)
            return data
        else:
            with open(fpath, "r", encoding="utf-8") as f:
                logging.debug("loading %s route data from %s",
                              entry.name, fpath)
                return json.load(f)

    def routes(self) -> dict[str, Any]:
        """Retrive all route list and data operating by the operator. Create/update when necessary
        """
        if not self.is_store:
            logging.info(
                "retiving %s routes data (no store is set)", type(self).__name__)
            return asyncio.run(self.fetch_routes())
        elif self.is_outdated(self.routes_json):
            logging.info(
                "%s local routes data is outdated or not exists, updating...", type(self).__name__)

            data = asyncio.run(self.fetch_routes())
            self._write_routes(data)
            return data
        else:
            with open(self.routes_json, "r", encoding="utf-8") as f:
                logging.debug("reading %s route data from %s",
                              type(self).__name__, self.routes_json)
                return json.load(f)

    def route_fname(self, entry: models.RouteEntry) -> str:
        """Get file name of target `entry` stop data

        Args:
            entry (route_entry.RouteEntry): Target route

        Returns:
            str: Name of the route data file 
                (e.g. "1A-outbound-1.json", "TML-outbound.json")
        """
        return f"{entry.name}-{entry.direction}.json"

    def _write_route(self, entry: models.RouteEntry, data: Mapping) -> None:
        """Write `data` (route data) to persistent storage

        Args:
            entry (route_entry.RouteEntry): The route which the `data` belongs to
            data (dict): Stop list and data of the `route`
        """
        fpath = os.path.join(self.route_directory, self.route_fname(entry))

        with open(fpath, "w", encoding="utf-8") as f:
            logging.info("writing %s route data to %s",
                         type(self).__name__, fpath)
            json.dump(data, f, indent=4)

    def _write_routes(self, data: Mapping) -> None:
        """Write `data` (routes data) to persistent storage

        Args:
            data (dict): Routes list and data of the operator
        """

        with open(self.routes_json, "w", encoding="utf-8") as f:
            logging.info("writing %s routes data to %s",
                         type(self).__name__, self.routes_json)
            json.dump(data, f, indent=4)


class KMBData(CompanyData):

    _direction = {
        'O': enums.Direction.OUTBOUND.value,
        'I': enums.Direction.INBOUND.value,
        enums.Direction.OUTBOUND.value: "I",
        enums.Direction.INBOUND.value: "O"
    }
    """direction text translation to `hketa.enums.Direction`"""

    def __init__(self, root: os.PathLike = None, store_local: bool = False, threshold: int = 30) -> None:
        super().__init__(os.path.join(root, "kmb"), store_local, threshold)

    async def fetch_routes(self) -> dict:
        async def fetch_route_details(session: aiohttp.ClientSession,
                                      stop: dict) -> dict:
            # async helper, get stop ID
            direction = self._direction[stop['bound']]
            stop_dets = (await api.kmb_route_stop_list(
                stop['route'], direction, stop['service_type'], session))['data']
            return {
                'route': stop['route'],
                'direction': direction,
                'service_type': stop['service_type'],
                'details': {
                    'orig': {
                        'stop_code': stop_dets[0]['stop'],
                        'name_tc': stop['orig_tc'],
                        'name_en': stop['orig_en']
                    },
                    'dest': {
                        'stop_code': stop_dets[-1]['stop'],
                        'name_tc': stop['dest_tc'],
                        'name_en': stop['dest_en']
                    }
                }
            }
        # generate output
        output = {'last_update': _TODAY, 'data': {}}

        async with aiohttp.ClientSession() as session:
            tasks = []
            for stop in (await api.kmb_route_list(session))['data']:
                tasks.append(fetch_route_details(session, stop))

            for entry in await asyncio.gather(*tasks):
                # route name
                output['data'].setdefault(entry['route'], {})
                # direction
                output['data'][entry['route']].setdefault(
                    entry['direction'], {})
                # service type
                output['data'][entry['route']][entry['direction']].setdefault(
                    entry['service_type'], entry['details'])
        return output

    async def fetch_route(self, route: models.RouteEntry) -> dict:
        async def fetch_stop_details(session: aiohttp.ClientSession, stop: dict):
            # async helper, get stop details
            dets = (await api.kmb_stop_details(stop['stop'], session))['data']
            return {
                stop['stop']: {
                    'seq': int(stop['seq']),
                    'name_tc': dets.get('name_tc'),
                    'name_en': dets.get('name_en')
                }
            }
        # generate output
        output = {'last_update': _TODAY, 'data': {}}

        async with aiohttp.ClientSession() as session:
            tasks = []
            for stop in (await api.kmb_route_stop_list(
                    route.name,
                    route.direction.value,
                    route.service_type, session))['data']:
                tasks.append(fetch_stop_details(session, stop))

            for entry in await asyncio.gather(*tasks):
                stop_code = list(entry.keys())[0]
                output['data'][stop_code] = entry[stop_code]
        return output

    def route_fname(self, entry: models.RouteEntry):
        return f"{entry.name}-{entry.direction}-{entry.service_type}.json"


class MTRLrtData(CompanyData):

    _direction = {
        enums.Direction.OUTBOUND.value: "1",
        enums.Direction.INBOUND.value: "2",
        '1': enums.Direction.OUTBOUND.value,
        '2': enums.Direction.INBOUND.value
    }
    """direction text translation to `hketa.enums`"""

    def __init__(self, root: os.PathLike = None, store_local: bool = False, threshold: int = 30) -> None:
        super().__init__(os.path.join(root, "mtr_lrt"), store_local, threshold)

    async def fetch_routes(self) -> dict:
        output = {'last_update': _TODAY, 'data': {}}

        apidata = csv.reader(await api.mtr_lrt_route_stop_list())
        next(apidata)  # ignore the header line

        for row in apidata:
            # [0]route, [1]direction , [2]stopCode, [3]stopID, [4]stopTCName, [5]stopENName, [6]seq
            output['data'].setdefault(row[0], {
                'outbound': {'orig': {}, 'dest': {}},
                'inbound': {'orig': {}, 'dest': {}}
            })

            direction = self._direction[row[1]]

            if (row[6] == "1.00"):  # original
                output['data'][row[0]][direction]['orig'] = {
                    'stop_code': row[3],
                    'name_tc': row[4],
                    'name_en': row[5]
                }
            else:  # destination
                output['data'][row[0]][direction]['dest'] = {
                    'stop_code': row[3],
                    'name_tc': row[4],
                    'name_en': row[5]
                }

        return output

    async def fetch_route(self, route: models.RouteEntry) -> dict:
        output = {'last_update': _TODAY, 'data': {}}

        apidata = csv.reader(await api.mtr_lrt_route_stop_list())
        stops = [stop for stop in apidata
                 if stop[0] == str(route.name)
                 and self._direction[stop[1]] == route.direction]

        for row in stops:
            # [0]route, [1]direction , [2]stopCode, [3]stopID, [4]stopTCName, [5]stopENName, [6]seq
            output['data'][row[3]] = {
                'seq': int(row[6].strip('.00')),
                'name_tc': row[4],
                'name_en': row[5]
            }

        return output


class MTRTrainData(CompanyData):

    _direction = {
        'DT': enums.Direction.DOWNLINK.value,
        'UT': enums.Direction.UPLINK.value,
        enums.Direction.DOWNLINK.value: "DT",
        enums.Direction.UPLINK.value: "UT",
    }
    """direction text translation to `hketa.enums`"""

    def __init__(self, root: os.PathLike = None, store_local: bool = False, threshold: int = 30) -> None:
        super().__init__(os.path.join(root, "mtr_train"), store_local, threshold)

    async def fetch_routes(self) -> dict:
        output = {'last_update': _TODAY, 'data': {}}

        apidata = csv.reader(await api.mtr_train_route_stop_list())
        next(apidata)  # ignore header line

        for row in apidata:
            # [0]Line Code [1]Direction [2]Station Code [3]Station ID [4]Chinese Name [5]English Name [6]Sequence
            if not any(row):  # skip empty row
                continue

            direction, _, type_ = row[1].partition("-")
            if type_:  # route with multiple origin/destination
                direction, type_ = type_, direction  # e.g. LMC-DT
                # make a "new line" for these type of route
                row[0] += f"-{type_}"
            direction = self._direction[direction]

            output['data'].setdefault(row[0], {})
            output['data'][row[0]].setdefault(direction, {})

            if (row[6] == '1'):  # origin
                output['data'][row[0]][direction]['orig'] = {
                    # 'id': row[3],
                    'stop_code': row[2],
                    'name_tc': row[4],
                    'name_en': row[5]
                }
            else:  # destination
                output['data'][row[0]][direction]['dest'] = {
                    # 'id': row[3],
                    'stop_code': row[2],
                    'name_tc': row[4],
                    'name_en': row[5]
                }

        return output

    async def fetch_route(self, route: models.RouteEntry) -> dict:
        output = {'last_update': _TODAY, 'data': {}}

        apidata = csv.reader(await api.mtr_train_route_stop_list())

        if "-" in route.name:
            # route with multiple origin/destination
            rtname, type_ = route.name.split("-")
            stops = [stop for stop in apidata
                     if stop[0] == rtname
                     and type_ in stop[1]]
        else:
            stops = [stop for stop in apidata
                     if stop[0] == str(route.name)
                     and self._direction[stop[1]] == route.direction]

        for stop in stops:
            # [0]Line Code [1]Direction [2]Station Code [3]Station ID [4]Chinese Name [5]English Name [6]Sequence
            output['data'][stop[2]] = {
                'id': stop[3],
                'seq': int(stop[-1]),
                'name_tc': stop[4],
                'name_en': stop[5]
            }

        return output


class MTRBusData(CompanyData):

    _direction = {
        'O': enums.Direction.OUTBOUND.value,
        'I': enums.Direction.INBOUND.value,
        enums.Direction.OUTBOUND.value: "I",
        enums.Direction.INBOUND.value: "O"
    }
    """direction text translation to `hketa.enums`"""

    def __init__(self, root: os.PathLike = None, store_local: bool = False, threshold: int = 30) -> None:
        super().__init__(os.path.join(root, "mtr_bus"), store_local, threshold)

    async def fetch_routes(self) -> dict:
        output = {'last_update': _TODAY, 'data': {}}

        apidata = csv.reader(await api.mtr_bus_stop_list())
        next(apidata)  # ignore header line

        for stop in apidata:
            # [0]route, [1]direction, [2]seq, [3]stopID, [4]stopLAT, [5]stopLONG, [6]stopTCName, [7]stopENName
            direction = self._direction[stop[1]]

            output['data'].setdefault(stop[0], {})
            output['data'][stop[0]].setdefault(
                direction, {'orig': {}, 'dest': {}})

            if stop[2] == "1.00":
                # orignal stop
                output['data'][stop[0]][direction]['orig'] = {
                    'stop_code': stop[3],
                    'name_tc': stop[6],
                    'name_en': stop[7]
                }
            else:
                # destination stop
                output['data'][stop[0]][direction]['dest'] = {
                    'stop_code': stop[3],
                    'name_tc': stop[6],
                    'name_en': stop[7]
                }

        return output

    async def fetch_route(self, route: models.RouteEntry) -> dict:
        output = {'last_update': _TODAY, 'data': {}}

        async with aiohttp.ClientSession() as session:
            apidata = csv.reader(await api.mtr_bus_stop_list(session))

        stops = [stop for stop in apidata
                 if stop[0] == str(route.name) and self._direction[stop[1]] == route.direction]
        for stop in stops:
            # [0]route, [1]direction, [2]seq, [3]stopID, [4]stopLAT, [5]stopLONG, [6]stopTCName, [7]stopENName
            output['data'][stop[3]] = {
                'seq': int(float(stop[2])),
                'name_tc': stop[6],
                'name_en': stop[7]
            }

        return output


class CityBusData(CompanyData):

    def __init__(self, root: os.PathLike = None, store_local: bool = False, threshold: int = 30) -> None:
        super().__init__(os.path.join(root, "ctb"), store_local, threshold)

    async def fetch_routes(self) -> dict:
        async def fetch_route_details(session: aiohttp.ClientSession,
                                      route: dict) -> dict:
            # async helper, get stop details + stop ID
            directions = {
                'inbound': (await api.bravobus_route_stop_list(
                    "ctb", route['route'], "inbound", session))['data'],
                'outbound': (await api.bravobus_route_stop_list(
                    "ctb", route['route'], "outbound", session))['data']
            }

            rtdets = {route['route']: {}}
            for direction, dets in directions.items():
                if len(dets) == 0:
                    continue
                orig = (await api.bravobus_stop_details(dets[0]['stop']))['data']
                dest = (await api.bravobus_stop_details(dets[-1]['stop']))['data']
                rtdets[route['route']].setdefault(direction, {
                    'orig': {
                        'name_tc': orig.get('name_tc', "未有資料"),
                        'name_en': orig.get('name_en', "N/A"),
                        'stop_code': dets[0]["stop"],
                    },
                    'dest': {
                        'name_tc': dest.get('name_tc', "未有資料"),
                        'name_en': dest.get('name_en', "N/A"),
                        'stop_code': dets[-1]["stop"],
                    }
                })

            return rtdets

        # generate output
        output = {'last_update': _TODAY, 'data': {}}

        async with aiohttp.ClientSession() as session:
            tasks = [fetch_route_details(session, stop) for stop in
                     (await api.bravobus_route_list("ctb", session))['data']]

            # keys()[0] = route name
            output['data'] = {list(entry.keys())[0]: entry[list(entry.keys())[0]]
                              for entry in await asyncio.gather(*tasks)}

        return output

    async def fetch_route(self, route: models.RouteEntry) -> dict:
        async def fetch_stop_details(session: aiohttp.ClientSession, stop: dict):
            # async helper, get stop details
            stopdets = (await api.bravobus_stop_details(stop['stop'], session))['data']
            return {
                stop['stop']: {
                    'seq': int(stop['seq']),
                    'name_tc': stopdets.get('name_tc', "未有資料"),
                    'name_en': stopdets.get('name_en', "N/A")
                }
            }

        # generate output
        output = {'last_update': _TODAY, 'data': {}}
        async with aiohttp.ClientSession() as session:
            tasks = []
            for stop in (await api.bravobus_route_stop_list(
                    "ctb",
                    route.name,
                    route.direction,
                    session))['data']:
                tasks.append(fetch_stop_details(session, stop))

            for entry in await asyncio.gather(*tasks):
                stop_code = list(entry.keys())[0]
                output['data'][stop_code] = entry[stop_code]

        return output
