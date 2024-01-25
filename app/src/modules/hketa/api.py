"""
This module includes methods to retrive transport related data (e.g. ETA)\
      from data.gov.hk
"""
import logging
from typing import Literal

import requests

# ----------------------------------------
#               ETA APIs
# ----------------------------------------


def kmb_eta(route: str, services_type: str | int) -> dict:
    """
    Fetche KMB/LWB buses ETA (by route) from `ETA Data` API

    KMB API(s): https://data.gov.hk/en-data/dataset/hk-td-tis_21-etakmb

    Args:
        route (str): name (route number) of the bus route
        services_type (int): services type of the bus route (`1` = normal)
        session (aiohttp.ClientSession, optional): client session for HTTP connections

    Returns:
        dict: see https://data.etabus.gov.hk/datagovhk/kmb_eta_data_dictionary.pdf

    Raises:
        aiohttp.ClientError: An error occurred when making the HTTP request
    """
    url = f"https://data.etabus.gov.hk/v1/transport/kmb/route-eta/{route}/{services_type}"
    logging.debug("GET request to '%s'", url)
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.json()


def mtr_bus_eta(route: str, lang: Literal["zh", "en"]) -> dict:
    """Fetche MTR buses ETA (by route) from `Real-time MTR Bus and Feeder Bus Schedule` API

    MTR bus API(s): https://data.gov.hk/en-data/dataset/mtr-mtr_bus-mtr-bus-eta-data

    Args:
        route (str): name (route number) of the bus route
        lang (Literal["zh", "en"]): desire language of returns text
        session (aiohttp.ClientSession, optional): client session for HTTP connections

    Returns:
        dict: see https://opendata.mtr.com.hk/doc/MTR_BUS_DataDictionary_v1.7.pdf

    Raises:
        aiohttp.ClientError: An error occurred when making the HTTP request
    """
    url = "https://rt.data.gov.hk/v1/transport/mtr/bus/getSchedule"
    logging.debug("POST request to '%s'", url)
    response = requests.post(url,
                             json={"language": lang, "routeName": route},
                             timeout=60)
    response.raise_for_status()
    return response.json()


def mtr_lrt_eta(stop: int) -> dict:
    """Fetche MTR LRTs ETA (by stop) from `Real-time Light Rail train information` API

    MTR light rail API(s): https://data.gov.hk/en-data/dataset/mtr-lrnt_data-light-rail-nexttrain-data

    Args:
        stop (int): stop ID of a light rail station
        session (aiohttp.ClientSession, optional): client session for HTTP connections

    Returns:
        dict: see https://opendata.mtr.com.hk/doc/LR_Next_Train_DataDictionary_v1.0.pdf

    Raises:
        aiohttp.ClientError: An error occurred when making the HTTP request
    """
    url = "https://rt.data.gov.hk/v1/transport/mtr/lrt/getSchedule"
    logging.debug("GET request to '%s'", url)
    response = requests.get(url,
                            params={"station_id": stop},
                            timeout=60)
    response.raise_for_status()
    return response.json()


def mtr_train_eta(route: str, stop: str, lang: Literal["tc", "en"]) -> dict:
    """Fetch MTR trains ETA (by route + stop) from `Real-time MTR train information` API

    MTR trains API(s): https://data.gov.hk/en-data/dataset/mtr-data2-nexttrain-data

    Args:
        route (str): line code
        stop (str): MTR station code
        lang (Literal["tc", "en"]): returns text language
        session (aiohttp.ClientSession, optional): client session for HTTP connections

    Returns:
        dict: see https://opendata.mtr.com.hk/doc/Next_Train_DataDictionary_v1.2.pdf

    Raises:
        aiohttp.ClientError: An error occurred when making the HTTP request
    """
    url = "https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php"
    logging.debug("GET request to '%s'", url)
    response = requests.get(url,
                            params={"line": route, "sta": stop, "lang": lang},
                            timeout=60)
    response.raise_for_status()
    return response.json()


def bravobus_eta(company: Literal["ctb", "nwfb"],
                 stop_id: str,
                 route: str) -> dict:
    """
    Fetch CityBus/NWFB buses ETA (by route) from `Estimated Time of Arrival (ETA) data` API

    CTB API(s): https://data.gov.hk/en-data/dataset/ctb-eta-transport-realtime-eta

    NWFB API(s): https://data.gov.hk/tc-data/dataset/nwfb-eta-transport-realtime-eta

    Args:
        company (Literal["ctb", "nwfb"]): bus company id
        stop_id (str): 6 digits stop id of the stop
        route (str): name (route number) of the bus route
        session (aiohttp.ClientSession, optional): client session for HTTP connections

    Returns:
        dict: see https://www.bravobus.com.hk/datagovhk/bus_eta_data_dictionary.pdf

    Raises:
        aiohttp.ClientError: An error occurred when making the HTTP request
    """
    url = f"https://rt.data.gov.hk/v1.1/transport/citybus-nwfb/eta/{company}/{stop_id}/{route}"
    logging.debug("GET request to '%s'", url)
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.json()


