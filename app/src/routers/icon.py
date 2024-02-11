from pathlib import Path
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import FileResponse
from app.src.models import std_response

from app.src.modules import hketa

router = APIRouter(prefix="")


@router.get("/{company}/{color}/icon")
def company_icon(company: hketa.enums.Transport, color: Literal['bw', 'c', 'bw_neg']):
    path = Path(__file__).parent.parent.parent.joinpath(
        'static', 'logos', color, f'{company.value}.bmp')
    if not path.exists():
        return std_response.StdResponse.fail(message="File not exists.")
    return FileResponse(path)
