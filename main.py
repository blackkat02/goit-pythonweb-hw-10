"""
Main entry point for the FastAPI application.

This module initializes the FastAPI application, includes the API router,
and defines the startup command for the server.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
from contextlib import asynccontextmanager
from src.api.v1.router import router as api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Use 'redis' as the hostname, not 'localhost'
    redis_connection = redis.from_url("redis://redis:6379", encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(redis_connection)
    print("FastAPILimiter initialized. Startup complete.")
    yield
    print("Application shutting down.")
    await FastAPILimiter.close()


# Create the FastAPI application instance.
app = FastAPI(
    lifespan=lifespan,
    title="Contacts API",  # Provides a title for the OpenAPI documentation
    description="A simple REST API for managing contacts.",  # A description for the OpenAPI docs
    version="1.0.0",  # API version
)

# CORS configuration
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the main API router under the `/api` prefix.
# This keeps the main application logic separate from the API endpoints.
app.include_router(api_router, prefix="/api")


# The `if __name__ == "__main__":` block is for local development.
# In a production environment (e.g., in a Docker container), the `CMD`
# from the Dockerfile will be used to run the application, not this block.
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
