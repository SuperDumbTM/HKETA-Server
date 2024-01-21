import datetime
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
    except hketa.exceptions.StopNotExist:
        return std_response.StdResponse.fail(
            message="Stop not exists.",
            code=status_code.StatusCode.STOP_NOT_EXIST,
            data={
                'route': route_name,
                'origin': None,
                'destination': None,
                'stop_name': None,
                'lang': lang.value,
                'logo_url': None,
                'timestamp': datetime.datetime.now().isoformat(timespec="seconds"),
                'etas': None
            }
        )

    info = {
        'route': route_name,
        'origin': provider.route.origin(),
        'destination': provider.route.destination(),
        'stop_name': provider.route.stop_name(),
        'lang': lang.value,
        'logo_url': f'/{company.value}/bw_neg/icon',
        'timestamp': datetime.datetime.now().isoformat(timespec="seconds"),
        'etas': None
    }

    try:
        return std_response.StdResponse.success_(
            data={
                **info,
                'etas': provider.etas(),
            }
        )
    except hketa.exceptions.EndOfService:
        return std_response.StdResponse.fail(
            message="The service of the route is ended.",
            code=status_code.StatusCode.ETA_EOF,
            data=info
        )
    except hketa.exceptions.AbnormalService:
        return std_response.StdResponse.fail(
            message="Special service arrangement is in effect.",
            code=status_code.StatusCode.ETA_ABM_SERVICE,
            data=info
        )
    except hketa.exceptions.ErrorReturns as e:
        return std_response.StdResponse.fail(
            message=str(e),
            code=status_code.StatusCode.ETA_RT_ERR,
            data=info
        )
    except hketa.exceptions.APIError:
        return std_response.StdResponse.fail(
            message="Failed to request ETA from the ETA API.",
            code=status_code.StatusCode.ETA_API_ERR,
            data=info
        )
    except hketa.exceptions.StationClosed:
        return std_response.StdResponse.fail(
            message="The stop of the requesting ETA has been closed.",
            code=status_code.StatusCode.ETA_STOP_CLOSED,
            data=info
        )
    except hketa.exceptions.RouteNotExist as e:
        return std_response.StdResponse.fail(
            message=str(e),
            code=status_code.StatusCode.ROUTE_NOT_EXIST,
            data=info
        )
