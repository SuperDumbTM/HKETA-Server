try:
    from lib.hketa.route import Route
    from lib.hketa.pt_operator import Operator
except ImportError:
    from .route import Route
    from .pt_operator import Operator


class RouteDetails(object):
    """A facade to retrive both the public transport operatpr information and
    route information
    """

    @property
    def eta_entry(self):
        return self._route.route_entry

    def __init__(self,
                 route: Route,
                 operator: Operator) -> None:
        self._route = route
        self._operator = operator

    def route_exists(self, raise_: bool = False) -> bool:
        return self._route.route_exists(raise_)

    def lang_code(self):
        return self._route.lang_code()

    def route_name(self):
        return self._route.route_name()

    def logo(self):
        return self._operator.logo()

    def comanpy(self):
        return self._route.comanpy()

    def stop_name(self):
        return self._route.stop_name()

    def rt_stop_name(self, code: str):
        return self._route.rt_stop_name(code)

    def stop_seq(self):
        return self._route.stop_seq()

    def stop_type(self):
        return self._operator.stop_type(self._route.route_entry)

    def origin(self):
        return self._operator.origin(self._route.route_entry)

    def orig_stopcode(self):
        return self._operator.orig_stopcode(self._route.route_entry)

    def destination(self):
        return self._operator.destination(self._route.route_entry)

    def dest_stopcode(self):
        return self._operator.dest_stopcode(self._route.route_entry)
