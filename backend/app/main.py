import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo.errors import PyMongoError

from app.database.client import close_mongo_connection, connect_to_mongo
from app.routes import api_router
from app.utils.settings import get_cors_origins, get_mongodb_uri

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if get_mongodb_uri() is None:
        logger.info("MongoDB is not configured; starting API without a database connection.")
    else:
        try:
            await connect_to_mongo()
        except PyMongoError:
            logger.warning("MongoDB is unavailable during startup; the API will remain available.")

    try:
        yield
    finally:
        await close_mongo_connection()

app = FastAPI(
    title="Solve Sphere API",
    description="Backend API for the Solve Sphere platform.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")