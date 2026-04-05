import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI News Aggregator...")
    await init_db()
    logger.info("Database initialized.")

    from app.scheduler import start_scheduler, stop_scheduler

    await start_scheduler()
    logger.info("Scheduler started.")

    yield

    await stop_scheduler()
    logger.info("Scheduler stopped.")


app = FastAPI(title="AI News Aggregator", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

from app.routers import api, web  # noqa: E402

app.include_router(web.router)
app.include_router(api.router, prefix="/api")