# ----------------------------------------
#              Route Details
# ----------------------------------------

def mtr_bus_stop_list() -> list:
    """Fetch MTR buses stop list from `MTR Bus & Feeder Bus Stops` API

    MTR API(s): https://data.gov.hk/tc-data/dataset/mtr-data-routes-fares-barrier-free-facilities

    Args:
        session (aiohttp.ClientSession, optional): client session for HTTP connections

    Returns:
        list: CSV encoded with list
            see https://opendata.mtr.com.hk/doc/DataDictionary.zip

    Raises:
        aiohttp.ClientError: An error occurred when making the HTTP request
    """
    url = "https://opendata.mtr.com.hk/data/mtr_bus_stops.csv"
    logging.debug("GET request to '%s'", url)
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    response = response.content.decode().splitlines()


def mtr_bus_route_list() -> list:
    """Fetch MTR buses available route list from `MTR Bus & Feeder Bus Routes` API

    MTR API(s): https://data.gov.hk/tc-data/dataset/mtr-data-routes-fares-barrier-free-facilities

    Args:
        session (aiohttp.ClientSession, optional): client session for HTTP connections

    Returns:
        list: CSV encoded with list
            see https://opendata.mtr.com.hk/doc/DataDictionary.zip

    Raises:
        aiohttp.ClientError: An error occurred when making the HTTP request
    """
    url = "https://opendata.mtr.com.hk/data/mtr_bus_routes.csv"
    logging.debug("GET request to '%s'", url)
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.content.decode().splitlines()


def mtr_lrt_route_stop_list() -> list:
    """Fetch MTR light rail details (availavle routes & respective stops) from `Light Rail Routes & Stops` API

    MTR API(s): https://data.gov.hk/tc-data/dataset/mtr-data-routes-fares-barrier-free-facilities

    Args:
        session (aiohttp.ClientSession, optional): client session for HTTP connections

    Returns:
        list: CSV encoded with list
            see https://opendata.mtr.com.hk/doc/DataDictionary.zip

    Raises:
        aiohttp.ClientError: An error occurred when making the HTTP request
    """
    url = "https://opendata.mtr.com.hk/data/light_rail_routes_and_stops.csv"
    logging.debug("GET request to '%s'", url)
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.content.decode().splitlines()


def mtr_train_route_stop_list() -> list:
    """Fetch MTR trains (availavle routes & respective stops) from `MTR Lines (except Light Rail) & Stations` API

    MTR API(s): https://data.gov.hk/tc-data/dataset/mtr-data-routes-fares-barrier-free-facilities

    Args:
        session (aiohttp.ClientSession, optional): client session for HTTP connections

    Returns:
        list: CSV encoded with list
            see https://opendata.mtr.com.hk/doc/DataDictionary.zip

    Raises:
        aiohttp.ClientError: An error occurred when making the HTTP request
    """
    url = "https://opendata.mtr.com.hk/data/mtr_lines_and_stations.csv"
    logging.debug("GET request to '%s'", url)
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.content.decode().splitlines()


def kmb_route_list() -> dict:
    """Fetch KMB available route list from `Route List Data` API

    KMB API(s): https://data.gov.hk/en-data/dataset/hk-td-tis_21-etakmb

    Args:
        session (aiohttp.ClientSession, optional): client session for HTTP connections

    Returns:
        dict: see https://data.etabus.gov.hk/datagovhk/kmb_eta_data_dictionary.pdf

    Raises:
        aiohttp.ClientError: An error occurred when making the HTTP request
    """
    url = "https://data.etabus.gov.hk/v1/transport/kmb/route/"
    logging.debug("GET request to '%s'", url)
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.json()


def kmb_route_stop_list(route: str,
                        direction: Literal["inbound", "outbound"],
                        services_type: int) -> dict:
    """Fetch KMB stop list (by route) from `Route-Stop Data` API

    KMB API(s): https://data.gov.hk/en-data/dataset/hk-td-tis_21-etakmb

    Args:
        route (str): name (route number) of the bus route
        dir (Literal["inbound", "outbound"]): direction
        services_type (int): services type of the route (`1` = normal)
        session (aiohttp.ClientSession, optional): client session for HTTP connections

    Returns:
        dict: see https://data.etabus.gov.hk/datagovhk/kmb_eta_data_dictionary.pdf

    Raises:
        aiohttp.ClientError: An error occurred when making the HTTP request
    """
    url = f"https://data.etabus.gov.hk/v1/transport/kmb/route-stop/{route}/{direction}/{services_type}"
    logging.debug("GET request to '%s'", url)
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.json()


