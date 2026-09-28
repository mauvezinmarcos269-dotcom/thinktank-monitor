import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1 import notifications as notifications_api
from app.core.config import settings
from app.core.status import NotificationEventType
from app.models.notification import Notification
from app.models.think_tank import PriorityTierEnum
from app.models.user import RoleEnum
from app.services import notification_dispatcher
from app.services import notification_service as notification_service_module
from app.services.notification_service import NotificationService


def test_format_content_kind_returns_chinese_label() -> None:
    service = NotificationService()

    assert service._format_content_kind("pdf") == "PDF 报告"
    assert service._format_content_kind("web_article") == "网页长文"
    assert service._format_content_kind(None) == "未知类型"


def test_notifications_endpoint_rejects_unknown_event_type() -> None:
    app = FastAPI()
    app.include_router(notifications_api.router, prefix="/notifications")
    client = TestClient(app)

    async def fake_get_db():
        yield object()

    async def fake_get_current_user():
        return type("User", (), {"id": 7})()

    app.dependency_overrides[notifications_api.get_db] = fake_get_db
    app.dependency_overrides[
        notifications_api.get_current_user
    ] = fake_get_current_user

    response = client.get(
        "/notifications",
        params={"event_type": "report.unknown"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_notifications_endpoint_passes_event_type_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_get_for_user(
        db: object,
        *,
        user_id: int,
        unread_only: bool,
        event_type: str | None,
        skip: int,
        limit: int,
    ) -> list[object]:
        captured.update(
            {
                "user_id": user_id,
                "unread_only": unread_only,
                "event_type": event_type,
                "skip": skip,
                "limit": limit,
            }
        )
        return []

    monkeypatch.setattr(
        notifications_api.notification_service,
        "get_for_user",
        fake_get_for_user,
    )

    response = await notifications_api.list_notifications(
        object(),  # type: ignore[arg-type]
        type("User", (), {"id": 7})(),  # type: ignore[arg-type]
        unread_only=True,
        event_type=NotificationEventType.report_review_needs_rerun,
        skip=10,
        limit=20,
    )

    assert response == []
    assert captured == {
        "user_id": 7,
        "unread_only": True,
        "event_type": NotificationEventType.report_review_needs_rerun.value,
        "skip": 10,
        "limit": 20,
    }


@pytest.mark.asyncio
async def test_dispatch_external_summary_returns_without_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[str] = []

    monkeypatch.setattr(settings, "NOTIFICATION_EMAIL_ENABLED", False)
    monkeypatch.setattr(settings, "NOTIFICATION_WECOM_WEBHOOK_URL", "")
    monkeypatch.setattr(settings, "NOTIFICATION_FEISHU_WEBHOOK_URL", "")
    monkeypatch.setattr(
        notification_dispatcher,
        "send_email_summary",
        lambda *_args, **_kwargs: called.append("email"),
    )
    monkeypatch.setattr(
        notification_dispatcher,
        "send_wecom_summary",
        lambda **_kwargs: called.append("wecom"),
    )
    monkeypatch.setattr(
        notification_dispatcher,
        "send_feishu_summary",
        lambda **_kwargs: called.append("feishu"),
    )

    await notification_dispatcher.dispatch_external_summary(
        title="日报",
        message="暂无更新",
    )

    assert called == []


@pytest.mark.asyncio
async def test_dispatch_external_summary_invokes_configured_channels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[tuple[str, str, str]] = []

    def fake_email(title: str, message: str) -> None:
        called.append(("email", title, message))

    async def fake_wecom_summary(*, title: str, message: str) -> None:
        called.append(("wecom", title, message))

    async def fake_feishu_summary(*, title: str, message: str) -> None:
        called.append(("feishu", title, message))

    monkeypatch.setattr(settings, "NOTIFICATION_EMAIL_ENABLED", True)
    monkeypatch.setattr(settings, "NOTIFICATION_WECOM_WEBHOOK_URL", "https://wecom")
    monkeypatch.setattr(settings, "NOTIFICATION_FEISHU_WEBHOOK_URL", "https://feishu")
    monkeypatch.setattr(notification_dispatcher, "send_email_summary", fake_email)
    monkeypatch.setattr(
        notification_dispatcher,
        "send_wecom_summary",
        fake_wecom_summary,
    )
    monkeypatch.setattr(
        notification_dispatcher,
        "send_feishu_summary",
        fake_feishu_summary,
    )

    await notification_dispatcher.dispatch_external_summary(
        title="日报",
        message="新增 3 篇报告",
    )

    assert sorted(called) == [
        ("email", "日报", "新增 3 篇报告"),
        ("feishu", "日报", "新增 3 篇报告"),
        ("wecom", "日报", "新增 3 篇报告"),
    ]


@pytest.mark.asyncio
async def test_dispatch_external_summary_logs_channel_errors(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def fail_wecom_summary(*, title: str, message: str) -> None:
        raise RuntimeError(f"{title}:{message}")

    monkeypatch.setattr(settings, "NOTIFICATION_EMAIL_ENABLED", False)
    monkeypatch.setattr(settings, "NOTIFICATION_WECOM_WEBHOOK_URL", "https://wecom")
    monkeypatch.setattr(settings, "NOTIFICATION_FEISHU_WEBHOOK_URL", "")
    monkeypatch.setattr(
        notification_dispatcher,
        "send_wecom_summary",
        fail_wecom_summary,
    )

    with caplog.at_level(logging.WARNING):
        await notification_dispatcher.dispatch_external_summary(
            title="日报",
            message="外发失败",
        )

    assert "通知外发失败" in caplog.text


def test_send_email_summary_skips_when_config_incomplete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ForbiddenSMTP:
        def __init__(self, *_args, **_kwargs) -> None:
            raise AssertionError("SMTP should not be opened without full config")

    monkeypatch.setattr(settings, "NOTIFICATION_EMAIL_TO", "")
    monkeypatch.setattr(settings, "NOTIFICATION_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "NOTIFICATION_SMTP_FROM", "alerts@example.com")
    monkeypatch.setattr(notification_dispatcher.smtplib, "SMTP", ForbiddenSMTP)

    notification_dispatcher.send_email_summary("日报", "暂无更新")


class _FakeAlertContextResult:
    def __init__(self, row: object | None) -> None:
        self.row = row

    def one_or_none(self) -> object | None:
        return self.row


class _FakeAlertDb:
    def __init__(self, row: object | None) -> None:
        self.row = row

    async def execute(self, statement: object) -> _FakeAlertContextResult:
        return _FakeAlertContextResult(self.row)


class _FakeRoleScalars:
    def __init__(self, values: list[int]) -> None:
        self.values = values

    def all(self) -> list[int]:
        return self.values


class _FakeRoleResult:
    def __init__(self, values: list[int]) -> None:
        self.values = values

    def scalars(self) -> _FakeRoleScalars:
        return _FakeRoleScalars(self.values)


class _FakeRoleDb:
    def __init__(self, user_ids: list[int]) -> None:
        self.user_ids = user_ids
        self.added: list[Notification] = []
        self.flushed = False

    async def execute(self, statement: object) -> _FakeRoleResult:
        return _FakeRoleResult(self.user_ids)

    def add_all(self, notifications: list[Notification]) -> None:
        self.added.extend(notifications)

    async def flush(self) -> None:
        self.flushed = True


@pytest.mark.asyncio
async def test_create_for_roles_targets_active_users_with_selected_roles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[tuple[str, str, int | None]] = []

    async def fake_dispatch(
        self: NotificationService,
        db: object,
        *,
        event_type: str,
        title: str,
        message: str,
        report_id: int | None,
    ) -> None:
        called.append((event_type, title, report_id))

    monkeypatch.setattr(
        NotificationService,
        "dispatch_instant_report_alert_if_needed",
        fake_dispatch,
    )

    db = _FakeRoleDb([1, 3])
    notifications = await NotificationService().create_for_roles(
        db,  # type: ignore[arg-type]
        roles={RoleEnum.admin},
        event_type=NotificationEventType.report_review_needs_rerun.value,
        title="报告需重跑",
        message="Sample report",
        report_id=12,
    )

    assert notifications == db.added
    assert db.flushed is True
    assert [notification.user_id for notification in notifications] == [1, 3]
    assert {notification.event_type for notification in notifications} == {
        NotificationEventType.report_review_needs_rerun.value
    }
    assert called == [
        (
            NotificationEventType.report_review_needs_rerun.value,
            "报告需重跑",
            12,
        )
    ]


@pytest.mark.asyncio
async def test_instant_alerts_are_disabled_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[tuple[str, str]] = []

    async def fake_dispatch(*, title: str, message: str) -> None:
        called.append((title, message))

    monkeypatch.setattr(settings, "NOTIFICATION_INSTANT_ALERTS_ENABLED", False)
    monkeypatch.setattr(
        notification_service_module,
        "dispatch_external_notification",
        fake_dispatch,
    )

    await NotificationService().dispatch_instant_report_alert_if_needed(
        _FakeAlertDb(
            (
                "Report title",
                "https://example.org/report",
                "RAND Corporation",
                PriorityTierEnum.p0,
            )
        ),
        event_type=NotificationEventType.report_created.value,
        title="发现新的涉华智库报告",
        message="Report title",
        report_id=1,
    )

    assert called == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("event_type", "title", "message"),
    [
        (
            NotificationEventType.report_ai_completed.value,
            "报告翻译与评论已完成",
            "Report title",
        ),
        (
            NotificationEventType.report_ai_failed.value,
            "报告 AI 处理失败，请处理",
            "Report title: 模型调用失败",
        ),
    ],
)
async def test_instant_alerts_dispatch_for_p0_report_events(
    monkeypatch: pytest.MonkeyPatch,
    event_type: str,
    title: str,
    message: str,
) -> None:
    called: list[tuple[str, str]] = []

    async def fake_dispatch(*, title: str, message: str) -> None:
        called.append((title, message))

    monkeypatch.setattr(settings, "NOTIFICATION_INSTANT_ALERTS_ENABLED", True)
    monkeypatch.setattr(
        notification_service_module,
        "dispatch_external_notification",
        fake_dispatch,
    )

    await NotificationService().dispatch_instant_report_alert_if_needed(
        _FakeAlertDb(
            (
                "Report title",
                "https://example.org/report",
                "RAND Corporation",
                PriorityTierEnum.p0,
            )
        ),
        event_type=event_type,
        title=title,
        message=message,
        report_id=1,
    )

    assert called == [
        (
            title,
            (
                "来源：RAND Corporation\n"
                "报告：Report title\n"
                "链接：https://example.org/report\n"
                "\n"
                f"{message}"
            ),
        )
    ]


@pytest.mark.asyncio
async def test_instant_alerts_skip_non_priority_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[tuple[str, str]] = []

    async def fake_dispatch(*, title: str, message: str) -> None:
        called.append((title, message))

    monkeypatch.setattr(settings, "NOTIFICATION_INSTANT_ALERTS_ENABLED", True)
    monkeypatch.setattr(
        notification_service_module,
        "dispatch_external_notification",
        fake_dispatch,
    )

    await NotificationService().dispatch_instant_report_alert_if_needed(
        _FakeAlertDb(
            (
                "Report title",
                "https://example.org/report",
                "Candidate Source",
                PriorityTierEnum.p4,
            )
        ),
        event_type=NotificationEventType.report_created.value,
        title="发现新的涉华智库报告",
        message="Report title",
        report_id=1,
    )

    assert called == []
