# pylint: disable=redefined-outer-name,

try:
    from app.src.modules.hketa import route, transport
except (ImportError, ModuleNotFoundError):
    import route
    import transport


class RouteDetails(object):
    """A facade to retrive both the public transport and route information.
    """

    @property
    def eta_entry(self):
        return self._route.route_entry

    def __init__(self,
                 route: route.Route,
                 transport: transport.Transport) -> None:
        self._route = route
        self._transport = transport

    def route_name(self):
        return self._route.route_name()

    def logo(self):
        return self._transport.logo()

    def comanpy(self):
        return self._route.comanpy()

    def stop_name(self):
        return self._route.stop_name()

    def rt_stop_name(self, code: str):
        return self._route.rt_stop_name(code)

    def stop_seq(self):
        return self._route.stop_seq()

    def stop_type(self):
        return self._transport.stop_type(self._route.route_entry)

    def origin(self):
        return self._transport.origin(self._route.route_entry)

    def orig_stopcode(self):
        return self._transport.orig_stopcode(self._route.route_entry)

    def destination(self):
        return self._transport.destination(self._route.route_entry)

    def dest_stopcode(self):
        return self._transport.dest_stopcode(self._route.route_entry)
