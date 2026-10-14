import asyncio
import os

from pydantic import ValidationError
from pymongo.errors import PyMongoError

from app.database.client import MongoDBNotConfigured, close_mongo_connection, connect_to_mongo
from app.models.auth import AdminRegistration, UserRole
from app.services.auth import DuplicateEmailError, create_user


async def provision_admin() -> int:
    email = os.getenv("ADMIN_EMAIL", "").strip()
    password = os.getenv("ADMIN_PASSWORD", "")
    name = os.getenv("ADMIN_NAME", "Platform Administrator").strip()
    if not email or not password:
        print("Set ADMIN_EMAIL and ADMIN_PASSWORD in backend/.env before provisioning.")
        return 1

    try:
        payload = AdminRegistration(name=name, email=email, password=password)
        await connect_to_mongo()
        await create_user(payload, UserRole.ADMIN)
    except DuplicateEmailError:
        print("An account already exists for ADMIN_EMAIL.")
        return 1
    except (MongoDBNotConfigured, ValidationError, PyMongoError, ValueError):
        print("Admin provisioning failed; check the account fields and MongoDB connection.")
        return 1
    finally:
        await close_mongo_connection()

    print("Admin account created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(provision_admin()))