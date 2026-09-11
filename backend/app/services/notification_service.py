import asyncio
import logging
import smtplib
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage

import httpx
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.crawl_candidate import CrawlCandidate
from app.models.notification import Notification
from app.models.report import Report
from app.models.source import CrawlStatusEnum, Source
from app.models.think_tank import ThinkTank
from app.models.user import User
from app.services.crawl_candidate_service import get_candidate_status_label

logger = logging.getLogger(__name__)


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

    async def create_daily_summary(
        self,
        db: AsyncSession,
        *,
        lookback_hours: int,
    ) -> dict[str, int | str]:
        since = datetime.now(UTC).replace(tzinfo=None) - timedelta(
            hours=lookback_hours
        )
        title, message, metrics = await self._build_summary(
            db,
            since=since,
            lookback_hours=lookback_hours,
        )

        notifications = await self.create_for_all_active_users(
            db,
            event_type="daily_summary",
            title=title,
            message=message,
        )
        await db.commit()
        await self.dispatch_external_summary(title=title, message=message)

        return {
            "status": "success",
            "created_notifications": len(notifications),
            **metrics,
        }

    async def dispatch_external_summary(
        self,
        *,
        title: str,
        message: str,
    ) -> None:
        tasks = []

        if settings.NOTIFICATION_EMAIL_ENABLED:
            tasks.append(
                asyncio.to_thread(
                    self._send_email_summary,
                    title,
                    message,
                )
            )

        if settings.NOTIFICATION_WECOM_WEBHOOK_URL:
            tasks.append(
                self._send_wecom_summary(
                    title=title,
                    message=message,
                )
            )

        if settings.NOTIFICATION_FEISHU_WEBHOOK_URL:
            tasks.append(
                self._send_feishu_summary(
                    title=title,
                    message=message,
                )
            )

        if not tasks:
            return

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.warning("通知摘要外发失败：%s", result)

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

    async def _build_summary(
        self,
        db: AsyncSession,
        *,
        since: datetime,
        lookback_hours: int,
    ) -> tuple[str, str, dict[str, int]]:
        new_reports = await self._count_where(
            db,
            Report,
            Report.created_at >= since,
        )
        failed_sources = await self._count_where(
            db,
            Source,
            Source.last_crawl_status == CrawlStatusEnum.failed,
        )
        saved_candidates = await self._count_where(
            db,
            CrawlCandidate,
            CrawlCandidate.status == "saved",
            CrawlCandidate.created_at >= since,
        )
        skipped_candidates = await self._count_where(
            db,
            CrawlCandidate,
            CrawlCandidate.status == "skipped",
            CrawlCandidate.created_at >= since,
        )
        candidate_rows = (
            await db.execute(
                select(CrawlCandidate.status, func.count(CrawlCandidate.id))
                .where(CrawlCandidate.created_at >= since)
                .group_by(CrawlCandidate.status)
                .order_by(CrawlCandidate.status.asc())
            )
        ).all()
        failure_rows = (
            await db.execute(
                select(Source, ThinkTank.name)
                .join(ThinkTank, ThinkTank.id == Source.think_tank_id)
                .where(Source.last_crawl_status == CrawlStatusEnum.failed)
                .order_by(Source.last_crawled_at.desc().nullslast(), Source.id.desc())
                .limit(5)
            )
        ).all()
        recent_report_rows = (
            await db.execute(
                select(Report.title)
                .where(Report.created_at >= since)
                .order_by(Report.created_at.desc(), Report.id.desc())
                .limit(5)
            )
        ).scalars().all()

        title = f"智库监测 {lookback_hours} 小时摘要"
        candidate_summary = "、".join(
            f"{get_candidate_status_label(status)} {int(count)}"
            for status, count in candidate_rows
        ) or "暂无候选报告更新"
        report_lines = "\n".join(f"- {report_title}" for report_title in recent_report_rows)
        failure_lines = "\n".join(
            f"- {think_tank_name}：{source.last_error or '最近一次抓取失败'}"
            for source, think_tank_name in failure_rows
        )
        message_parts = [
            f"过去 {lookback_hours} 小时新增入库报告 {new_reports} 篇。",
            f"候选报告统计：{candidate_summary}。",
            f"当前失败来源 {failed_sources} 个。",
        ]

        if report_lines:
            message_parts.append(f"最新入库报告：\n{report_lines}")

        if failure_lines:
            message_parts.append(f"最近失败原因：\n{failure_lines}")

        return (
            title,
            "\n\n".join(message_parts),
            {
                "new_reports": new_reports,
                "saved_candidates": saved_candidates,
                "skipped_candidates": skipped_candidates,
                "failed_sources": failed_sources,
            },
        )

    async def _count_where(self, db: AsyncSession, model: type, *conditions) -> int:
        statement = select(func.count(model.id))

        for condition in conditions:
            statement = statement.where(condition)

        value = await db.scalar(statement)
        return int(value or 0)

    def _send_email_summary(self, title: str, message: str) -> None:
        recipients = [
            item.strip()
            for item in settings.NOTIFICATION_EMAIL_TO.split(",")
            if item.strip()
        ]

        if (
            not recipients
            or not settings.NOTIFICATION_SMTP_HOST
            or not settings.NOTIFICATION_SMTP_FROM
        ):
            logger.info("邮件通知未配置完整，跳过摘要邮件发送。")
            return

        email = EmailMessage()
        email["Subject"] = title
        email["From"] = settings.NOTIFICATION_SMTP_FROM
        email["To"] = ", ".join(recipients)
        email.set_content(message)

        with smtplib.SMTP(
            settings.NOTIFICATION_SMTP_HOST,
            settings.NOTIFICATION_SMTP_PORT,
            timeout=20,
        ) as smtp:
            if settings.NOTIFICATION_SMTP_USE_TLS:
                smtp.starttls()

            if settings.NOTIFICATION_SMTP_USERNAME:
                smtp.login(
                    settings.NOTIFICATION_SMTP_USERNAME,
                    settings.NOTIFICATION_SMTP_PASSWORD,
                )

            smtp.send_message(email)

    async def _send_wecom_summary(self, *, title: str, message: str) -> None:
        payload = {
            "msgtype": "text",
            "text": {
                "content": f"{title}\n\n{message}",
            },
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                settings.NOTIFICATION_WECOM_WEBHOOK_URL,
                json=payload,
            )
            response.raise_for_status()

    async def _send_feishu_summary(self, *, title: str, message: str) -> None:
        payload = {
            "msg_type": "text",
            "content": {
                "text": f"{title}\n\n{message}",
            },
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                settings.NOTIFICATION_FEISHU_WEBHOOK_URL,
                json=payload,
            )
            response.raise_for_status()


notification_service = NotificationService()
