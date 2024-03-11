import os

try:
    from . import enums, eta_processor, models, transport
    from .route import Route
except (ImportError, ModuleNotFoundError):
    import enums
    import eta_processor
    import models
    import transport
    from route import Route


class EtaFactory:

    data_path: os.PathLike

    store: bool
    """Indicator of storing routes data to local or not"""

    threshold: int
    """Expiry threshold of the local routes data file"""

    def __init__(self,
                 data_path: os.PathLike = None,
                 store: bool = False,
                 threshold: int = 30) -> None:
        self.data_path = data_path
        self.store = store
        self.threshold = threshold

    def create_transport(self, company: enums.Transport) -> transport.Transport:
        match company:
            case enums.Transport.KMB:
                return transport.KowloonMotorBus(self.data_path,
                                                 self.store,
                                                 self.threshold)
            case enums.Transport.MTRBUS:
                return transport.MTRBus(self.data_path,
                                        self.store,
                                        self.threshold)
            case enums.Transport.MTRLRT:
                return transport.MTRLightRail(self.data_path,
                                              self.store,
                                              self.threshold)
            case enums.Transport.MTRTRAIN:
                return transport.MTRTrain(self.data_path,
                                          self.store,
                                          self.threshold)
            case enums.Transport.CTB:
                return transport.CityBus(self.data_path,
                                         self.store,
                                         self.threshold)
            case enums.Transport.NLB:
                return transport.NewLantaoBus(self.data_path,
                                              self.store,
                                              self.threshold)
            case _:
                raise ValueError(f"Unrecognized company: {company}")

    def create_eta_processor(self, entry: models.RouteEntry) -> eta_processor.EtaProcessor:
        route = Route(entry, self.create_transport(entry.company))
        match entry.company:
            case enums.Transport.KMB:
                return eta_processor.KmbEta(route)
            case enums.Transport.MTRBUS:
                return eta_processor.MtrBusEta(route)
            case enums.Transport.MTRLRT:
                return eta_processor.MtrLrtEta(route)
            case enums.Transport.MTRTRAIN:
                return eta_processor.MtrTrainEta(route)
            case enums.Transport.CTB | enums.Transport.NWFB:
                return eta_processor.BravoBusEta(route)
            case enums.Transport.NLB:
                return eta_processor.NlbEta(route)
            case _:
                raise ValueError(f"Unrecognized company: {entry.company}")
