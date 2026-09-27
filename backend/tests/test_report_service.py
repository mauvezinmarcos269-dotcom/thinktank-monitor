from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1 import reports as reports_api
from app.core.content_kind import ReportContentKind
from app.core.status import ReportAIStatus, ReportReviewStatus
from app.models.report_review_event import ReportReviewEvent
from app.models.user import RoleEnum
from app.schemas.report import ReportBatchReviewUpdate, ReportUpdate
from app.services import report_service


def test_build_report_filters_includes_review_status() -> None:
    filters = report_service.build_report_filters(
        review_status=ReportReviewStatus.pending_review,
        ai_status=ReportAIStatus.success,
        content_kind=ReportContentKind.web_article,
        deliverable_status="partial",
        keyword="china",
        think_tank_id=5,
        source_id=9,
    )

    assert len(filters) == 7
    compiled = " ".join(
        str(filter_item.compile(compile_kwargs={"literal_binds": True}))
        for filter_item in filters
    )
    assert "review_status" in compiled
    assert "pending_review" in compiled
    assert "ai_status" in compiled
    assert "success" in compiled
    assert "content_kind" in compiled
    assert "web_article" in compiled
    assert "summary" in compiled
    assert "commentary" in compiled
    assert "translation" in compiled
    assert "title" in compiled
    assert "%china%" in compiled
    assert "think_tank_id" in compiled
    assert "source_id" in compiled


def test_build_report_filters_matches_numeric_keyword_as_report_id() -> None:
    filters = report_service.build_report_filters(
        keyword="381",
    )

    assert len(filters) == 1
    compiled = str(
        filters[0].compile(
            compile_kwargs={"literal_binds": True}
        )
    )

    assert "reports.id = 381" in compiled
    assert "%381%" in compiled


@pytest.mark.asyncio
async def test_reports_endpoint_passes_review_status_to_list_and_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_get_reports(
        db: object,
        *,
        skip: int,
        limit: int,
        review_status: ReportReviewStatus | None,
        ai_status: ReportAIStatus | None,
        content_kind: ReportContentKind | None,
        deliverable_status: str | None,
        keyword: str | None,
        think_tank_id: int | None,
        source_id: int | None,
    ) -> list[object]:
        captured["list"] = (
            skip,
            limit,
            review_status,
            ai_status,
            content_kind,
            deliverable_status,
            keyword,
            think_tank_id,
            source_id,
        )
        return []

    async def fake_count_reports(
        db: object,
        *,
        review_status: ReportReviewStatus | None,
        ai_status: ReportAIStatus | None,
        content_kind: ReportContentKind | None,
        deliverable_status: str | None,
        keyword: str | None,
        think_tank_id: int | None,
        source_id: int | None,
    ) -> int:
        captured["count"] = (
            review_status,
            ai_status,
            content_kind,
            deliverable_status,
            keyword,
            think_tank_id,
            source_id,
        )
        return 0

    monkeypatch.setattr(
        reports_api.report_service,
        "get_reports",
        fake_get_reports,
    )
    monkeypatch.setattr(
        reports_api.report_service,
        "count_reports",
        fake_count_reports,
    )

    response = await reports_api.get_reports(
        object(),  # type: ignore[arg-type]
        SimpleNamespace(),  # type: ignore[arg-type]
        skip=20,
        limit=10,
        review_status=ReportReviewStatus.approved,
        ai_status=ReportAIStatus.success,
        content_kind=ReportContentKind.pdf,
        deliverable_status="complete",
        keyword="RAND",
        think_tank_id=5,
        source_id=9,
    )

    assert response.total == 0
    assert captured["list"] == (
        20,
        10,
        ReportReviewStatus.approved,
        ReportAIStatus.success,
        ReportContentKind.pdf,
        "complete",
        "RAND",
        5,
        9,
    )
    assert captured["count"] == (
        ReportReviewStatus.approved,
        ReportAIStatus.success,
        ReportContentKind.pdf,
        "complete",
        "RAND",
        5,
        9,
    )


@pytest.mark.asyncio
async def test_retry_report_ai_resets_review_status_to_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = SimpleNamespace(
        id=12,
        content="report content",
        ai_status=ReportAIStatus.failed.value,
        review_status=ReportReviewStatus.needs_rerun.value,
        updated_at=None,
    )

    class FakeDB:
        def __init__(self) -> None:
            self.added: list[object] = []

        def add(self, obj: object) -> None:
            self.added.append(obj)

        async def commit(self) -> None:
            return None

        async def refresh(self, _: object) -> None:
            return None

    async def fake_get_report(db: object, report_id: int) -> object:
        assert report_id == report.id
        return report

    class FakeTask:
        id = "task-12"

    class FakeQueue:
        @staticmethod
        def delay(*args: object) -> FakeTask:
            assert args == (1, 50, report.id)
            return FakeTask()

    monkeypatch.setattr(
        reports_api.report_service,
        "get_report",
        fake_get_report,
    )
    monkeypatch.setattr(
        reports_api,
        "enqueue_ai_chunk_tasks_task",
        FakeQueue,
    )

    response = await reports_api.retry_report_ai(
        report.id,
        FakeDB(),  # type: ignore[arg-type]
        SimpleNamespace(),  # type: ignore[arg-type]
    )

    assert report.ai_status == ReportAIStatus.pending.value
    assert report.review_status == ReportReviewStatus.pending_review.value
    assert response.ai_status == ReportAIStatus.pending
    assert response.review_status == ReportReviewStatus.pending_review


