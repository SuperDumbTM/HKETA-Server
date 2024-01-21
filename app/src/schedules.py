from pathlib import Path
from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from fastapi import APIRouter
from pytz import UTC
from app.src import definition

from app.src.modules.hketa import predictor

router = APIRouter()
scheduler = None


@router.on_event("startup")
def init_scheduler():
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

    # ---------- init tasks ----------
    scheduler.add_job(predictor.KmbPredictor(definition.DATASET_PATH).fetch_dataset,
                      trigger='cron',
                      minute='*/1',
                      id='kmb_ml_fetch_raw')
    scheduler.add_job(predictor.KmbPredictor(definition.DATASET_PATH).raws_to_ml_dataset,
                      args=['day'],
                      trigger='cron',
                      hour='3',
                      minute='0',
                      id='kmb_ml_raw2dataset_day')
    scheduler.add_job(predictor.KmbPredictor(definition.DATASET_PATH).raws_to_ml_dataset,
                      args=['night'],
                      trigger='cron',
                      hour='15',
                      minute='0',
                      id='kmb_ml_raw2dataset_night')


@router.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown(wait=False)
