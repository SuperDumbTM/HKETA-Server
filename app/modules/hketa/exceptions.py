import logging
from typing import Awaitable

import aiohttp

try:
    from app.modules.hketa import enums
except (ImportError, ModuleNotFoundError):
    import enums


def aioex_to_etex(func: Awaitable):
    """a decorator that will catch `aiohttp.ClientError` and re-raise it to
    `hketa.exceptions`

    - `aiohttp.ClientResponseError` will be raised as `hketa.ErrorReturns`
    - `aiohttp.ClientError` will be reaised as `hketa.APIError`
    """
    async def warp(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except aiohttp.ClientResponseError as e:
            logging.error("aiohttp.ClientResponseError is raised, raise "
                          "as ErrorReturns")
            logging.debug(e, exc_info=True)
            raise ErrorReturns(f"{e.status} {e.message}") from e
        except aiohttp.ClientError as e:
            logging.error("aiohttp.ClientError is raised, raise"
                          "as APIError")
            logging.debug(e, exc_info=True)
            raise APIError from e
    return warp


class HketaException(Exception):
    """Base exception of HketaException"""

    message: dict[enums.Locale, str]
    """Exception description"""

    def __init__(self, *args: object) -> None:
        logging.error("Error occurs: %s", self.__class__.__name__)
        super().__init__(*args)

    def detail(self, lang: enums.Locale = enums.Locale.TC) -> str | None:
        return self.message.get(lang)


class EndOfService(HketaException):
    """The service of the route is ended"""

    message = {
        enums.Locale.TC: "非服務時間",
        enums.Locale.EN: "End-of-Service"
    }


class ErrorReturns(HketaException):
    """API returned an error with messages//API call failed with messages"""

    def detail(self, lang: enums.Locale = enums.Locale.TC):
        return str(self)


class APIError(HketaException):
    """API returned an error/API call failed/invalid API returns"""

    message = {
        enums.Locale.TC: "API 錯誤",
        enums.Locale.EN: "API Error"
    }


class EmptyDataError(HketaException):
    """No ETA data is/can be provided"""

    message = {
        enums.Locale.TC: "沒有數據",
        enums.Locale.EN: "No Data"
    }


class StationClosed(HketaException):
    """The station is closed"""

    message = {
        enums.Locale.TC: "車站關閉",
        enums.Locale.EN: "Stop Closed"
    }


class AbnormalService(HketaException):
    """Special service arrangement is in effect"""

    message = {
        enums.Locale.TC: "特別車務安排",
        enums.Locale.EN: "Speical Arrangement"
    }


class RouteNotExist(HketaException):
    """Invalid route name/number"""

    message = {
        enums.Locale.TC: "路線不存在",
        enums.Locale.EN: "Route Not Exists"
    }
