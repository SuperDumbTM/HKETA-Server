from enum import Enum


class StatusCode(str, Enum):
    SUCCESS = "success"
    """The request has been processed successfully."""

    ERROR = "server-error"
    """The request cannot be processed due to server error (generic error)."""

    ETA_EOF = "eta-end-of-service"
    """The service of the requested ETA has ended."""

    ETA_RT_ERR = "eta-error-response"
    """An error with messages were responsed by the ETA API."""

    ETA_API_ERR = "eta-api-error"
    """Failed to request ETA from the ETA API."""

    ETA_EMPTY = "eta-no-entry"
    """Requesting ETAs successfully but no ETAs for the requested route."""

    ETA_STOP_CLOSED = "eta-stop-closure"
    """The stop of the requesting ETA has been closed."""

    ETA_ABM_SERVICE = "eta-abnormal-service"
    """Special service arrangement is in effect."""

    ROUTE_NOT_EXIST = "route-not-exist"
    """Invalid route."""

    STOP_NOT_EXIST = "stop-not-exist"
    """Invalid stop code"""
