from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.core.config import settings
from app.core.logger import setup_logging
from app.db.session import engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()

    yield

    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    auth_router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["Authentication"],
)


@app.get(
    "/",
    summary="服务根路径",
)
async def root() -> dict[str, str]:
    return {
        "message": "ThinkTank Monitor API",
    }


@app.get(
    "/health",
    summary="健康检查",
)
async def health() -> dict[str, str]:
    return {
        "status": "ok",
    }