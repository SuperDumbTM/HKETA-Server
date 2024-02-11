import asyncio
import os
from multiprocessing.pool import Pool, ThreadPool
from pathlib import Path
from typing import Literal

from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles
import pytz
from app.src import definition

from app.src.modules import hketa
from app.src.routers import eta, icon, route


app = FastAPI(title="HKETA-API-Server")

app.mount("/static", StaticFiles(directory=os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "static")), name="static")


# initialisation
scheduler = None


@app.on_event("startup")
async def init_scheduler():
    global scheduler

    scheduler = AsyncIOScheduler(
        jobstores={
            'default': MemoryJobStore(),
        },
        executors={
            "default": ThreadPoolExecutor(12),
            "processpool": ProcessPoolExecutor(4),
        },
        job_defaults={"coalesce": False, "max_instances": 3},
        timezone=pytz.timezone('Asia/Hong_kong'),
    )

    @scheduler.scheduled_job(trigger='cron', minute='*/1', max_instances=1)
    def fetch_raw_dataset_mtrb_job():
        asyncio.run(hketa.predictor.MtrBusPredictor(definition.DATASET_PATH,
                                                    definition.ETA_FACTORY.create_transport(hketa.enums.Company.MTRBUS)).fetch_dataset())

    @scheduler.scheduled_job(trigger='cron', minute='*/1', second='10', max_instances=1)
    def fetch_raw_dataset_kmb_job():
        asyncio.run(hketa.predictor.KmbPredictor(definition.DATASET_PATH,
                                                 definition.ETA_FACTORY.create_transport(hketa.enums.Company.KMB)).fetch_dataset())

    @scheduler.scheduled_job(trigger='cron', args=['day'], hour='3', minute='0', max_instances=1)
    @scheduler.scheduled_job(trigger='cron', args=['night'], hour='15', minute='0', max_instances=1)
    def perpare_ml_dataset_mtrb(type_: Literal['day', 'night']):
        hketa.predictor.MtrBusPredictor(
            definition.DATASET_PATH, definition.ETA_FACTORY.create_transport(hketa.enums.Company.MTRBUS)) \
            .raws_to_ml_dataset(type_)

    @scheduler.scheduled_job(trigger='cron', args=['day'], hour='3', minute='10', max_instances=1)
    @scheduler.scheduled_job(trigger='cron', args=['night'], hour='15', minute='10', max_instances=1)
    def perpare_ml_dataset_kmb(type_: Literal['day', 'night']):
        hketa.predictor.KmbPredictor(
            definition.DATASET_PATH, definition.ETA_FACTORY.create_transport(hketa.enums.Company.KMB)) \
            .raws_to_ml_dataset(type_)

    scheduler.start()


@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown(wait=False)


app.include_router(eta.router)
app.include_router(route.router)
app.include_router(icon.router)
