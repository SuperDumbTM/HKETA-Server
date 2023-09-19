import logging
import os
import json
import csv
import time
import datetime
import asyncio
import aiohttp
from abc import ABC, abstractmethod

try:
    import api
    import enums as etaenums
    from route_entry import RouteEntry
except ImportError:
    from . import api
    from . import enums as etaenums
    from .route_entry import RouteEntry


ROUTEDIR = "route"
"""\"route\" file directory name"""

RTJSON = "routes.json"
"""\"routes\" data file name"""


class OperatorData(ABC):
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

    today = datetime.date.today().strftime('%Y%m%d')
    """string repersentation of today date (YYYYMMDD)"""

    threshold: int
    """threshold to determine an file is outdated (in day)"""

    _dirpath: str
    """root directory of the respective class (company/transportation).
    """

    _store: bool
    """indicator of storing routes data to local or not"""

    @staticmethod
    def lang_key(locale: etaenums.Language):
        match locale:
            case etaenums.Language.TC:
                return "name_tc"
            case etaenums.Language.EN:
                return "name_en"
            case _:
                raise KeyError(f"undefined locale: {locale}")

    def __init__(self,
                 root: os.PathLike,
                 dir_name: os.PathLike,
                 store_local: bool = True,
                 threshold: int = 30) -> None:
        if store_local and root is None:
            logging.error(f"no directory is provided for storing data files")
            raise TypeError(
                "'store_local' is set to True but argument 'root' is missing")

        logging.debug(f"expiry threshold is set to {threshold}")
        self.threshold = threshold
        logging.debug(f"store_local is set to {store_local}")
        self._store = store_local

        if self._store:
            if not os.path.exists(root):
                logging.info(f"{root} does not exists, creating...")
                os.mkdir(root)

            # path of the data directory
            self._dirpath = os.path.join(root, dir_name)
            if not os.path.exists(os.path.join(self._dirpath, ROUTEDIR)):
                logging.info(f"{os.path.join(self._dirpath, ROUTEDIR)} "
                             "does not exists, creating...")
                os.makedirs(os.path.join(self._dirpath, ROUTEDIR))

    def is_outdated(self, fpath: str) -> bool:
        """Determine whether the file is outdated.

        Args:
            fpath (str): File path

        Returns:
            bool: `true` if file not exists or outdated
        """
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                lastupd = json.load(f)['lastupdate']
                lastupd_unix = time.mktime(
                    datetime.datetime.strptime(lastupd, "%Y%m%d").timetuple())

                unix_diff = time.time() - lastupd_unix
                return True if unix_diff > self.threshold * 24 * 60 * 60 else False
        else:
            return True

    @abstractmethod
    async def fetch_route(self, route: RouteEntry) -> dict:
        """Retrive stop list and data of the `route`

        Returns:
            >>> example
            {
                'lastupdate': "YYYYMMDD",
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
    async def fetch_routes(self) -> dict:
        """Retrive all route list and data operating by the operator

        Returns:
            >>> example
            {
                'lastupdate': "YYYYMMDD",
                'data': {
                    '<stop code>': {
                        'seq': int,
                        'name_tc': str,
                        'name_en': str
                    }
                }
            }
        """

    def route(self, entry: RouteEntry) -> dict:
        """Retrive stop list and data of the `route`. Create/update the data file if necessary

        Args:
            route (RouteEntry): Target route
        """
        if not self._store:
            logging.info(
                f"retiving  {entry.name} route data (no store is set)")

            return asyncio.run(self.fetch_route(entry))
        elif self.is_outdated(os.path.join(self._dirpath,
                                           ROUTEDIR,
                                           self.route_fname(entry))):
            logging.info(
                f"{entry.name} local route data is outdated, refetching...")

            data = asyncio.run(self.fetch_route(entry))
            self._write_route(entry, data)
            return data
        else:
            fpath = os.path.join(self._dirpath,
                                 ROUTEDIR,
                                 self.route_fname(entry))
            with open(fpath, "r", encoding="utf-8") as f:
                logging.debug(
                    f"loading {entry.name} route data from {fpath}")

                return json.load(f)

    def routes(self) -> dict:
        """Retrive all route list and data operating by the operator. Create/update when necessary
        """
        if not self._store:
            logging.info(
                f"retiving {type(self).__name__} routes data (no store is set)")

            return asyncio.run(self.fetch_routes())
        elif self.is_outdated(os.path.join(self._dirpath, RTJSON)):
            logging.info(
                f"{type(self).__name__} "
                "local routes data is outdated or not exists, updating...")

            data = asyncio.run(self.fetch_routes())
            self._write_routes(data)
            return data
        else:
            fpath = os.path.join(self._dirpath, RTJSON)
            with open(fpath, "r", encoding="utf-8") as f:
                logging.debug(
                    f"reading {type(self).__name__} route data from {fpath}")

                return json.load(f)

    def route_fname(self, entry: RouteEntry):
        """Get file name of target `entry` stop data

        Args:
            entry (RouteEntry): Target route

        Returns:
            str: Name of the route data file 
                (e.g. "1A-outbound-1.json", "TML-outbound.json")
        """
        return f"{entry.name}-{entry.direction}.json"

    def _write_route(self, route: RouteEntry, data: dict) -> None:
        """Write `data` (route data) to persistent storage

        Args:
            route (RouteEntry): Route that the `data` belongs to
            data (dict): Stop list and data of the `route`
        """
        fpath = os.path.join(
            self._dirpath, ROUTEDIR, self.route_fname(route))
        with open(fpath, "w", encoding="utf-8") as f:
            logging.info(
                f"writing {type(self).__name__} route data to {fpath} ")
            json.dump(data, f)

    def _write_routes(self, data: dict) -> None:
        """Write `data` (routes data) to persistent storage

        Args:
            data (dict): Routes list and data of the operator
        """

        fpath = os.path.join(self._dirpath, RTJSON)
        with open(fpath, "w", encoding="utf-8") as f:
            logging.info(
                f"writing {type(self).__name__} routes list to {fpath}")
            json.dump(data, f)


class KMBData(OperatorData):

    _direction = {
        'O': etaenums.Direction.OUTBOUND.value,
        'I': etaenums.Direction.INBOUND.value,
        etaenums.Direction.OUTBOUND.value: "I",
        etaenums.Direction.INBOUND.value: "O"
    }
    """direction text translation to `hketa.enums.Direction`"""

    def __init__(self, **kwargs) -> None:
        kwargs['dir_name'] = "kmb"
        super().__init__(**kwargs)

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
        output = {'lastupdate': super().today, 'data': {}}

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

    async def fetch_route(self, route: RouteEntry) -> dict:
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
        output = {'lastupdate': super().today, 'data': {}}

        async with aiohttp.ClientSession() as session:
            tasks = []
            for stop in (await api.kmb_route_stop_list(
                    route.name,
                    route.direction,
                    route.service_type, session))['data']:
                tasks.append(fetch_stop_details(session, stop))

            for entry in await asyncio.gather(*tasks):
                stop_code = list(entry.keys())[0]
                output['data'][stop_code] = entry[stop_code]
        return output

    def route_fname(self, route: RouteEntry):
        return f"{route.name}-{route.direction}-{route.service_type}.json"


class MTRLrtData(OperatorData):

    _direction = {
        etaenums.Direction.OUTBOUND.value: "1",
        etaenums.Direction.INBOUND.value: "2",
        '1': etaenums.Direction.OUTBOUND.value,
        '2': etaenums.Direction.INBOUND.value
    }
    """direction text translation to `hketa.enums`"""

    def __init__(self, **kwargs) -> None:
        kwargs['dir_name'] = os.path.join("mtr", "lrt")
        super().__init__(**kwargs)

    async def fetch_routes(self) -> dict:
        output = {'lastupdate': super().today, 'data': {}}

        apidata = csv.reader(await api.mtr_lrt_route_stop_list())
        next(apidata)  # ignore header line

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

    async def fetch_route(self, route: RouteEntry) -> dict:
        output = {'lastupdate': super().today, 'data': {}}

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


class MTRTrainData(OperatorData):

    _direction = {
        'DT': etaenums.Direction.DOWNLINK.value,
        'UT': etaenums.Direction.UPLINK.value,
        etaenums.Direction.DOWNLINK.value: "DT",
        etaenums.Direction.UPLINK.value: "UT",
    }
    """direction text translation to `hketa.enums`"""

    def __init__(self, **kwargs) -> None:
        kwargs['dir_name'] = os.path.join("mtr", "train")
        super().__init__(**kwargs)

    async def fetch_routes(self) -> dict:
        output = {'lastupdate': super().today, 'data': {}}

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

    async def fetch_route(self, route: RouteEntry) -> dict:
        output = {'lastupdate': super().today, 'data': {}}

        apidata = csv.reader(await api.mtr_train_route_stop_list())

        if "-" in route.name:  # route with multiple origin/destination
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


class MTRBusData(OperatorData):

    _direction = {
        'O': etaenums.Direction.OUTBOUND.value,
        'I': etaenums.Direction.INBOUND.value,
        etaenums.Direction.OUTBOUND.value: "I",
        etaenums.Direction.INBOUND.value: "O"
    }
    """direction text translation to `hketa.enums`"""

    def __init__(self, **kwargs) -> None:
        kwargs['dir_name'] = os.path.join("mtr", "bus")
        super().__init__(**kwargs)

    async def fetch_routes(self) -> dict:
        output = {'lastupdate': super().today, 'data': {}}

        apidata = csv.reader(await api.mtr_bus_stop_list())
        next(apidata)  # ignore header line

        for stop in apidata:
            # [0]route, [1]direction, [2]seq, [3]stopID, [4]stopLAT, [5]stopLONG, [6]stopTCName, [7]stopENName
            direction = self._direction[stop[1]]

            output['data'].setdefault(stop[0], {})
            output['data'][stop[0]].setdefault(
                direction, {'orig': {}, 'dest': {}})

            if (stop[2] == "1"):  # orignal
                output['data'][stop[0]][direction]['orig'] = {
                    'stop_code': stop[3],
                    'name_tc': stop[6],
                    'name_en': stop[7]
                }
            else:  # destination
                output['data'][stop[0]][direction]['dest'] = {
                    'stop_code': stop[3],
                    'name_tc': stop[6],
                    'name_en': stop[7]
                }

        return output

    async def fetch_route(self, route: RouteEntry) -> dict:
        output = {'lastupdate': super().today, 'data': {}}

        async with aiohttp.ClientSession() as session:
            apidata = csv.reader(await api.mtr_bus_stop_list(session))

        stops = [stop for stop in apidata
                 if stop[0] == str(route.name) and self._direction[stop[1]] == route.direction]
        for stop in stops:
            # [0]route, [1]direction, [2]seq, [3]stopID, [4]stopLAT, [5]stopLONG, [6]stopTCName, [7]stopENName
            output['data'][stop[3]] = {
                'seq': int(stop[2]),
                'name_tc': stop[6],
                'name_en': stop[7]
            }

        return output


class BravoBusData(OperatorData):

    _co = "ctb"
    """`company_id` for api calls"""

    def __init__(self, company_id: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._co = company_id

    async def fetch_routes(self) -> dict:
        async def fetch_route_details(session: aiohttp.ClientSession,
                                      route: dict) -> dict:
            # async helper, get stop details + stop ID
            directions = {
                'inbound': (await api.bravobus_route_stop_list(
                    self._co, route['route'], "inbound", session))['data'],
                'outbound': (await api.bravobus_route_stop_list(
                    self._co, route['route'], "outbound", session))['data']
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
        output = {'lastupdate': super().today, 'data': {}}

        async with aiohttp.ClientSession() as session:
            tasks = [fetch_route_details(session, stop) for stop in
                     (await api.bravobus_route_list(self._co, session))['data']]

            # keys()[0] = route name
            output['data'] = {list(entry.keys())[0]: entry[list(entry.keys())[0]]
                              for entry in await asyncio.gather(*tasks)}

        return output

    async def fetch_route(self, route: RouteEntry) -> dict:
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
        output = {'lastupdate': super().today, 'data': {}}
        async with aiohttp.ClientSession() as session:
            tasks = []
            for stop in (await api.bravobus_route_stop_list(
                    self._co,
                    route.name,
                    route.direction,
                    session))['data']:
                tasks.append(fetch_stop_details(session, stop))

            for entry in await asyncio.gather(*tasks):
                stop_code = list(entry.keys())[0]
                output['data'][stop_code] = entry[stop_code]

        return output


class CityBusData(BravoBusData):

    def __init__(self, **kwargs) -> None:
        kwargs['dir_name'] = kwargs['company_id'] = "ctb"
        super().__init__(**kwargs)


class NWFirstBusData(BravoBusData):

    def __init__(self, **kwargs) -> None:
        kwargs['dir_name'] = kwargs['company_id'] = "nwfb"
        super().__init__(**kwargs)
