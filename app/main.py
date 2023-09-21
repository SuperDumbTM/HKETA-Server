from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import eta, route

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(eta.router)
app.include_router(route.router)
