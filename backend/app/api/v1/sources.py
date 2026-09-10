from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.source import SourceTypeEnum
from app.models.user import RoleEnum, User
from app.schemas.institution import (
    CrawlCandidateListResponse,
    CrawlCandidateStatisticsResponse,
    SourceCrawlRunListResponse,
    SourceHealthListResponse,
    SourceRead,
    SourceUpdate,
)
from app.services.crawl_candidate_service import crawl_candidate_service
from app.services.source_service import source_service
from app.utils.datetime import utc_now_naive
from app.workers.crawl_tasks import crawl_source_task

router = APIRouter(tags=["数据源"])


@router.get("", response_model=list[SourceRead], summary="查询来源列表")
async def list_all_sources(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    source_type: SourceTypeEnum | None = None,
    is_active: bool | None = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
):
    return await source_service.get_multi(
        db,
        source_type=source_type,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )


@router.get("/health", response_model=SourceHealthListResponse, summary="查询来源健康状态")
async def list_source_health(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    is_active: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 500,
):
    return await source_service.get_health(
        db,
        is_active=is_active,
        limit=limit,
    )


@router.get(
    "/crawl-runs",
    response_model=SourceCrawlRunListResponse,
    summary="查询来源抓取运行历史",
)
async def list_source_crawl_runs(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    source_id: Annotated[int | None, Query(gt=0)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    return await source_service.get_recent_crawl_runs(
        db,
        source_id=source_id,
        limit=limit,
    )


@router.get(
    "/crawl-candidates/export",
    summary="导出抓取候选报告明细 CSV",
)
async def export_crawl_candidates(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    crawl_run_id: Annotated[int | None, Query(gt=0)] = None,
    source_id: Annotated[int | None, Query(gt=0)] = None,
    candidate_status: str | None = None,
    skip_reason_code: str | None = None,
    skip_reason_label: str | None = None,
) -> Response:
    csv_text = await crawl_candidate_service.build_csv(
        db,
        crawl_run_id=crawl_run_id,
        source_id=source_id,
        status=candidate_status,
        skip_reason_code=skip_reason_code,
        skip_reason_label=skip_reason_label,
    )
    scope = f"run-{crawl_run_id}" if crawl_run_id else f"source-{source_id or 'all'}"
    date_part = utc_now_naive().strftime("%Y%m%d")
    filename = f"crawl-candidates-{scope}-{date_part}.csv"
    encoded_filename = quote(filename)

    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                "attachment; "
                f"filename*=UTF-8''{encoded_filename}"
            ),
        },
    )


@router.get(
    "/crawl-candidates/statistics",
    response_model=CrawlCandidateStatisticsResponse,
    summary="查询抓取候选报告统计",
)
async def get_crawl_candidate_statistics(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    crawl_run_id: Annotated[int | None, Query(gt=0)] = None,
    source_id: Annotated[int | None, Query(gt=0)] = None,
):
    return await crawl_candidate_service.get_statistics(
        db,
        crawl_run_id=crawl_run_id,
        source_id=source_id,
    )


@router.get(
    "/crawl-candidates",
    response_model=CrawlCandidateListResponse,
    summary="查询抓取候选报告明细",
)
async def list_crawl_candidates(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    crawl_run_id: Annotated[int | None, Query(gt=0)] = None,
    source_id: Annotated[int | None, Query(gt=0)] = None,
    candidate_status: str | None = None,
    skip_reason_code: str | None = None,
    skip_reason_label: str | None = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
):
    return await crawl_candidate_service.get_recent_candidates(
        db,
        crawl_run_id=crawl_run_id,
        source_id=source_id,
        status=candidate_status,
        skip_reason_code=skip_reason_code,
        skip_reason_label=skip_reason_label,
        skip=skip,
        limit=limit,
    )


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

    if source.source_type not in {
        SourceTypeEnum.rss,
        SourceTypeEnum.website,
    }:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="当前手动抓取仅支持 RSS 和 website 类型来源。",
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
