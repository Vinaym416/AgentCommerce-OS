"""
AGENTCOMMERCE OS
MongoDB Connection Layer

Responsible only for:
- MongoDB connection
- Database access
- Connection health check

Repositories will use this layer.
"""

import os

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# CONFIGURATION
# ============================================================

MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb://localhost:27017"
)

MONGODB_DATABASE = os.getenv(
    "MONGODB_DATABASE",
    "agentcommerce"
)


# ============================================================
# MONGODB CLIENT
# ============================================================

client = MongoClient(
    MONGODB_URI,

    # Detect connection problems quickly
    serverSelectionTimeoutMS=5000,

    # Keep connections alive
    connect=True,
)


# ============================================================
# DATABASE
# ============================================================

db = client[MONGODB_DATABASE]


# ============================================================
# HEALTH CHECK
# ============================================================

def check_connection() -> bool:

    try:

        client.admin.command("ping")

        return True

    except ConnectionFailure:

        return False


# ============================================================
# GET DATABASE
# ============================================================

def get_database():

    return db


# ============================================================
# CLI TEST
# ============================================================

def main():

    print("=" * 60)
    print("AGENTCOMMERCE OS — MONGODB")
    print("=" * 60)

    try:

        client.admin.command("ping")

        print("MongoDB connection successful.")
        print(f"Database: {MONGODB_DATABASE}")

    except Exception as exc:

        print(
            "MongoDB connection failed."
        )

        print(
            f"{type(exc).__name__}: {exc}"
        )


if __name__ == "__main__":

    main()