@pytest.mark.asyncio
async def test_batch_review_endpoint_updates_unique_reports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    updated_reports = [
        SimpleNamespace(
            id=1,
            source_id=1,
            title="Report 1",
            url="https://example.com/1",
        ),
        SimpleNamespace(
            id=2,
            source_id=1,
            title="Report 2",
            url="https://example.com/2",
        ),
    ]
    calls: list[tuple[int, ReportReviewStatus | None, int | None]] = []

    async def fake_update_report(
        db: object,
        report_id: int,
        data: ReportUpdate,
        reviewer_id: int | None = None,
    ) -> object | None:
        calls.append((report_id, data.review_status, reviewer_id))
        return next(
            (report for report in updated_reports if report.id == report_id),
            None,
        )

    monkeypatch.setattr(
        reports_api.report_service,
        "update_report",
        fake_update_report,
    )

    response = await reports_api.batch_update_report_review_status(
        ReportBatchReviewUpdate(
            report_ids=[1, 2, 2, 99],
            review_status=ReportReviewStatus.approved,
        ),
        object(),  # type: ignore[arg-type]
        SimpleNamespace(id=7),  # type: ignore[arg-type]
    )

    assert calls == [
        (1, ReportReviewStatus.approved, 7),
        (2, ReportReviewStatus.approved, 7),
        (99, ReportReviewStatus.approved, 7),
    ]
    assert response.updated_count == 2
    assert [report.id for report in response.items] == [1, 2]
    assert response.not_found_ids == [99]


@pytest.mark.asyncio
async def test_retry_report_ai_preserves_review_status_when_queue_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = SimpleNamespace(
        id=13,
        content="report content",
        ai_status=ReportAIStatus.failed.value,
        review_status=ReportReviewStatus.needs_rerun.value,
        updated_at=None,
    )

    class FakeDB:
        def __init__(self) -> None:
            self.added: list[object] = []

        def add(self, obj: object) -> None:
            self.added.append(obj)

        async def commit(self) -> None:
            return None

        async def refresh(self, _: object) -> None:
            return None

    async def fake_get_report(db: object, report_id: int) -> object:
        assert report_id == report.id
        return report

    class FakeQueue:
        @staticmethod
        def delay(*args: object) -> object:
            raise RuntimeError("queue unavailable")

    monkeypatch.setattr(
        reports_api.report_service,
        "get_report",
        fake_get_report,
    )
    monkeypatch.setattr(
        reports_api,
        "enqueue_ai_chunk_tasks_task",
        FakeQueue,
    )

    with pytest.raises(HTTPException) as exc_info:
        await reports_api.retry_report_ai(
            report.id,
            FakeDB(),  # type: ignore[arg-type]
            SimpleNamespace(),  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 503
    assert report.ai_status == ReportAIStatus.failed.value
    assert report.review_status == ReportReviewStatus.needs_rerun.value


@pytest.mark.asyncio
async def test_update_report_trims_review_note_and_sets_reviewed_at(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = SimpleNamespace(
        id=14,
        title="Sample report",
        review_status=ReportReviewStatus.pending_review.value,
        review_note=None,
        reviewed_at=None,
    )

    class FakeDB:
        def __init__(self) -> None:
            self.added: list[object] = []

        def add(self, obj: object) -> None:
            self.added.append(obj)

        async def commit(self) -> None:
            return None

        async def refresh(self, _: object) -> None:
            return None

    async def fake_get_report(db: object, report_id: int) -> object:
        assert report_id == report.id
        return report

    notification_calls: list[dict[str, object]] = []

    async def fake_create_for_roles(db: object, **kwargs: object) -> list[object]:
        notification_calls.append(kwargs)
        return []

    monkeypatch.setattr(report_service, "get_report", fake_get_report)
    monkeypatch.setattr(
        report_service.notification_service,
        "create_for_roles",
        fake_create_for_roles,
    )

    db = FakeDB()

    updated = await report_service.update_report(
        db,  # type: ignore[arg-type]
        report.id,
        ReportUpdate(
            review_status=ReportReviewStatus.needs_rerun,
            review_note="  翻译部分需要重新生成。  ",
        ),
        reviewer_id=7,
    )

    assert updated is report
    assert report.review_status == ReportReviewStatus.needs_rerun
    assert report.review_note == "翻译部分需要重新生成。"
    assert report.reviewed_at is not None
    assert len(db.added) == 1
    assert isinstance(db.added[0], ReportReviewEvent)
    assert db.added[0].report_id == report.id
    assert db.added[0].review_note == "翻译部分需要重新生成。"
    assert db.added[0].reviewer_id == 7
    assert notification_calls == [
        {
            "roles": {RoleEnum.admin},
            "event_type": "report.review_needs_rerun",
            "title": "报告需重跑",
            "message": "Sample report\n\n复核意见：翻译部分需要重新生成。",
            "report_id": report.id,
        }
    ]


@pytest.mark.asyncio
async def test_review_events_endpoint_returns_report_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = [
        SimpleNamespace(
            id=1,
            report_id=15,
            review_status=ReportReviewStatus.needs_rerun.value,
            review_note="需要重跑全文翻译。",
            reviewer_id=7,
            reviewer=SimpleNamespace(email="teacher@example.com"),
            created_at=datetime(2026, 9, 16, 1, 2, 3),
        )
    ]
    captured: dict[str, object] = {}

    async def fake_get_report_review_events(
        db: object,
        report_id: int,
    ) -> list[object]:
        captured["report_id"] = report_id
        return events

    monkeypatch.setattr(
        reports_api.report_service,
        "get_report_review_events",
        fake_get_report_review_events,
    )

    response = await reports_api.get_report_review_events(
        15,
        object(),  # type: ignore[arg-type]
        SimpleNamespace(),  # type: ignore[arg-type]
    )

    assert len(response) == 1
    assert captured["report_id"] == 15
    assert response[0].reviewer_id == 7
    assert response[0].reviewer_email == "teacher@example.com"
