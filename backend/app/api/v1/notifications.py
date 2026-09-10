from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import NotificationRead, NotificationUnreadCount
from app.services.notification_service import notification_service

router = APIRouter()


@router.get("", response_model=list[NotificationRead], summary="查询站内通知")
async def list_notifications(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    unread_only: bool = False,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    return await notification_service.get_for_user(
        db,
        user_id=current_user.id,
        unread_only=unread_only,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/unread-count",
    response_model=NotificationUnreadCount,
    summary="查询未读通知数",
)
async def get_unread_count(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> NotificationUnreadCount:
    unread_count = await notification_service.count_unread(
        db,
        user_id=current_user.id,
    )

    return NotificationUnreadCount(unread_count=unread_count)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationRead,
    summary="标记单条通知已读",
)
async def mark_notification_read(
    notification_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    notification = await notification_service.mark_read(
        db,
        user_id=current_user.id,
        notification_id=notification_id,
    )

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="通知不存在。",
        )

    return notification


@router.post("/read-all", summary="标记全部通知已读")
async def mark_all_notifications_read(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, int]:
    updated_count = await notification_service.mark_all_read(
        db,
        user_id=current_user.id,
    )

    return {"updated_count": updated_count}
