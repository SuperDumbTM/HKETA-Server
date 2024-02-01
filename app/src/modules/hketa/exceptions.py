import logging


class HketaException(Exception):
    """Base exception of HketaException"""

    def __init__(self, *args: object) -> None:
        logging.error("Error occurs: %s", self.__class__.__name__)
        super().__init__(*args)


class EndOfService(HketaException):
    """The service of the route is ended"""


class ErrorReturns(HketaException):
    """API returned an error with messages//API call failed with messages"""


class APIError(HketaException):
    """API returned an error/API call failed/invalid API returns"""


class EmptyDataError(HketaException):
    """No ETA data is/can be provided"""


class StationClosed(HketaException):
    """The station is closed"""


class AbnormalService(HketaException):
    """Special service arrangement is in effect"""


class RouteError(HketaException):
    """Invalid route"""


class RouteNotExist(RouteError):
    """Invalid route name/number"""


class StopNotExist(RouteError):
    """Invalid stop code/ Stop not exists"""


class ServiceTypeNotExist(RouteError):
    """Invalid srervice type"""
