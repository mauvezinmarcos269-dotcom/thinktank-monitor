from io import BytesIO
from typing import Annotated, Literal
from urllib.parse import quote
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.core.content_kind import ReportContentKind
from app.core.status import ReportAIStatus, ReportCrawlStatus, ReportReviewStatus
from app.db.session import get_db
from app.models.user import RoleEnum, User
from app.schemas.ai_report import AIProgressRead, ManualAIResponse
from app.schemas.report import (
    ManualCrawlResponse,
    ReportBatchExportRequest,
    ReportBatchReviewResponse,
    ReportBatchReviewUpdate,
    ReportCreate,
    ReportListResponse,
    ReportRead,
    ReportReviewEventRead,
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
    review_status: ReportReviewStatus | None = None,
    ai_status: ReportAIStatus | None = None,
    content_kind: ReportContentKind | None = None,
    deliverable_status: Literal["complete", "partial", "empty"] | None = None,
    keyword: Annotated[str | None, Query(max_length=200)] = None,
    think_tank_id: Annotated[int | None, Query(gt=0)] = None,
    source_id: Annotated[int | None, Query(gt=0)] = None,
) -> ReportListResponse:
    reports = await report_service.get_reports(
        db,
        skip=skip,
        limit=limit,
        review_status=review_status,
        ai_status=ai_status,
        content_kind=content_kind,
        deliverable_status=deliverable_status,
        keyword=keyword,
        think_tank_id=think_tank_id,
        source_id=source_id,
    )
    total = await report_service.count_reports(
        db,
        review_status=review_status,
        ai_status=ai_status,
        content_kind=content_kind,
        deliverable_status=deliverable_status,
        keyword=keyword,
        think_tank_id=think_tank_id,
        source_id=source_id,
    )

    return ReportListResponse(
        items=reports,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.patch(
    "/batch-review",
    response_model=ReportBatchReviewResponse,
    summary="批量更新报告复核状态",
)
async def batch_update_report_review_status(
    data: ReportBatchReviewUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.admin))],
) -> ReportBatchReviewResponse:
    updated_reports = []
    not_found_ids = []

    for report_id in dict.fromkeys(data.report_ids):
        report = await report_service.update_report(
            db,
            report_id,
            ReportUpdate(review_status=data.review_status),
            reviewer_id=current_user.id,
        )

        if report is None:
            not_found_ids.append(report_id)
        else:
            updated_reports.append(report)

    return ReportBatchReviewResponse(
        items=updated_reports,
        updated_count=len(updated_reports),
        not_found_ids=not_found_ids,
    )


@router.post(
    "/batch-export",
    summary="批量导出报告 AI 成果压缩包",
)
async def batch_export_report_results(
    data: ReportBatchExportRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> Response:
    report_ids = list(dict.fromkeys(data.report_ids))
    extension = "docx" if data.export_format == "docx" else "md"
    not_found_ids: list[int] = []
    exported_count = 0
    archive_buffer = BytesIO()

    with ZipFile(archive_buffer, "w", ZIP_DEFLATED) as archive:
        for report_id in report_ids:
            report = await report_service.get_report(db, report_id)

            if report is None:
                not_found_ids.append(report_id)
                continue

            filename = build_export_filename(report.id, report.title, extension)
            content = (
                build_report_docx(report)
                if data.export_format == "docx"
                else build_report_markdown(report).encode("utf-8")
            )
            archive.writestr(filename, content)
            exported_count += 1

        if not_found_ids:
            archive.writestr(
                "missing-report-ids.txt",
                "\n".join(str(report_id) for report_id in not_found_ids),
            )

    if exported_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="所选报告不存在",
        )

    archive_buffer.seek(0)
    filename = (
        f"thinktank-reports-{data.export_format}-"
        f"{utc_now_naive():%Y%m%d-%H%M%S}.zip"
    )
    encoded_filename = quote(filename)

    return Response(
        content=archive_buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                "attachment; "
                f"filename*=UTF-8''{encoded_filename}"
            ),
        },
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
    "/{report_id}/review-events",
    response_model=list[ReportReviewEventRead],
    summary="获取报告复核历史",
)
async def get_report_review_events(
    report_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[ReportReviewEventRead]:
    events = await report_service.get_report_review_events(db, report_id)

    if events is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告不存在",
        )

    return [
        ReportReviewEventRead(
            id=event.id,
            report_id=event.report_id,
            review_status=event.review_status,
            review_note=event.review_note,
            reviewer_id=event.reviewer_id,
            reviewer_email=event.reviewer.email if event.reviewer else None,
            created_at=event.created_at,
        )
        for event in events
    ]


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
        ReportAIStatus.processing.value,
        ReportAIStatus.finalize_queued.value,
        ReportAIStatus.finalizing.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"报告 {report_id} 的 AI 任务正在处理中，请勿重复提交。",
        )

    previous_review_status = report.review_status
    report.ai_status = ReportAIStatus.pending.value
    report.review_status = ReportReviewStatus.pending_review.value
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
        report.ai_status = ReportAIStatus.failed.value
        report.review_status = previous_review_status
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
        review_status=report.review_status,
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
    current_user: Annotated[User, Depends(require_roles(RoleEnum.admin))],
):
    report = await report_service.update_report(
        db,
        report_id,
        data,
        reviewer_id=current_user.id,
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
    if report.crawl_status == ReportCrawlStatus.running.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"报告 {report_id} 正在抓取中，请勿重复提交",
        )

    # 3. 将状态重置为 pending 并落库
    report.crawl_status = ReportCrawlStatus.pending.value
    report.crawl_error = None
    report.updated_at = utc_now_naive()
    await db.commit()
    await db.refresh(report)

    # 4. 调用 Celery 任务，并加入队列异常兜底机制
    try:
        task = fetch_report_content_task.delay(report_id)
    except Exception as exc:
        report.crawl_status = ReportCrawlStatus.failed.value
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
