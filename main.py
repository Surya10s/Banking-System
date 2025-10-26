# File: main.py
"""Main FastAPI application entry point."""

from fastapi import FastAPI
from db import engine
import schemas
from api.routes import users, transfers, tasks

app = FastAPI(
    title="Money Transfer API",
    description="API for managing user accounts and money transfers",
    version="1.0.0"
)

# Create all tables
schemas.Base.metadata.create_all(bind=engine)

# Include routers
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(transfers.router, prefix="/transfers", tags=["Transfers"])
app.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])


@app.get("/", tags=["Health"])
def home():
    """Health check endpoint."""
    return {"message": "Server is running successfully"}
