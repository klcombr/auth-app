"""Autenticação Fullstack - Sistema completo com JWT, Refresh Tokens e RBAC"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from app.models import init_db
from app.routers import auth, users

app = FastAPI(
    title="AuthAPI",
    description="Sistema completo de autenticação com JWT, refresh tokens e controle de acesso",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["autenticação"])
app.include_router(users.router, prefix="/api/users", tags=["usuarios"])


@app.on_event("startup")
async def on_startup():
    init_db()


@app.get("/")
async def root():
    return {
        "message": "AuthAPI - Sistema de Autenticação Completo",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
