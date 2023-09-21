import os

try:
    from app.modules.hketa import company_data, enums, models, transport, route, eta_processor
except (ImportError, ModuleNotFoundError):
    import company_data
    import enums
    import models
    import transport
    import route
    import eta_processor


class EtaFactory:

    data_path: os.PathLike

    store: bool
    """Indicator of storing routes data to local or not"""

    threshold: int
    """Expiry threshold of the local routes data file"""

    def __init__(self, data_path: os.PathLike = None,
                 store: bool = False, threshold: int = 30) -> None:
        self.data_path = data_path
        self.store = store
        self.threshold = threshold

    def create_company_data(self, company: enums.Company) -> company_data.CompanyData:
        match company:
            case enums.Company.KMB:
                return company_data.KMBData(self.data_path,
                                            self.store,
                                            self.threshold)
            case enums.Company.MTRBUS:
                return company_data.MTRBusData(self.data_path,
                                               self.store,
                                               self.threshold)
            case enums.Company.MTRLRT:
                return company_data.MTRLrtData(self.data_path,
                                               self.store,
                                               self.threshold)
            case enums.Company.MTRTRAIN:
                return company_data.MTRTrainData(self.data_path,
                                                 self.store,
                                                 self.threshold)
            case enums.Company.CTB:
                return company_data.CityBusData(self.data_path,
                                                self.store,
                                                self.threshold)
            case _:
                raise ValueError(f"Unrecognized company: {company}")

    def create_route(self, entry: models.RouteEntry) -> route.Route:
        match entry.company:
            case enums.Company.KMB:
                return route.KMBRoute(
                    entry,
                    transport.KowloonMotorBus(
                        self.create_company_data(entry.company))
                )
            case enums.Company.MTRBUS:
                return route.MTRBusRoute(
                    entry,
                    transport.MTRBus(self.create_company_data(entry.company))
                )
            case enums.Company.MTRLRT:
                return route.MTRLrtRoute(
                    entry,
                    transport.MTRTrain(self.create_company_data(entry.company))
                )
            case enums.Company.MTRTRAIN:
                return route.MTRTrainRoute(
                    entry,
                    transport.MTRTrain(self.create_company_data(entry.company))
                )
            case enums.Company.CTB:
                return route.BravoBusRoute(
                    entry,
                    transport.CityBus(self.create_company_data(entry.company))
                )
            case _:
                raise ValueError(f"unrecognized company: {entry.company}")

    def create_eta_processor(self, entry: models.RouteEntry) -> eta_processor.EtaProcessor:
        match entry.company:
            case enums.Company.KMB:
                return eta_processor.KmbEta(self.create_route(route))
            case enums.Company.MTRBUS:
                return eta_processor.MtrBusEta(self.create_route(route))
            case enums.Company.MTRLRT:
                return eta_processor.MtrLrtEta(self.create_route(route))
            case enums.Company.MTRTRAIN:
                return eta_processor.MtrTrainEta(self.create_route(route))
            case enums.Company.CTB | enums.Company.NWFB:
                return eta_processor.BravoBusEta(self.create_route(route))
            case _:
                raise ValueError(f"unrecognized company: {entry.company}")
