from typing import Optional

from fastapi import APIRouter

from app import definitation
from app.modules.hketa import enums, factories, models

router = APIRouter()


@router.get("/{company}/routes")
def get_route_list(company: enums.Company,
                   direction: enums.Direction = None,
                   service_type: Optional[str | int] = None,
                   lang: enums.Locale = enums.Locale.TC):
    comp_data = definitation.ETA_FACTORY.create_company_data(company)

    route_list = comp_data.routes()

    return route_list


@router.get("/{company}/{route_name}/{direction}/stops")
def get_stop_list(company: enums.Company,
                  route_name: str,
                  direction: enums.Direction,
                  service_type: Optional[str | int] = None):

    comp_data = definitation.ETA_FACTORY.create_company_data(company)

    return comp_data.route(
        models.RouteEntry(
            company, route_name, direction, service_type, None, enums.Locale.TC
        )
    )
