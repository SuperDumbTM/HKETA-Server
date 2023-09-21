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

    factory = factories.EtaFactory(definitation.ROUTE_DATA_PATH, True, -1)
    transport = factory.create_company_data(company)

    return transport.route(models.RouteEntry(
        company, "K76", enums.Direction.INBOUND, '1', "", lang
    ))


# @router.get("/{company}/{route_name}/{direction}/stops")
# def get_stop_list(company: enums.Company,
#                   route_name: str,
#                   direction: enums.Direction,
#                   service_type: Optional[str | int] = None,
#                   lang: enums.Locale = enums.Locale.TC):

#     factory = factories.EtaFactory(definitation.ROUTE_DATA_PATH, True)
#     transport = factory.create_company_data(company)

#     return transport.routes()
