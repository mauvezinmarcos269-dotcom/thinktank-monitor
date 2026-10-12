from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def dispatch_external_notification(
    *,
    title: str,
    message: str,
) -> None:
    tasks = []

    if settings.NOTIFICATION_EMAIL_ENABLED:
        tasks.append(
            asyncio.to_thread(
                send_email_summary,
                title,
                message,
            )
        )

    if settings.NOTIFICATION_WECOM_WEBHOOK_URL:
        tasks.append(
            send_wecom_summary(
                title=title,
                message=message,
            )
        )

    if settings.NOTIFICATION_FEISHU_WEBHOOK_URL:
        tasks.append(
            send_feishu_summary(
                title=title,
                message=message,
            )
        )

    if not tasks:
        return

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            logger.warning("通知外发失败：%s", result)


async def dispatch_external_summary(
    *,
    title: str,
    message: str,
) -> None:
    await dispatch_external_notification(
        title=title,
        message=message,
    )


def send_email_summary(title: str, message: str) -> None:
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


async def send_wecom_summary(*, title: str, message: str) -> None:
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


async def send_feishu_summary(*, title: str, message: str) -> None:
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
