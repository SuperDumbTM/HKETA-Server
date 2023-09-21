import os
from typing import Final


ROUTE_DATA_PATH: Final[os.PathLike] = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "caches", "transport_data")
