# Public interface for the database connection package
from .mongo import (
    get_database,
    close_mongo_connection,
    MongoDB,
)

__all__ = [
    "get_database",
    "close_mongo_connection",
    "MongoDB",
]
