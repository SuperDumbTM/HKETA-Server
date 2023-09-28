import os
from typing import Final

from app.src.modules.hketa import factories


ROUTE_DATA_PATH: Final[os.PathLike] = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "caches", "transport_data")

ETA_FACTORY: Final[factories.EtaFactory] = factories.EtaFactory(
    ROUTE_DATA_PATH, True, 30)
