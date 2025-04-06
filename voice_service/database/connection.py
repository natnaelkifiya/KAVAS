import time
import psycopg2
from psycopg2 import pool
from psycopg2.extensions import connection
from contextlib import contextmanager
from psycopg2.errors import DuplicateDatabase, DuplicateTable
from config import MySettings
from pgvector.psycopg2 import register_vector
import logging


# Create a connection pool
connection_pool = None


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db_pool():
    """Initialize the database connection pool."""
    global connection_pool
    
    if connection_pool is None:
        try:
            connection_pool = pool.ThreadedConnectionPool(
                minconn=MySettings.DB_POOL_MIN_SIZE,
                maxconn=MySettings.DB_POOL_MAX_SIZE,
                host=MySettings.DB_HOST,
                port=MySettings.DB_PORT,
                dbname=MySettings.DB_NAME,
                user=MySettings.DB_USER,
                password=MySettings.DB_PASSWORD
            )
            print("Database connection pool created successfully")
        except Exception as e:
            print(f"Error creating connection pool: {e}")
            raise

def close_db_pool():
    """Close the database connection pool."""
    global connection_pool
    if connection_pool:
        connection_pool.closeall()
        connection_pool = None
        print("Database connection pool closed")


@contextmanager
def get_db_connection():
    """Get a database connection from the pool using a context manager."""
    global connection_pool
    
    if connection_pool is None:
        init_db_pool()
    
    conn = None
    try:
        conn = connection_pool.getconn() #type:ignore
        # Register the pgvector extension
        with conn.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        register_vector(conn)
        yield conn
    except Exception as e:
        print(f"Error getting connection from pool: {e}")
        raise
    finally:
        if conn:
            connection_pool.putconn(conn) #type:ignore

@contextmanager
def get_db_cursor(commit=False):
    """Get a database cursor using a context manager."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
            if commit:
                conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Database error: {e}")
            raise
        finally:
            cursor.close()


def check_database_connection(max_retries=5, retry_interval=1):
    """Check if the database is accessible, with retries."""
    retries = 0
    
    while retries < max_retries:
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
            return True
        except Exception as e:
            retries += 1
            if retries == max_retries:
                print(f"Database connection failed after {max_retries} attempts: {str(e)}")
                raise
            time.sleep(retry_interval)
    
    return False

def setup_tables():
    """Ensure required tables exist."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                logger.info("pgvector extension enabled.")
                
                cursor.execute("""
                    CREATE TABLE users(
                        id uuid NOT NULL,
                        name text,
                        voice_embedding vector,
                        PRIMARY KEY(id)
                    );
                """)

                conn.commit()
        logger.info("Tables created successfully.")
    except DuplicateTable:
        logger.info("Tables already exist.")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise

                
setup_tables()