import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database.connection import init_db_pool, close_db_pool, check_database_connection, setup_tables
from voice.router import voice_router
import uvicorn


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        logger.info("Initializing database connection pool...")
        init_db_pool()
        
        logger.info("Checking database connection...")
        setup_tables()
        check_database_connection()
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        logger.warning("Application will start without database connectivity")
        # Allow app to start even with database errors for development
        raise Exception("Database connection error")
    
    yield
    
    # Shutdown
    logger.info("Closing database connection pool...")
    close_db_pool()
    logger.info("Application shutdown complete")


def start_application():
    app = FastAPI(title="KAVAS", version="0.1.0", lifespan= lifespan,)
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Update this with your frontend origins in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(voice_router)

    
    # Health check endpoint
    @app.get("/health")
    def health_check():
        return {"status": "healthy"}
    
    return app


app = start_application()
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8005, reload= True)
