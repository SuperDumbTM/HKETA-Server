from typing import Optional
from pydantic import BaseModel

from app.enums.company import Company
from app.enums.direction import Direction
from app.enums.language import Language


class EtaModel(BaseModel):
    company: Company
    route_name: str
    direction: Direction
    service_type: Optional[str | int]
    stop: str
    lang: Language
