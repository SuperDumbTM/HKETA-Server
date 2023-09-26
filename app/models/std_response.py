from typing import Any, Optional
from pydantic import BaseModel

from app.enums import error_code


class StdResponse(BaseModel):

    status: bool
    message: str
    data: Optional[dict[str, Any]] = None
    code: Optional[error_code.ErrorCode] = None

    @staticmethod
    def success(message: str = "Success.",
                data: Optional[dict[str, Any]] = None,
                code: Optional[error_code.ErrorCode] = None) -> "StdResponse":
        return StdResponse(status=True, message=message, data=data, code=code)

    @staticmethod
    def fail(message: str = "Error.",
             data: Optional[dict[str, Any]] = None,
             code: Optional[str] = None) -> "StdResponse":
        return StdResponse(status=False, message=message, data=data, code=code)
