from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.source import SourceTypeEnum
from app.models.user import RoleEnum, User
from app.schemas.institution import SourceRead, SourceUpdate
from app.services.source_service import source_service
from app.workers.crawl_tasks import crawl_source_task

router = APIRouter(tags=["数据源"])

@router.post(
    "/{source_id}/crawl",
    status_code=status.HTTP_202_ACCEPTED,
    summary="手动触发来源抓取",
)
async def trigger_source_crawl(
    source_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.admin))],
):
    source = await source_service.get_by_id(db, source_id)

    if not source.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="来源已停用，不能执行抓取。",
        )

    if source.source_type != SourceTypeEnum.rss:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="当前手动抓取仅支持 RSS 类型来源。",
        )

    task = crawl_source_task.delay(source_id)

    return {
        "message": "抓取任务已提交。",
        "source_id": source_id,
        "task_id": task.id,
    }

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
