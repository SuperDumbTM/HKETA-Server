import os

try:
    import eta_processor as eta
    import lib.hketa.route_details as rtdet
    import lib.hketa.route as _rtdet
    import lib.hketa.pt_operator as operator
    import lib.hketa.pt_operator_data as opdata
    import lib.hketa.enums as etaenums
    from route_entry import RouteEntry
except ImportError:
    from . import eta_processor as eta
    from . import route_details as rtdet
    from . import route as _rtdet
    from . import pt_operator as operator
    from . import pt_operator_data as opdata
    from . import enums as etaenums
    from .route_entry import RouteEntry


class EtaFactory(object):

    data_path: os.PathLike

    store: bool
    """indicator of storing routes data to local or not"""

    threshold: int
    """expiry threshold of the local routes data file"""

    def __init__(self, data_path: os.PathLike = None,
                 store: bool = False, threshold: int = 30) -> None:
        self.data_path = data_path
        self.store = store
        self.threshold = threshold

    def create_rdata(self, company: etaenums.Company) -> opdata.OperatorData:
        match company:
            case etaenums.Company.KMB:
                return opdata.KMBData(root=self.data_path,
                                           store_local=self.store,
                                           threshold=self.threshold)
            case etaenums.Company.MTRBUS:
                return opdata.MTRBusData(root=self.data_path,
                                              store_local=self.store,
                                              threshold=self.threshold)
            case etaenums.Company.MTRLRT:
                return opdata.MTRLrtData(root=self.data_path,
                                              store_local=self.store,
                                              threshold=self.threshold)
            case etaenums.Company.MTRTRAIN:
                return opdata.MTRTrainData(root=self.data_path,
                                                store_local=self.store,
                                                threshold=self.threshold)
            case etaenums.Company.CTB:
                return opdata.CityBusData(root=self.data_path,
                                               store_local=self.store,
                                               threshold=self.threshold)
            case etaenums.Company.NWFB:
                return opdata.NWFirstBusData(root=self.data_path,
                                                  store_local=self.store,
                                                  threshold=self.threshold)
            case _:
                raise ValueError(f"unrecognized company: {company}")

    def create_rdets(self, route: RouteEntry) -> rtdet.RouteDetails:
        match route.co:
            case etaenums.Company.KMB:
                return rtdet.RouteDetails(
                    _rtdet.KMBRoute(
                        route, self.create_rdata(route.co)),
                    operator.KowloonMotorBus(self.create_rdata(route.co))
                )
            case etaenums.Company.MTRBUS:
                return rtdet.RouteDetails(
                    _rtdet.MTRBusRoute(
                        route, self.create_rdata(route.co)),
                    operator.MTRBus(self.create_rdata(route.co))
                )
            case etaenums.Company.MTRLRT:
                return rtdet.RouteDetails(
                    _rtdet.MTRLrtRoute(
                        route, self.create_rdata(route.co)),
                    operator.MTRLightRail(self.create_rdata(route.co))
                )
            case etaenums.Company.MTRTRAIN:
                return rtdet.RouteDetails(
                    _rtdet.MTRTrainRoute(
                        route, self.create_rdata(route.co)),
                    operator.MTRTrain(self.create_rdata(route.co))
                )
            case etaenums.Company.CTB:
                return rtdet.RouteDetails(
                    _rtdet.BravoBusRoute(
                        route, self.create_rdata(route.co)),
                    operator.CityBus(self.create_rdata(route.co))
                )
            case etaenums.Company.NWFB:
                return rtdet.RouteDetails(
                    _rtdet.BravoBusRoute(
                        route, self.create_rdata(route.co)),
                    operator.NWFirstBus(
                        self.create_rdata(route.co))
                )
            case _:
                raise ValueError(f"unrecognized company: {route.co}")

    def create_eta(self, route: RouteEntry) -> eta.EtaProcessor:
        match route.co:
            case etaenums.Company.KMB:
                return eta.KmbEta(self.create_rdets(route))
            case etaenums.Company.MTRBUS:
                return eta.MtrBusEta(self.create_rdets(route))
            case etaenums.Company.MTRLRT:
                return eta.MtrLrtEta(self.create_rdets(route))
            case etaenums.Company.MTRTRAIN:
                return eta.MtrTrainEta(self.create_rdets(route))
            case etaenums.Company.CTB | etaenums.Company.NWFB:
                return eta.BravoBusEta(self.create_rdets(route))
            case _:
                raise ValueError(f"unrecognized company: {route.co}")
