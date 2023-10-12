from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter

from app.src import definition
from app.src.models import std_response
from app.src.modules import hketa

router = APIRouter()


@router.get("/{company}/routes")
def get_route_list(company: hketa.enums.Company,
                   route: Optional[str] = None,
                   service_type: Optional[str | int] = None,
                   terminal_name: Optional[str] = None,
                   ) -> std_response.StdResponse:
    route_list = (definition.ETA_FACTORY
                  .create_company_data(company)
                  .route_list())

    if route:
        route_list = {route: route_list[route]}

    if service_type:
        for route_name in list(route_list.keys()):
            route_list[route_name].inbound = [inbound for inbound in route_list[route_name].inbound
                                              if inbound.service_type == service_type]
            route_list[route_name].outbound = [inbound for inbound in route_list[route_name].inbound
                                               if inbound.service_type == service_type]

            if not route_list[route_name].inbound and not route_list[route_name].outbound:
                route_list.pop(route_name)

    if terminal_name:
        for route_name in list(route_list.keys()):
            filtered = filter(
                lambda detail: (terminal_name in detail.orig.name.values()
                                or terminal_name in detail.dest.name.values()),
                route_list[route_name].inbound + route_list[route_name].outbound)

            if len(list(filtered)) <= 0:
                route_list.pop(route_name)

    return std_response.StdResponse.success(data={'routes': route_list})


@router.get("/{company}/{route}")
def get_route_details(company: hketa.enums.Company,
                      route: str = None,
                      ) -> std_response.StdResponse:
    route_list = (definition.ETA_FACTORY
                  .create_company_data(company)
                  .route_list())

    if route not in route_list.keys():
        # TODO: handle route not exists
        pass
    return std_response.StdResponse.success(data=asdict(route_list[route.upper()]))


@router.get("/{company}/{route_name}/{direction}/{service_type}/stops")
def get_stop_list(company: hketa.enums.Company,
                  route_name: str,
                  direction: hketa.enums.Direction,
                  service_type: str) -> std_response.StdResponse:

    return std_response.StdResponse.success(
        data={
            'company': company,
            'route_name': route_name,
            'direction': direction,
            'service_type': service_type,
            'stops': definition.ETA_FACTORY.create_company_data(company).stop_list(
                hketa.models.RouteEntry(
                    company, route_name, direction, "", service_type, hketa.enums.Locale.TC
                ))
        }
    )
