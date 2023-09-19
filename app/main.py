from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import eta

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(eta.router)
