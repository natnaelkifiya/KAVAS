from fastapi import Depends
from database.connection import get_db_connection, get_db_cursor

def get_db():
    """Dependency to get a database connection."""
    with get_db_connection() as conn:
        yield conn

def get_db_cursor_dependency(commit=False):
    """Dependency to get a database cursor."""
    with get_db_cursor(commit=commit) as cursor:
        yield cursor