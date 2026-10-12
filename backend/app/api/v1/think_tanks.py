from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.source import SourceTypeEnum
from app.models.think_tank import OrganizationTypeEnum
from app.models.user import RoleEnum, User
from app.schemas.institution import (
    SourceCreate,
    SourceRead,
    ThinkTankCreate,
    ThinkTankDetailRead,
    ThinkTankRead,
    ThinkTankUpdate,
)
from app.services.source_service import source_service
from app.services.think_tank_service import think_tank_service

router = APIRouter(tags=["智库机构"])

@router.get("", response_model=list[ThinkTankRead], summary="查询智库机构列表")
async def list_think_tanks(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    q: Annotated[str | None, Query(max_length=100, description="按中文名、英文名、国家/地区模糊搜索。")] = None,
    country: Annotated[str | None, Query(max_length=100)] = None,
    organization_type: OrganizationTypeEnum | None = None,
    parent_id: int | None = None,
    is_key: bool | None = None,
    is_active: bool | None = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    return await think_tank_service.get_multi(
        db, q=q, country=country, organization_type=organization_type,
        parent_id=parent_id, is_key=is_key, is_active=is_active, skip=skip, limit=limit
    )

@router.get("/countries", response_model=list[str], summary="查询已录入的国家和地区")
async def list_countries(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    return await think_tank_service.get_countries(db)


@router.get(
    "/missing-sources",
    response_model=list[ThinkTankRead],
    summary="查询尚未配置启用来源的机构",
)
async def list_think_tanks_missing_sources(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
):
    return await think_tank_service.get_without_active_sources(
        db,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/statistics",
    response_model=dict[str, int],
    summary="获取机构和来源统计信息"
)
async def get_institution_statistics(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> dict[str, int]:
    return await think_tank_service.get_statistics(db)

@router.get("/{think_tank_id}", response_model=ThinkTankDetailRead, summary="查询智库机构详情")
async def get_think_tank(
    think_tank_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    return await think_tank_service.get_by_id(db, think_tank_id, load_sources=True)

@router.post("", response_model=ThinkTankRead, status_code=status.HTTP_201_CREATED, summary="创建智库机构")
async def create_think_tank(
    payload: ThinkTankCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.admin))],
):
    return await think_tank_service.create(db, payload)

@router.patch("/{think_tank_id}", response_model=ThinkTankRead, summary="更新智库机构")
async def update_think_tank(
    think_tank_id: int,
    payload: ThinkTankUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.admin))],
):
    return await think_tank_service.update(db, think_tank_id, payload)

@router.delete("/{think_tank_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除智库机构及其来源")
async def delete_think_tank(
    think_tank_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.admin))],
):
    await think_tank_service.delete(db, think_tank_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- 智库嵌套资源的路由 ---

@router.get("/{think_tank_id}/sources", response_model=list[SourceRead], summary="查询某个智库的来源列表")
async def list_sources(
    think_tank_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    source_type: SourceTypeEnum | None = None,
    is_active: bool | None = None,
):
    # 先校验智库是否存在
    await think_tank_service.get_by_id(db, think_tank_id)
    return await source_service.get_by_think_tank(db, think_tank_id, source_type, is_active)

@router.post("/{think_tank_id}/sources", response_model=SourceRead, status_code=status.HTTP_201_CREATED, summary="为智库添加来源")
async def create_source(
    think_tank_id: int,
    payload: SourceCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.admin))],
):
    await think_tank_service.get_by_id(db, think_tank_id)
    return await source_service.create(db, think_tank_id, payload)
