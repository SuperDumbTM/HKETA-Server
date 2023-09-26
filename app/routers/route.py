from typing import Optional

from fastapi import APIRouter

from app import definitation
from app.models import std_response
from app.modules.hketa import enums, models

router = APIRouter()


@router.get("/{company}/routes")
def get_route_list(company: enums.Company,
                   direction: Optional[enums.Direction] = None,
                   service_type: Optional[str | int] = None
                   ) -> std_response.StdResponse:
    route_list = definitation.ETA_FACTORY.create_company_data(company).routes()
    return route_list


@router.get("/{company}/{route_name}/{direction}/stops")
def get_stop_list(company: enums.Company,
                  route_name: str,
                  direction: enums.Direction,
                  service_type: Optional[str | int] = None):
    return definitation.ETA_FACTORY.create_company_data(company).route(
        models.RouteEntry(
            company, route_name, direction, "", service_type, enums.Locale.TC
        )
    )
