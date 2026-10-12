"""Exercise the real authorization router and service against in-memory SQLite."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from celery import Celery, Task
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from starlette.background import BackgroundTask

from app.api.deps import get_current_user
from app.api.v1 import llm_authorizations as authorization_api
from app.core.config import settings
from app.core.llm import SiliconFlowClient
from app.core.llm_authorization import (
    LLMContext,
    LLMNotAuthorized,
    LLMScope,
    candidate_target_key,
    document_hash,
)
from app.db import session as database
from app.models.base import Base
from app.models.crawl_candidate import CrawlCandidate
from app.models.crawl_run import CrawlRun
from app.models.llm_authorization import LLMAuthorization
from app.models.report import Report
from app.models.source import Source, SourceTypeEnum
from app.models.think_tank import ThinkTank
from app.models.user import RoleEnum, User
from app.services import crawler_service
from app.services import llm_authorization_service as authorization_service

API = "/api/v1/llm-authorizations"
CONSENT = "allow_external_processing"
DESTINATION = {
    "provider": "test_provider",
    "endpoint": "https://llm.example.invalid/v1/chat/completions",
    "model": "test-model",
}


@pytest.fixture
def isolated_side_effects(monkeypatch):
    """Fail on attempted side effects even if application code catches the error."""
    guards = []
    for owner, name, asynchronous in (
        (database.engine.sync_engine.dialect, "connect", False),
        (database, "AsyncSessionLocal", False),
        (authorization_service, "AsyncSessionLocal", False),
        (httpx.HTTPTransport, "handle_request", False),
        (httpx.AsyncHTTPTransport, "handle_async_request", True),
        (SiliconFlowClient, "__init__", False),
        (SiliconFlowClient, "chat", True),
        (Task, "delay", False),
        (Task, "apply_async", False),
        (Task, "apply", False),
        (Celery, "send_task", False),
        (BackgroundTask, "__call__", True),
        (crawler_service, "crawl_source", False),
        (crawler_service, "crawl_all_sources", False),
        (crawler_service, "_crawl_source_async", True),
        (crawler_service, "_crawl_all_sources_async", True),
        (crawler_service, "fetch_report_document", True),
    ):
        factory = AsyncMock if asynchronous else Mock
        guard = factory(name=name, side_effect=AssertionError(f"Forbidden side effect: {name}"))
        monkeypatch.setattr(owner, name, guard)
        guards.append(guard)
    yield
    for guard in guards:
        guard.assert_not_called()


@pytest.fixture
def harness(monkeypatch, isolated_side_effects):
    for key, value in {
        "LLM_PROVIDER": DESTINATION["provider"],
        "LLM_BASE_URL": DESTINATION["endpoint"],
        "LLM_MODEL": DESTINATION["model"],
        "LLM_OUTBOUND_ENABLED": True,
    }.items():
        monkeypatch.setattr(settings, key, value)

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    try:
        with Session(engine, expire_on_commit=False, autoflush=False) as session:
            admin = User(id=7, email="admin@example.invalid", hashed_password="unused", role=RoleEnum.admin)
            teacher = User(id=8, email="teacher@example.invalid", hashed_password="unused", role=RoleEnum.teacher)
            session.add_all([
                admin,
                teacher,
                ThinkTank(id=1, key="test", name="Test institute", country="Test"),
            ])
            session.flush()
            source = Source(id=11, think_tank_id=1, source_type=SourceTypeEnum.website, url="https://source.example.invalid")
            session.add(source)
            session.flush()
            run = CrawlRun(id=21, source_id=source.id, status="success")
            report = Report(
                id=31,
                source_id=source.id,
                title="Test report",
                url="https://source.example.invalid/report",
                content="Content requiring explicit permission for external processing.",
                ai_status="pending",
            )
            session.add_all([run, report])
            session.flush()
            candidate = CrawlCandidate(
                id=41,
                crawl_run_id=run.id,
                source_id=source.id,
                report_id=report.id,
                title=report.title,
                url=report.url + "?tracking=test",
                normalized_url=report.url,
                document_hash=document_hash(report.title, report.content),
                content_length=len(report.content),
                status="pending_relevance",
            )
            session.add(candidate)
            session.commit()

            # Only the async I/O boundary is adapted; ORM queries remain real SQL.
            db = SimpleNamespace(
                add=Mock(side_effect=session.add),
                **{
                    name: AsyncMock(side_effect=getattr(session, name))
                    for name in ("get", "scalar", "scalars", "execute", "flush", "commit", "refresh", "delete", "rollback")
                },
            )
            state = SimpleNamespace(
                session=session, db=db, admin=admin, teacher=teacher, user=admin,
                report=report, candidate=candidate, source=source, run=run,
            )

            async def override_db():
                yield db

            async def override_user():
                return state.user

            # Mount only this router: application startup and workers must not run.
            app = FastAPI()
            app.include_router(authorization_api.router, prefix=API)
            app.dependency_overrides[authorization_api.get_db] = override_db
            app.dependency_overrides[get_current_user] = override_user
            with TestClient(app) as client:
                state.client = client
                state.app = app
                yield state
    finally:
        engine.dispose()


@pytest.fixture(params=list(LLMScope), ids=lambda scope: scope.value)
def target(request, harness):
    scope = request.param
    obj = harness.report if scope == LLMScope.report_generation else harness.candidate
    return SimpleNamespace(
        obj=obj,
        scope=scope,
        params={"scope": scope.value, "target_id": obj.id},
        context=LLMContext(
            scope=scope,
            target_key=(
                str(obj.id) if scope == LLMScope.report_generation
                else candidate_target_key(obj.source_id, obj.normalized_url or obj.url)
            ),
            document_hash=(
                document_hash(obj.title, obj.content)
                if scope == LLMScope.report_generation else obj.document_hash
            ),
            report_id=obj.id if scope == LLMScope.report_generation else None,
        ),
    )


def preview(harness, target):
    response = harness.client.get(f"{API}/preview", params=target.params)
    assert response.status_code == 200, response.text
    return response.json()


def grant_payload(harness, target):
    data = preview(harness, target)
    return {
        key: data[key]
        for key in ("scope", "target_id", "document_hash", "provider", "endpoint", "model", "policy_version")
    } | {"consent": CONSENT}


def grant(harness, target):
    response = harness.client.post(API, json=grant_payload(harness, target))
    assert response.status_code == 201, response.text
    return response.json()


def seed_grant(harness, target, **overrides):
    data = {
        "scope": target.scope.value,
        "target_key": target.context.target_key,
        "document_hash": target.context.document_hash,
        "policy_version": authorization_service.POLICY_VERSION,
        **DESTINATION,
        "candidate_id": target.obj.id if target.scope == LLMScope.relevance_sample else None,
        "report_id": target.context.report_id,
        "granted_by": harness.admin.id,
    }
    authorization = LLMAuthorization(**(data | overrides))
    harness.session.add(authorization)
    harness.session.commit()
    return authorization


def snapshot(harness, *, include_grants=True):
    return {
        table.name: harness.session.execute(select(table).order_by(*table.primary_key.columns)).all()
        for table in Base.metadata.sorted_tables
        if include_grants or table.name != LLMAuthorization.__tablename__
    }


def assert_no_mutations(harness):
    for name in ("add", "delete", "flush", "commit", "rollback"):
        getattr(harness.db, name).assert_not_called()


@pytest.mark.parametrize("already_authorized", [False, True])
def test_admin_preview_is_read_only_and_starts_no_work(harness, target, already_authorized):
    if already_authorized:
        seed_grant(harness, target)
    before = snapshot(harness)

    data = preview(harness, target)

    assert data == {
        **target.params,
        "title": target.obj.title,
        "document_hash": target.context.document_hash,
        "content_length": len(harness.report.content),
        "data_scope": data["data_scope"],
        **DESTINATION,
        "policy_version": 1,
        "outbound_enabled": True,
        "authorized": already_authorized,
    }
    assert data["data_scope"]
    assert "content" not in data
    assert snapshot(harness) == before
    assert_no_mutations(harness)


@pytest.mark.parametrize("consent", [None, False, True, "", "yes", "ALLOW_EXTERNAL_PROCESSING"])
def test_post_requires_explicit_consent(harness, target, consent):
    payload = grant_payload(harness, target)
    payload["consent"] = consent
    before = snapshot(harness)

    response = harness.client.post(API, json=payload)

    assert response.status_code == 422
    assert any(error["loc"] == ["body", "consent"] for error in response.json()["detail"])
    assert snapshot(harness) == before
    assert_no_mutations(harness)


def test_post_rejects_missing_consent(harness, target):
    payload = grant_payload(harness, target)
    del payload["consent"]

    response = harness.client.post(API, json=payload)

    assert response.status_code == 422
    assert any(error["loc"] == ["body", "consent"] for error in response.json()["detail"])
    assert harness.session.scalars(select(LLMAuthorization)).all() == []
    assert_no_mutations(harness)


@pytest.mark.parametrize("field,value", [
    ("document_hash", "0" * 64),
    ("provider", "other_provider"),
    ("endpoint", "https://other.example.invalid/v1/chat/completions"),
    ("model", "other-model"),
])
def test_post_rejects_mismatched_preview_without_retiring_existing_grant(harness, target, field, value):
    seed_grant(harness, target)
    payload = grant_payload(harness, target)
    payload[field] = value
    before = snapshot(harness)

    response = harness.client.post(API, json=payload)

    assert response.status_code == 409
    assert snapshot(harness) == before
    assert_no_mutations(harness)


@pytest.mark.parametrize("field,value", [
    ("policy_version", 2),
    ("document_hash", "not-a-sha256"),
    ("target_id", 0),
    ("scope", "all"),
    ("enqueue", True),
])
def test_post_validates_policy_and_rejects_extra_fields(harness, target, field, value):
    payload = grant_payload(harness, target) | {field: value}

    response = harness.client.post(API, json=payload)

    assert response.status_code == 422
    assert any(error["loc"] == ["body", field] for error in response.json()["detail"])
    assert_no_mutations(harness)


def test_document_change_between_preview_and_post_requires_new_consent(harness, target):
    existing = seed_grant(harness, target)
    payload = grant_payload(harness, target)
    if target.scope == LLMScope.report_generation:
        target.obj.content += " Revised after preview."
    else:
        target.obj.document_hash = "a" * 64
    harness.session.commit()
    before = snapshot(harness)

    response = harness.client.post(API, json=payload)

    assert response.status_code == 409
    assert preview(harness, target)["authorized"] is False
    assert existing.revoked_at is None
    assert snapshot(harness) == before
    assert_no_mutations(harness)


@pytest.mark.parametrize("setting,value", [
    ("LLM_PROVIDER", "changed-provider"),
    ("LLM_BASE_URL", "https://changed.example.invalid/v1/chat/completions"),
    ("LLM_MODEL", "changed-model"),
])
def test_destination_change_between_preview_and_post_is_rejected(harness, target, monkeypatch, setting, value):
    seed_grant(harness, target)
    payload = grant_payload(harness, target)
    before = snapshot(harness)
    monkeypatch.setattr(settings, setting, value)

    response = harness.client.post(API, json=payload)

    assert response.status_code == 409
    assert preview(harness, target)["authorized"] is False
    assert snapshot(harness) == before
    assert_no_mutations(harness)


@pytest.mark.asyncio
async def test_grant_persists_consent_without_enqueuing_or_changing_work(harness, target):
    before = snapshot(harness, include_grants=False)

    data = grant(harness, target)

    assert data["scope"] == target.scope.value
    assert data["target_key"] == target.context.target_key
    assert data["document_hash"] == target.context.document_hash
    assert {key: data[key] for key in DESTINATION} == DESTINATION
    assert data["granted_by"] == harness.admin.id
    assert data["granted_at"]
    assert data["revoked_by"] is None
    assert data["revoked_at"] is None
    assert data["candidate_id"] == (target.obj.id if target.scope == LLMScope.relevance_sample else None)
    assert data["report_id"] == target.context.report_id
    assert len(harness.session.scalars(select(LLMAuthorization)).all()) == 1
    permit = await authorization_service.require_authorization(harness.db, target.context)
    assert permit.authorization_id == data["id"]
    assert permit.context == target.context
    assert preview(harness, target)["authorized"] is True
    assert snapshot(harness, include_grants=False) == before


@pytest.mark.parametrize("method,path", [
    ("GET", "/preview"), ("GET", ""), ("POST", ""), ("POST", "/revoke"),
])
def test_teacher_cannot_preview_list_grant_or_revoke(harness, target, method, path):
    seed_grant(harness, target)
    payload = grant_payload(harness, target)
    before = snapshot(harness)
    harness.user = harness.teacher
    harness.db.get.reset_mock()
    harness.db.scalar.reset_mock()
    harness.db.scalars.reset_mock()

    kwargs = {"json": payload} if method == "POST" and path == "" else {"params": target.params}
    response = harness.client.request(method, API + path, **kwargs)

    assert response.status_code == 403
    assert snapshot(harness) == before
    for name in ("get", "scalar", "scalars"):
        getattr(harness.db, name).assert_not_called()
    assert_no_mutations(harness)


@pytest.mark.asyncio
async def test_revoke_retires_all_versions_is_idempotent_and_preserves_other_grants(harness, target):
    active = [
        seed_grant(harness, target),
        seed_grant(harness, target),
        seed_grant(harness, target, document_hash="b" * 64),
        seed_grant(harness, target, endpoint="https://old.example.invalid", model="old-model"),
        seed_grant(harness, target, policy_version=0),
    ]
    original_time = datetime(2025, 1, 1)
    already_revoked = seed_grant(harness, target, revoked_at=original_time, revoked_by=harness.teacher.id)
    other_target = seed_grant(harness, target, target_key="another-target")
    other_scope = seed_grant(
        harness, target,
        scope=(LLMScope.relevance_sample if target.scope == LLMScope.report_generation else LLMScope.report_generation).value,
    )
    before = snapshot(harness, include_grants=False)

    response = harness.client.post(f"{API}/revoke", params=target.params)

    assert response.status_code == 200
    assert response.json() == {"revoked_count": len(active)}
    for authorization in active:
        harness.session.refresh(authorization)
        assert authorization.revoked_at is not None
        assert authorization.revoked_by == harness.admin.id
    assert len({authorization.revoked_at for authorization in active}) == 1
    harness.session.refresh(already_revoked)
    assert already_revoked.revoked_at == original_time
    assert already_revoked.revoked_by == harness.teacher.id
    for authorization in (other_target, other_scope):
        harness.session.refresh(authorization)
        assert authorization.revoked_at is None
    after_first_revoke = snapshot(harness)

    repeated = harness.client.post(f"{API}/revoke", params=target.params)

    assert repeated.status_code == 200
    assert repeated.json() == {"revoked_count": 0}
    assert snapshot(harness) == after_first_revoke
    assert snapshot(harness, include_grants=False) == before
    assert preview(harness, target)["authorized"] is False
    with pytest.raises(LLMNotAuthorized):
        await authorization_service.require_authorization(harness.db, target.context)


def test_regrant_keeps_history_and_only_latest_grant_active(harness, target):
    first = grant(harness, target)
    second = grant(harness, target)

    response = harness.client.get(API, params=target.params)

    assert response.status_code == 200
    history = response.json()
    assert [item["id"] for item in history] == [second["id"], first["id"]]
    assert history[0]["revoked_at"] is None
    assert history[1]["revoked_at"] is not None
    assert history[1]["revoked_by"] == harness.admin.id
    assert preview(harness, target)["authorized"] is True


@pytest.mark.asyncio
async def test_identical_target_and_document_in_other_scope_do_not_authorize(harness, target):
    other_scope = LLMScope.relevance_sample if target.scope == LLMScope.report_generation else LLMScope.report_generation
    other = seed_grant(harness, target, scope=other_scope.value)

    assert preview(harness, target)["authorized"] is False
    history = harness.client.get(API, params=target.params)
    assert history.status_code == 200
    assert history.json() == []
    with pytest.raises(LLMNotAuthorized):
        await authorization_service.require_authorization(harness.db, target.context)

    own = grant(harness, target)

    harness.session.refresh(other)
    assert other.revoked_at is None
    permit = await authorization_service.require_authorization(harness.db, target.context)
    assert permit.authorization_id == own["id"]


def test_preview_and_post_reject_missing_document_but_history_and_revoke_work(harness, target):
    payload = grant_payload(harness, target)
    existing = seed_grant(harness, target)
    if target.scope == LLMScope.report_generation:
        target.obj.content = None
    else:
        target.obj.document_hash = None
        target.obj.content_length = None
    harness.session.commit()

    assert harness.client.get(f"{API}/preview", params=target.params).status_code == 409
    assert harness.client.post(API, json=payload).status_code == 409
    history = harness.client.get(API, params=target.params)
    assert history.status_code == 200
    assert [item["id"] for item in history.json()] == [existing.id]
    response = harness.client.post(f"{API}/revoke", params=target.params)
    assert response.status_code == 200
    assert response.json() == {"revoked_count": 1}


@pytest.mark.asyncio
async def test_outbound_switch_blocks_use_even_when_grant_exists(harness, target, monkeypatch):
    seed_grant(harness, target)
    monkeypatch.setattr(settings, "LLM_OUTBOUND_ENABLED", False)
    before = snapshot(harness)

    data = preview(harness, target)

    assert data["outbound_enabled"] is False
    assert data["authorized"] is True
    with pytest.raises(LLMNotAuthorized):
        await authorization_service.require_authorization(harness.db, target.context)
    assert snapshot(harness) == before
    assert_no_mutations(harness)
