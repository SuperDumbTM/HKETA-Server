from typing import Optional
from pydantic import BaseModel

from app.src.enums.company import Company
from app.src.enums.direction import Direction
from app.src.enums.language import Language


class EtaModel(BaseModel):
    company: Company
    route_name: str
    direction: Direction
    service_type: Optional[str | int]
    stop: str
    lang: Language
