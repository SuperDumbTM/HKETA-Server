from typing import Optional

from fastapi import APIRouter

from app.src import definition
from app.src.enums import status_code
from app.src.models import std_response
from app.src.modules import hketa

router = APIRouter(prefix="")


@router.get("/{company}/{route_name}/{direction}/etas")
def get_eta(company: hketa.enums.Company,
            route_name: str,
            direction: hketa.enums.Direction,
            stop: str,
            service_type: Optional[str | int] = None,
            lang: hketa.enums.Locale = hketa.enums.Locale.TC):

    try:
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
                'route': route_name,
                'orig': provider.details.origin(),
                'dest': provider.details.destination(),
                'direction': direction.value,
                'stop': provider.details.stop_name(),
                'logo': "",
                'etas': provider.etas()
            }
        )
    except hketa.exceptions.EndOfService:
        return std_response.StdResponse.fail(
            message="The service of the route is ended.",
            code=status_code.StatusCode.ETA_EOF
        )
    except hketa.exceptions.AbnormalService:
        return std_response.StdResponse.fail(
            message="Special service arrangement is in effect.",
            code=status_code.StatusCode.ETA_ABM_SERVICE
        )
    except hketa.exceptions.ErrorReturns as e:
        return std_response.StdResponse.fail(
            message=str(e),
            code=status_code.StatusCode.ETA_RT_ERR
        )
    except hketa.exceptions.APIError:
        return std_response.StdResponse.fail(
            message="Failed to request ETA from the ETA API.",
            code=status_code.StatusCode.ETA_API_ERR
        )
    except hketa.exceptions.StationClosed:
        return std_response.StdResponse.fail(
            message="The stop of the requesting ETA has been closed.",
            code=status_code.StatusCode.ETA_STOP_CLOSED
        )
    except hketa.exceptions.RouteNotExist as e:
        return std_response.StdResponse.fail(
            message=str(e),
            code=status_code.StatusCode.ROUTE_NOT_EXIST
        )
