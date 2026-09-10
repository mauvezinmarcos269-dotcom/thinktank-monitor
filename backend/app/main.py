from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.reports import router as reports_router
from app.api.v1.sources import router as sources_router
from app.api.v1.think_tanks import router as think_tanks_router
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

# ---------------------------------------------------------------------------
# 路由注册区
# ---------------------------------------------------------------------------

app.include_router(
    auth_router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["Authentication"],
)


# 智库管理路由
app.include_router(
    think_tanks_router,
    prefix=f"{settings.API_V1_STR}/think-tanks",
    tags=["Think Tanks"],
)

# 数据源/情报源管理路由
app.include_router(
    sources_router,
    prefix=f"{settings.API_V1_STR}/sources",
    tags=["Sources"],
)

app.include_router(
    reports_router,
    prefix=f"{settings.API_V1_STR}/reports",
    tags=["Reports"],
)

app.include_router(
    notifications_router,
    prefix=f"{settings.API_V1_STR}/notifications",
    tags=["Notifications"],
)

# ---------------------------------------------------------------------------


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
