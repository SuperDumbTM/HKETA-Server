from typing import Any, Optional
from pydantic import BaseModel

from app.enums import status_code


class StdResponse(BaseModel):

    status: bool
    message: str
    code: status_code.StatusCode
    data: Optional[dict[str, Any]] = None

    @staticmethod
    def success(message: str = "Success.",
                data: Optional[dict[str, Any]] = None,
                code: Optional[status_code.StatusCode] = status_code.StatusCode.SUCCESS) -> "StdResponse":
        return StdResponse(status=True, message=message, data=data, code=code)

    @staticmethod
    def fail(message: str = "Failed.",
             data: Optional[dict[str, Any]] = None,
             code: Optional[str] = status_code.StatusCode.ERROR) -> "StdResponse":
        return StdResponse(status=False, message=message, data=data, code=code)
