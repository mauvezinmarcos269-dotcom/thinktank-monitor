from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.user import User


class NotificationService:
    async def create_for_all_active_users(
        self,
        db: AsyncSession,
        *,
        event_type: str,
        title: str,
        message: str,
        report_id: int | None = None,
    ) -> list[Notification]:
        result = await db.execute(
            select(User.id).where(
                User.is_active.is_(True),
            )
        )

        user_ids = list(result.scalars().all())

        notifications = [
            Notification(
                user_id=user_id,
                report_id=report_id,
                event_type=event_type,
                title=title[:255],
                message=message,
                is_read=False,
            )
            for user_id in user_ids
        ]

        db.add_all(notifications)
        await db.flush()

        return notifications

    async def get_for_user(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Notification]:
        statement = select(Notification).where(Notification.user_id == user_id)

        if unread_only:
            statement = statement.where(Notification.is_read.is_(False))

        statement = (
            statement.order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(statement)
        return list(result.scalars().all())

    async def count_unread(
        self,
        db: AsyncSession,
        *,
        user_id: int,
    ) -> int:
        count = await db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )

        return count or 0

    async def mark_read(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        notification_id: int,
    ) -> Notification | None:
        result = await db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )

        notification = result.scalar_one_or_none()

        if notification is None:
            return None

        notification.is_read = True
        await db.commit()
        await db.refresh(notification)

        return notification

    async def mark_all_read(
        self,
        db: AsyncSession,
        *,
        user_id: int,
    ) -> int:
        result = await db.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True)
        )

        await db.commit()

        return result.rowcount or 0


notification_service = NotificationService()
