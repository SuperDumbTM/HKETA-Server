import os
from pathlib import Path
from typing import Final

from app.src.modules.hketa import factories

CACHE_PATH: Final[Path] = Path(
    os.environ.get('APP_CACHE_PATH', str(Path(__file__).parents[1].joinpath('caches'))))

ROUTE_DATA_PATH: Final[Path] = CACHE_PATH.joinpath('transport_data')

DATASET_PATH: Final[Path] = CACHE_PATH.joinpath('datasets')

ETA_FACTORY: Final[factories.EtaFactory] = factories.EtaFactory(
    ROUTE_DATA_PATH, True, 30)
