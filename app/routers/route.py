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
    route_list = (definitation.ETA_FACTORY
                  .create_company_data(company)
                  .route_list())

    for route_name in route_list.keys():
        if (route_list[route_name].inbound is not None):
            route_list[route_name].inbound = [inbound for inbound in route_list[route_name].inbound
                                              if inbound.service_type == service_type]
        if (route_list[route_name].outbound is not None):
            route_list[route_name].outbound = [inbound for inbound in route_list[route_name].inbound
                                               if inbound.service_type == service_type]

    return std_response.StdResponse.success(
        data={
            'routes': route_list
        }
    )


@router.get("/{company}/{route_name}/{direction}/stops")
def get_stop_list(company: enums.Company,
                  route_name: str,
                  direction: enums.Direction,
                  service_type: Optional[str | int] = None):
    return definitation.ETA_FACTORY.create_company_data(company).stop_list(
        models.RouteEntry(
            company, route_name, direction, "", service_type, enums.Locale.TC
        )
    )
