from typing import Any, Optional
from pydantic import BaseModel

from app.src.enums import status_code


class StdResponse(BaseModel):

    success: bool
    message: str
    code: status_code.StatusCode
    data: Optional[dict[str, Any]] = None

    @staticmethod
    def success_(message: str = "Success.",
                 data: Optional[dict[str, Any]] = None,
                 code: Optional[status_code.StatusCode] = status_code.StatusCode.SUCCESS) -> "StdResponse":
        return StdResponse(success=True, message=message, data=data, code=code)

    @staticmethod
    def fail(message: str = "Failed.",
             data: Optional[dict[str, Any]] = None,
             code: Optional[status_code.StatusCode] = status_code.StatusCode.ERROR) -> "StdResponse":
        return StdResponse(success=False, message=message, data=data, code=code)
