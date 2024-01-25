from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter

from app.src import definition, utils
from app.src.models import std_response
from app.src.modules import hketa

router = APIRouter()


@router.get("/routes/{company}")
def get_route_list(company: hketa.enums.Company,
                   route_no: Optional[str] = None,
                   service_type: Optional[str | int] = None,
                   terminal_name: Optional[str] = None,
                   ) -> std_response.StdResponse:
    route_list = definition.ETA_FACTORY \
        .create_transport(company) \
        .route_list()

    if route_no:
        route_list = {route_no: route_list[route_no]}

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

    return std_response.StdResponse.success_(data={'routes': route_list})


@router.get("/services/{company}/{route_no}")
def get_route_details(company: hketa.enums.Company,
                      route_no: str = None,
                      ) -> std_response.StdResponse:
    route_list = definition.ETA_FACTORY \
        .create_transport(company) \
        .route_list()

    if route_no not in route_list.keys():
        # TODO: handle route not exists
        pass
    return std_response.StdResponse.success_(data=asdict(route_list[route_no.upper()]))


@router.get("/stops/{company}/{route_no}")
def get_stop_list(company: hketa.enums.Company,
                  route_no: str,
                  direction: hketa.enums.Direction,
                  service_type: str) -> std_response.StdResponse:
    transport_ = definition.ETA_FACTORY.create_transport(company)
    return std_response.StdResponse.success_(
        data={
            'company': company,
            'route_name': route_no,
            'direction': direction,
            'service_type': service_type,
            'stops': transport_.stop_list(route_no, direction, service_type)
        }
    )


@router.get("/stop/{company}/{route_name}")
def get_stop(company: hketa.enums.Company,
             route_no: str,
             direction: hketa.enums.Direction,
             service_type: str,
             stop_code: str) -> std_response.StdResponse:
    stop_list = definition.ETA_FACTORY \
        .create_transport(company) \
        .stop_list(route_no, direction, service_type)

    for stop in stop_list:
        if stop.stop_code == stop_code:
            return std_response.StdResponse.success_(
                data={
                    'company': company,
                    'route_name': route_no,
                    'direction': direction,
                    'service_type': service_type,
                    'stop': asdict(stop, dict_factory=utils.custom_asdict_factory)
                }
            )
    return std_response.StdResponse.fail(message="Not found.")
