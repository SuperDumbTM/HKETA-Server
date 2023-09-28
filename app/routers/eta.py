from typing import Optional

from fastapi import APIRouter

from app import definition
from app.models import std_response
from app.modules import hketa

router = APIRouter(prefix="")


@router.get("/{company}/{route_name}/{direction}/etas")
def get_eta(company: hketa.enums.Company,
            route_name: str,
            direction: hketa.enums.Direction,
            stop: str,
            service_type: Optional[str | int] = None,
            lang: hketa.enums.Locale = hketa.enums.Locale.TC) -> std_response.StdResponse:
    provider = definition.ETA_FACTORY.create_eta_processor(
        hketa.models.RouteEntry(
            company=company,
            name=route_name,
            direction=direction,
            stop=stop,
            service_type=service_type,
            lang=lang
        ))

    return std_response.StdResponse.success(
        data={
            'etas': provider.etas()
        }
    )
