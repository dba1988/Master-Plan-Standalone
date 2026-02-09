from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.lib.config import settings
from app.features.health.routes import router as health_router
from app.features.auth.routes import router as auth_router
from app.features.projects.routes import router as projects_router

app = FastAPI(
    title="Master Plan Admin API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api", tags=["Health"])
app.include_router(auth_router, prefix="/api", tags=["Authentication"])
app.include_router(projects_router, prefix="/api", tags=["Projects"])


@app.get("/")
async def root():
    return {"message": "Master Plan Admin API", "docs": "/docs"}
