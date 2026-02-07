"""Core application setup for Schema Inspector service"""

import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from niagads.database.session import DatabaseSessionManager
from niagads.schema_inspector_service.routes import create_router
from niagads.settings.core import CustomSettings


class Settings(CustomSettings):
    """Settings for Schema Inspector Service"""

    DATABASE_URI: str
    DEBUG: bool = False
    TEMPLATES_DIR: str = None  # Optional override for templates directory


# Initialize settings
settings = Settings.from_env()

# Initialize database session manager
session_manager = DatabaseSessionManager(
    connection_string=settings.DATABASE_URI,
    echo=settings.DEBUG,
)

# Create FastAPI application
app = FastAPI(
    title="GenomicsDB Schema Inspector",
    description="A tool for inspecting database tables by schema, table name, and run_id",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError exceptions"""
    return JSONResponse(
        status_code=400,
        content={"error": "Bad Request", "detail": str(exc)},
    )


@app.exception_handler(KeyError)
async def key_error_handler(request: Request, exc: KeyError):
    """Handle KeyError exceptions (schema/table not found)"""
    return JSONResponse(
        status_code=404,
        content={"error": "Not Found", "detail": str(exc)},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": str(exc)},
    )


# Include routers with templates directory
templates_dir = Settings.from_env().TEMPLATES_DIR
router = create_router(templates_dir, session_manager)
app.include_router(router)


# Lifespan events
@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    # Test database connection
    try:
        await session_manager.test_connection()
        print("✓ Database connection successful")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    # Close database connections
    await session_manager.close()
    print("✓ Database connections closed")


if __name__ == "__main__":
    uvicorn.run(
        "niagads.schema_inspector_service.core:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.DEBUG,
    )
