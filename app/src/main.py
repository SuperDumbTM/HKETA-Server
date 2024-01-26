import asyncio
import os
from multiprocessing.pool import Pool, ThreadPool
from pathlib import Path
from typing import Literal

from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles
from pytz import UTC
from app.src import definition

from app.src.modules import hketa
from app.src.routers import eta, icon, route


app = FastAPI(title="HKETA-API-Server", debug=True)

app.mount("/static", StaticFiles(directory=os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "static")), name="static")


# initialisation
scheduler = None


@app.on_event("startup")
async def init_scheduler():
    global scheduler
    jobstores = {
        "default": MemoryJobStore(),
    }
    executors = {
        "default": ThreadPoolExecutor(15),
        "processpool": ProcessPoolExecutor(5),
    }
    job_defaults = {"coalesce": False, "max_instances": 3}

    scheduler = BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone=UTC,
    )
    scheduler.start()

    def fetch_raw_dataset_job():
        # asyncio.run(
        #     hketa.predictor.KmbPredictor(definition.DATASET_PATH,
        #                                  definition.ETA_FACTORY.create_transport(hketa.enums.Company.KMB)).fetch_dataset()
        # )
        hketa.predictor.KmbPredictor(definition.DATASET_PATH,
                                     definition.ETA_FACTORY.create_transport(hketa.enums.Company.KMB)).raws_to_ml_dataset('day')
        return
        asyncio.run(
            hketa.predictor.KmbPredictor(definition.DATASET_PATH,
                                         definition.ETA_FACTORY.create_transport(hketa.enums.Company.KMB)).fetch_dataset()
        )
        # return
        # asyncio.run(
        #     hketa.predictor.MtrBusPredictor(definition.DATASET_PATH,
        #                                     definition.ETA_FACTORY.create_transport(hketa.enums.Company.MTRBUS)).fetch_dataset()
        # )

    def perpare_ml_dataset(type_: Literal['day', 'night']):
        hketa.predictor.KmbPredictor(
            definition.DATASET_PATH, definition.ETA_FACTORY.create_transport(hketa.enums.Company.KMB)) \
            .raws_to_ml_dataset(type_)
        hketa.predictor.MtrBusPredictor(
            definition.DATASET_PATH, definition.ETA_FACTORY.create_transport(hketa.enums.Company.MTRBUS)) \
            .raws_to_ml_dataset(type_)

    import threading
    t = threading.Thread(target=fetch_raw_dataset_job)
    t.start()
    t.join()
    print('done')
    return

    # ---------- init tasks ----------
    scheduler.add_job(fetch_raw_dataset_job,
                      trigger='cron',
                      minute='*/1',
                      id='fetch_raw')
    scheduler.add_job(perpare_ml_dataset,
                      args=['day'],
                      trigger='cron',
                      hour='3',
                      minute='0',
                      id='ml_raw2dataset_dat')
    scheduler.add_job(perpare_ml_dataset,
                      args=['night'],
                      trigger='cron',
                      hour='15',
                      minute='0',
                      id='ml_raw2dataset_night')


@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown(wait=False)


app.include_router(eta.router)
app.include_router(route.router)
app.include_router(icon.router)
