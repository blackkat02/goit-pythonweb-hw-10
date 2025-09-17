"""
Main entry point for the FastAPI application.

This module initializes the FastAPI application, includes the API router,
and defines the startup command for the server.
"""

import uvicorn
from fastapi import FastAPI
from src.api.v1.router import router as api_router

# Create the FastAPI application instance.
app = FastAPI(
    title="Contacts API",  # Provides a title for the OpenAPI documentation
    description="A simple REST API for managing contacts.",  # A description for the OpenAPI docs
    version="1.0.0",  # API version
)

# Include the main API router under the `/api` prefix.
# This keeps the main application logic separate from the API endpoints.
app.include_router(api_router, prefix="/api")

# The `if __name__ == "__main__":` block is for local development.
# In a production environment (e.g., in a Docker container), the `CMD`
# from the Dockerfile will be used to run the application, not this block.
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
