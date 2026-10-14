from typing import Any

from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError

from app.database.collections import ensure_database_structure
from app.utils.settings import get_mongodb_database_name, get_mongodb_uri

_client: AsyncMongoClient | None = None
_database: Any | None = None


class MongoDBNotConfigured(RuntimeError):
    """Raised when MongoDB settings are missing."""


async def connect_to_mongo() -> None:
    global _client, _database

    uri = get_mongodb_uri()
    if uri is None:
        raise MongoDBNotConfigured("MONGODB_URI is not configured")

    if _client is None:
        _client = AsyncMongoClient(uri, serverSelectionTimeoutMS=5000)
        _database = _client[get_mongodb_database_name()]

    try:
        await _client.admin.command("ping")
        await ensure_database_structure(_database)
    except PyMongoError:
        await close_mongo_connection()
        raise


async def ping_database() -> None:
    if _client is None:
        await connect_to_mongo()
        return

    await _client.admin.command("ping")


def get_database() -> Any:
    if _database is None:
        raise MongoDBNotConfigured("MongoDB is not connected")
    return _database


async def close_mongo_connection() -> None:
    global _client, _database

    client = _client
    _client = None
    _database = None
    if client is not None:
        await client.close()