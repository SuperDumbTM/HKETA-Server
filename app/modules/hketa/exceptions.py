import aiohttp
import logging
from typing import Awaitable


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
            raise ErrorReturns(f"{e.status} {e.message}")
        except aiohttp.ClientError as e:
            logging.error("aiohttp.ClientError is raised, raise"
                          "as APIError")
            logging.debug(e, exc_info=True)
            raise APIError
    return warp


class HketaException(Exception):
    """Base exception of HketaException"""

    _tc_msg: str
    """Exception description in traditional Chinese"""

    _en_msg: str
    """Exception description in English"""

    def __init__(self, *args: object) -> None:
        logging.error(f"error occurs: {self.__class__.__name__}")
        super().__init__(*args)

    def get_msg(self, lang: enums.Language = enums.Language.TC) -> str:
        if lang == enums.Language.TC:
            return self._tc_msg
        else:
            return self._en_msg


class EndOfService(HketaException):
    """The service of the route is ended"""

    _tc_msg = "非服務時間"
    _en_msg = "End of Services"


class ErrorReturns(HketaException):
    """API returned an error with messages//API call failed with messages"""

    def get_msg(self, lang: enums.Language = enums.Language.TC):
        return str(self)


class APIError(HketaException):
    """API returned an error/API call failed/invalid API returns"""

    _tc_msg = "API 錯誤"
    _en_msg = "API Error"


class EmptyDataError(HketaException):
    """No ETA data is/can be provided"""

    _tc_msg = "沒有數據"
    _en_msg = "No Data"


class StationClosed(HketaException):
    """The station is closed"""

    _tc_msg = "車站關閉"
    _en_msg = "Stop Closed"


class AbnormalService(HketaException):
    """Special service arrangement is in effect"""

    _tc_msg = "特別車務安排"
    _en_msg = "Speical Arrangement"


class RouteNotExist(HketaException):
    """Invalid route name/number"""

    _tc_msg = "路線不存在"
    _en_msg = "Route Not Exists"
