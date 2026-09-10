from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import RoleEnum, User
from app.schemas.ai_report import AIProgressRead, ManualAIResponse
from app.schemas.report import (
    ManualCrawlResponse,
    ReportCreate,
    ReportListResponse,
    ReportRead,
    ReportUpdate,
)
from app.services import report_service
from app.services.ai.report_ai_chunk_service import get_report_ai_progress
from app.services.report_export_service import (
    build_export_filename,
    build_report_docx,
    build_report_markdown,
)
from app.utils.datetime import utc_now_naive
from app.workers.report_tasks import (
    enqueue_ai_chunk_tasks_task,
    fetch_report_content_task,
)

router = APIRouter()


@router.post(
    "",
    response_model=ReportRead,
    status_code=status.HTTP_201_CREATED,
    summary="创建报告",
)
async def create_report(
    data: ReportCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.admin))],
):
    return await report_service.create_report(db, data)


@router.get(
    "",
    response_model=ReportListResponse,
    summary="获取报告列表",
)
async def get_reports(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ReportListResponse:
    reports = await report_service.get_reports(db, skip=skip, limit=limit)
    total = await report_service.count_reports(db)

    return ReportListResponse(
        items=reports,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{report_id}",
    response_model=ReportRead,
    summary="获取报告详情",
)
async def get_report(
    report_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    report = await report_service.get_report(db, report_id)

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告不存在",
        )

    return report


@router.get(
    "/{report_id}/ai-progress",
    response_model=AIProgressRead,
    summary="获取报告 AI 分块进度",
)
async def get_report_ai_progress_endpoint(
    report_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> AIProgressRead:
    progress = await get_report_ai_progress(db, report_id)

    if progress is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告不存在",
        )

    return progress


@router.get(
    "/{report_id}/export",
    summary="导出报告 AI 成果 Markdown",
)
async def export_report_results(
    report_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> Response:
    report = await report_service.get_report(db, report_id)

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告不存在",
        )

    markdown = build_report_markdown(report)
    filename = build_export_filename(report.id, report.title, "md")
    encoded_filename = quote(filename)

    return Response(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": (
                "attachment; "
                f"filename*=UTF-8''{encoded_filename}"
            ),
        },
    )


@router.get(
    "/{report_id}/export-docx",
    summary="导出报告 AI 成果 Word 文档",
)
async def export_report_results_docx(
    report_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> Response:
    report = await report_service.get_report(db, report_id)

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告不存在",
        )

    content = build_report_docx(report)
    filename = build_export_filename(report.id, report.title, "docx")
    encoded_filename = quote(filename)

    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": (
                "attachment; "
                f"filename*=UTF-8''{encoded_filename}"
            ),
        },
    )


@router.post(
    "/{report_id}/retry-ai",
    response_model=ManualAIResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="手动重试报告 AI 分块处理",
)
async def retry_report_ai(
    report_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.admin))],
) -> ManualAIResponse:
    report = await report_service.get_report(db, report_id)

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告不存在",
        )

    if not report.content:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="报告正文为空，请先抓取正文。",
        )

    if report.ai_status in {
        "processing",
        "finalize_queued",
        "finalizing",
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"报告 {report_id} 的 AI 任务正在处理中，请勿重复提交。",
        )

    report.ai_status = "pending"
    report.updated_at = utc_now_naive()
    await db.commit()
    await db.refresh(report)

    try:
        task = enqueue_ai_chunk_tasks_task.delay(
            1,
            50,
            report.id,
        )
    except Exception as exc:
        report.ai_status = "failed"
        report.updated_at = utc_now_naive()
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="任务队列不可用，请检查 Celery 和 Redis 服务。",
        ) from exc

    return ManualAIResponse(
        message="报告 AI 分块处理任务已提交。",
        report_id=report.id,
        ai_status=report.ai_status,
        task_id=task.id,
        updated_at=report.updated_at,
    )


@router.patch(
    "/{report_id}",
    response_model=ReportRead,
    summary="更新报告",
)
async def update_report(
    report_id: int,
    data: ReportUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.admin))],
):
    report = await report_service.update_report(
        db,
        report_id,
        data,
    )

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告不存在",
        )

    return report


@router.delete(
    "/{report_id}",
    response_model=ReportRead,
    summary="删除报告",
)
async def delete_report(
    report_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.admin))],
):
    report = await report_service.delete_report(
        db,
        report_id,
    )

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告不存在",
        )

    return report


@router.post(
    "/{report_id}/fetch-content",
    response_model=ManualCrawlResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="手动触发报告正文抓取",
)
async def trigger_fetch_content(
    report_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.admin))],
):
    # 1. 验证 Report 存在
    report = await report_service.get_report(db, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告不存在",
        )

    # 2. 任务执行期间禁止重复提交，避免多个 Worker 同时抓取同一 URL
    if report.crawl_status == "running":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"报告 {report_id} 正在抓取中，请勿重复提交",
        )

    # 3. 将状态重置为 pending 并落库
    report.crawl_status = "pending"
    report.crawl_error = None
    report.updated_at = utc_now_naive()
    await db.commit()
    await db.refresh(report)

    # 4. 调用 Celery 任务，并加入队列异常兜底机制
    try:
        task = fetch_report_content_task.delay(report_id)
    except Exception as exc:
        report.crawl_status = "failed"
        report.crawl_error = f"任务投递失败: {str(exc)[:1800]}"
        report.updated_at = utc_now_naive()
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="任务队列不可用，请检查 Celery 和 Redis 服务。",
        ) from exc

    # 5. 返回 202 Accepted 和标准化任务响应
    return ManualCrawlResponse(
        message="报告正文抓取任务已提交。",
        report_id=report.id,
        crawl_status=report.crawl_status,
        task_id=task.id,
        updated_at=report.updated_at,
    )
