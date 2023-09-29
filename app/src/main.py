import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.src.routers import eta, route

app = FastAPI(debug=True)

app.mount("/static", StaticFiles(directory=os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "static")), name="static")

app.include_router(eta.router)
app.include_router(route.router)
