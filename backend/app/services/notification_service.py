from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.content_kind import get_content_kind_label
from app.core.status import NotificationEventType
from app.models.notification import Notification
from app.models.report import Report
from app.models.source import Source
from app.models.think_tank import PriorityTierEnum, ThinkTank
from app.models.user import RoleEnum, User
from app.services.notification_dispatcher import (
    dispatch_external_notification,
    dispatch_external_summary,
    send_email_summary,
    send_feishu_summary,
    send_wecom_summary,
)
from app.services.notification_summary import build_daily_summary, count_where

INSTANT_ALERT_EVENT_TYPES = {
    NotificationEventType.report_created.value,
    NotificationEventType.report_ai_completed.value,
    NotificationEventType.report_ai_failed.value,
}

INSTANT_ALERT_PRIORITY_TIERS = {
    PriorityTierEnum.p0,
    PriorityTierEnum.p1,
}


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

        await self.dispatch_instant_report_alert_if_needed(
            db,
            event_type=event_type,
            title=title,
            message=message,
            report_id=report_id,
        )

        return notifications

    async def create_for_roles(
        self,
        db: AsyncSession,
        *,
        roles: set[RoleEnum],
        event_type: str,
        title: str,
        message: str,
        report_id: int | None = None,
    ) -> list[Notification]:
        if not roles:
            return []

        result = await db.execute(
            select(User.id).where(
                User.is_active.is_(True),
                User.role.in_(roles),
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

        await self.dispatch_instant_report_alert_if_needed(
            db,
            event_type=event_type,
            title=title,
            message=message,
            report_id=report_id,
        )

        return notifications

    async def create_daily_summary(
        self,
        db: AsyncSession,
        *,
        lookback_hours: int,
    ) -> dict[str, int | str]:
        since = datetime.now(UTC).replace(tzinfo=None) - timedelta(
            hours=lookback_hours
        )
        summary = await build_daily_summary(
            db,
            since=since,
            lookback_hours=lookback_hours,
        )

        notifications = await self.create_for_all_active_users(
            db,
            event_type=NotificationEventType.daily_summary.value,
            title=summary.title,
            message=summary.message,
        )
        await db.commit()
        await self.dispatch_external_summary(
            title=summary.title,
            message=summary.message,
        )

        return {
            "status": "success",
            "created_notifications": len(notifications),
            **summary.metrics,
        }

    async def dispatch_external_summary(
        self,
        *,
        title: str,
        message: str,
    ) -> None:
        await dispatch_external_summary(
            title=title,
            message=message,
        )

    async def dispatch_instant_report_alert_if_needed(
        self,
        db: AsyncSession,
        *,
        event_type: str,
        title: str,
        message: str,
        report_id: int | None,
    ) -> None:
        if not self._should_consider_instant_alert(
            event_type=event_type,
            report_id=report_id,
        ):
            return

        alert_context = await self._get_report_alert_context(
            db,
            report_id=report_id,
        )

        if alert_context is None:
            return

        report_title, report_url, think_tank_name, priority_tier = alert_context

        if priority_tier not in INSTANT_ALERT_PRIORITY_TIERS:
            return

        alert_message = "\n".join(
            [
                f"来源：{think_tank_name}",
                f"报告：{report_title}",
                f"链接：{report_url}",
                "",
                message,
            ]
        )

        await dispatch_external_notification(
            title=title,
            message=alert_message,
        )

    def _should_consider_instant_alert(
        self,
        *,
        event_type: str,
        report_id: int | None,
    ) -> bool:
        return (
            settings.NOTIFICATION_INSTANT_ALERTS_ENABLED
            and report_id is not None
            and event_type in INSTANT_ALERT_EVENT_TYPES
        )

    async def _get_report_alert_context(
        self,
        db: AsyncSession,
        *,
        report_id: int | None,
    ) -> tuple[str, str, str, PriorityTierEnum] | None:
        if report_id is None:
            return None

        result = await db.execute(
            select(
                Report.title,
                Report.url,
                ThinkTank.name,
                ThinkTank.priority_tier,
            )
            .join(Source, Source.id == Report.source_id)
            .join(ThinkTank, ThinkTank.id == Source.think_tank_id)
            .where(Report.id == report_id)
        )

        row = result.one_or_none()

        if row is None:
            return None

        report_title, report_url, think_tank_name, priority_tier = row

        return (
            report_title,
            report_url,
            think_tank_name,
            priority_tier,
        )

    async def get_for_user(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        unread_only: bool = False,
        event_type: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Notification]:
        statement = select(Notification).where(Notification.user_id == user_id)

        if unread_only:
            statement = statement.where(Notification.is_read.is_(False))

        if event_type:
            statement = statement.where(Notification.event_type == event_type)

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

    async def _build_summary(
        self,
        db: AsyncSession,
        *,
        since: datetime,
        lookback_hours: int,
    ) -> tuple[str, str, dict[str, int]]:
        summary = await build_daily_summary(
            db,
            since=since,
            lookback_hours=lookback_hours,
        )
        return summary.title, summary.message, summary.metrics

    async def _count_where(self, db: AsyncSession, model: type, *conditions) -> int:
        return await count_where(db, model, *conditions)

    def _format_content_kind(self, value: str | None) -> str:
        return get_content_kind_label(value)

    def _send_email_summary(self, title: str, message: str) -> None:
        send_email_summary(title, message)

    async def _send_wecom_summary(self, *, title: str, message: str) -> None:
        await send_wecom_summary(
            title=title,
            message=message,
        )

    async def _send_feishu_summary(self, *, title: str, message: str) -> None:
        await send_feishu_summary(
            title=title,
            message=message,
        )


notification_service = NotificationService()
