from typing import Optional
from fastapi import APIRouter

from app.modules.hketa import enums

router = APIRouter(prefix="")


@router.get("/{company}/{route_name}/{direction}/eta")
def get_eta(company: enums.Company,
            route_name: str,
            direction: enums.Direction,
            stop: str,
            service_type: Optional[str | int] = None,
            lang: enums.Locale = enums.Locale.TC):
    pass