def kmb_stop_details(stop_id: str) -> dict:
    """Fetch KMB stop information from `Stop Data` API

    KMB API(s): https://data.gov.hk/en-data/dataset/hk-td-tis_21-etakmb

    Args:
        stop_id (str): bus stop id (query from `Route-Stop API`)
        session (aiohttp.ClientSession, optional): client session for HTTP connections

    Returns:
        dict: see https://data.etabus.gov.hk/datagovhk/kmb_eta_data_dictionary.pdf

    Raises:
        aiohttp.ClientError: An error occurred when making the HTTP request
    """
    url = f"https://data.etabus.gov.hk/v1/transport/kmb/stop/{stop_id}"
    logging.debug("GET request to '%s'", url)
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.json()


def bravobus_route_list(company: Literal["ctb", "nwfb"]) -> dict:
    """Fetch CityBus/NWFB available route list by route from `Route data` API

    CTB API(s): https://data.gov.hk/en-data/dataset/ctb-eta-transport-realtime-eta

    NWFB API(s): https://data.gov.hk/tc-data/dataset/nwfb-eta-transport-realtime-eta

    Args:
        session (aiohttp.ClientSession, optional): client session for HTTP connections

    Returns:
        dict: see https://www.bravobus.com.hk/datagovhk/bus_eta_data_dictionary.pdf

    Raises:
        aiohttp.ClientError: An error occurred when making the HTTP request
    """
    url = f"https://rt.data.gov.hk/v2/transport/citybus/route/{company}"
    logging.debug("GET request to '%s'", url)
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.json()


def bravobus_route_stop_list(
        company: Literal["ctb"],
        route: str,
        direction: Literal["inbound", "outbound"]) -> dict:
    """Fetch CityBys/NWFB stop list (by route) from `Bus Stop List of specific Route data` API

    CTB API(s): https://data.gov.hk/en-data/dataset/ctb-eta-transport-realtime-eta


    Args:
        company (Literal["ctb"]): bus company
        route (str): name (route number) of the bus route
        dir (Literal["inbound", "outbound"]): route direction
        session (aiohttp.ClientSession, optional): client session for HTTP connections

    Returns:
        dict: see https://www.bravobus.com.hk/datagovhk/bus_eta_data_dictionary.pdf

    Raises:
        aiohttp.ClientError: An error occurred when making the HTTP request
    """
    url = f"https://rt.data.gov.hk/v2/transport/citybus/route-stop/{company}/{route}/{direction}"
    logging.debug("GET request to '%s'", url)
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.json()


def bravobus_stop_details(stop_id: str) -> dict:
    """Fetch CityBus/NWFB stop information from `Stop Data` API

    CTB API(s): https://data.gov.hk/en-data/dataset/ctb-eta-transport-realtime-eta

    Args:
        stop_id (str): bus stop id
        session (aiohttp.ClientSession, optional): client session for HTTP connections

    Returns:
        dict: see https://www.bravobus.com.hk/datagovhk/bus_eta_data_dictionary.pdf

    Raises:
        aiohttp.ClientError: An error occurred when making the HTTP request
    """
    url = f"https://rt.data.gov.hk/v2/transport/citybus/stop/{stop_id}"
    logging.debug("GET request to '%s'", url)
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.json()


async def nlb_route_list() -> dict:
    """Fetch NLB available route list from `Route List Data` API

    NLB API(s): https://data.gov.hk/en-data/dataset/nlb-bus-nlb-bus-service-v2

    Args:
        session (aiohttp.ClientSession, optional): client session for HTTP connections

    Returns:
        dict: see https://data.etabus.gov.hk/datagovhk/kmb_eta_data_dictionary.pdf

    Raises:
        aiohttp.ClientError: An error occurred when making the HTTP request
    """
    url = "https://rt.data.gov.hk/v2/transport/nlb/route.php?action=list"
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.json()


async def nlb_route_stop_list(route_id: str) -> dict:
    """Fetch NLB stop list (by route) from `Route-Stop Data` API

    NLB API(s): https://data.gov.hk/en-data/dataset/nlb-bus-nlb-bus-service-v2

    Args:
        session (aiohttp.ClientSession, optional): client session for HTTP connections

    Returns:
        dict: see https://data.etabus.gov.hk/datagovhk/kmb_eta_data_dictionary.pdf

    Raises:
        aiohttp.ClientError: An error occurred when making the HTTP request
    """
    url = f"https://rt.data.gov.hk/v2/transport/nlb/stop.php?action=list&routeId={route_id}"
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.json()
