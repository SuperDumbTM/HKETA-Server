from typing import Annotated, Optional
from fastapi import APIRouter, Query

from app.modules.hketa.enums.company import Company
from app.modules.hketa.enums.direction import Direction
from app.modules.hketa.enums.language import Language

router = APIRouter(prefix="/eta")


@router.get("/")
def get_eta(company: Company,
            route_name: str,
            direction: Direction,
            stop: str,
            service_type: Optional[str | int] = None,
            lang: Language = Language.TC):
    pass
