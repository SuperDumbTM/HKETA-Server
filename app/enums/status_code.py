from enum import Enum


class StatusCode(str, Enum):
    SUCCESS = "success"
    """The request has successfully processed"""

    ERROR = "server-error"
    """The request cannot be processed due to server error (generic error)"""
