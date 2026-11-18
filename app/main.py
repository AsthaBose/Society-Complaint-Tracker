import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config, models  # noqa: F401  (models must be imported so create_all sees the tables)
from .database import Base, engine
from .routers import auth, complaints

BASE_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    if config.SECRET_KEY == config.DEFAULT_SECRET:
        logging.getLogger("uvicorn.error").warning(
            "SECRET_KEY is the development default. Set a real one before deploying."
        )
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Society Complaint Tracker", version="0.1.0", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(complaints.router)


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok"}


app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(BASE_DIR / "static" / "index.html")
