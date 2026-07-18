from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.report import ReportCreate, ReportRead, ReportUpdate
from app.services import report_service

router = APIRouter()


@router.post(
    "",
    response_model=ReportRead,
    status_code=status.HTTP_201_CREATED,
    summary="创建报告",
)
async def create_report(
    data: ReportCreate,
    db: AsyncSession = Depends(get_db),
):
    return await report_service.create_report(db, data)


@router.get(
    "",
    response_model=list[ReportRead],
    summary="获取报告列表",
)
async def get_reports(
    db: AsyncSession = Depends(get_db),
):
    return await report_service.get_reports(db)


@router.get(
    "/{report_id}",
    response_model=ReportRead,
    summary="获取报告详情",
)
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
):
    report = await report_service.get_report(db, report_id)

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告不存在",
        )

    return report


@router.patch(
    "/{report_id}",
    response_model=ReportRead,
    summary="更新报告",
)
async def update_report(
    report_id: int,
    data: ReportUpdate,
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
