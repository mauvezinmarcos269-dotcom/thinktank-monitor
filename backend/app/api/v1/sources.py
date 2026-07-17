from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.user import RoleEnum, User
from app.schemas.institution import SourceRead, SourceUpdate
from app.services.source_service import source_service

router = APIRouter(tags=["数据源"])

@router.patch("/{source_id}", response_model=SourceRead, summary="更新来源")
async def update_source(
    source_id: int,
    payload: SourceUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.admin))],
):
    return await source_service.update(db, source_id, payload)

@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除来源")
async def delete_source(
    source_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.admin))],
):
    await source_service.delete(db, source_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
