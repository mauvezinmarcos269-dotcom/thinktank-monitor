import hashlib
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.core.llm import SiliconFlowClient
from app.core.llm_authorization import (
    LLMContext,
    LLMNotAuthorized,
    LLMPermit,
    LLMScope,
    candidate_target_key,
    document_hash,
    report_context,
)
from app.models import Base
from app.models.llm_authorization import LLMAuthorization
from app.models.report import Report
from app.models.report_ai_chunk import ReportAIChunk
from app.models.user import RoleEnum, User
from app.services import llm_authorization_service as service
from app.services.ai import report_relevance_service as relevance
from app.services.ai.report_ai_chunk_runner import run_report_ai_chunk
from app.services.ai.report_ai_finalizer_runner import run_report_ai_finalization
from app.utils.datetime import utc_now_naive
from app.workers import report_tasks


class MemoryAsyncDb:
    """Exercise real SQL expressions on SQLite without an async driver or network."""

    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def get(self, model, key, **kwargs):
        return self.session.get(model, key)

    def add(self, obj):
        self.session.add(obj)

    async def scalar(self, statement):
        return self.session.scalar(statement)

    async def scalars(self, statement):
        return self.session.scalars(statement)

    async def execute(self, statement):
        return self.session.execute(statement)

    async def flush(self):
        self.session.flush()

    async def commit(self):
        self.session.commit()

    async def rollback(self):
        self.session.rollback()

    async def stream(self, statement):
        items = self.session.execute(statement).all()

        class Rows:
            async def __aiter__(self):
                for item in items:
                    yield item

            async def close(self):
                pass

        return Rows()


@pytest.fixture
def memory(monkeypatch):
    original_client = httpx.AsyncClient

    def forbidden_http(request):
        raise AssertionError("HTTP was not explicitly mocked")

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original_client(
            transport=httpx.MockTransport(forbidden_http), verify=False, trust_env=False
        ),
    )
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine, expire_on_commit=False)
    user = User(
        id=1,
        email="admin@example.test",
        hashed_password="test-only",
        role=RoleEnum.admin,
        is_active=True,
    )
    report = Report(
        id=1,
        source_id=1,
        title="Title",
        url="https://example.test/report",
        content="Original text",
        crawl_status="success",
        ai_status="pending",
    )
    session.add_all([user, report])
    session.commit()
    db = MemoryAsyncDb(session)
    monkeypatch.setattr(settings, "LLM_OUTBOUND_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_BASE_URL", "https://llm.example.test/chat")
    monkeypatch.setattr(settings, "LLM_MODEL", "test-model")
    monkeypatch.setattr(settings, "LLM_PROVIDER", "test-provider")
    monkeypatch.setattr(settings, "LLM_API_KEY", "not-a-real-key")
    monkeypatch.setattr(service, "AsyncSessionLocal", lambda: db)
    monkeypatch.setattr(relevance, "AsyncSessionLocal", lambda: db)
    yield SimpleNamespace(db=db, session=session, user=user, report=report)
    session.close()
    engine.dispose()


def grant(memory, context=None):
    context = context or report_context(memory.report)
    destination = service.current_destination()
    row = LLMAuthorization(
        scope=context.scope.value,
        target_key=context.target_key,
        document_hash=context.document_hash,
        policy_version=service.POLICY_VERSION,
        provider=destination.provider,
        endpoint=destination.endpoint,
        model=destination.model,
        report_id=context.report_id,
        granted_by=1,
    )
    memory.session.add(row)
    memory.session.commit()
    return row


def mock_post(client, monkeypatch):
    response = httpx.Response(
        200,
        json={"choices": [{"message": {"content": "result"}}]},
        request=httpx.Request("POST", settings.LLM_BASE_URL),
    )
    response.elapsed = timedelta(0)
    post = AsyncMock(return_value=response)
    monkeypatch.setattr(client.client, "post", post)
    return post


def test_setting_defaults_to_disabled():
    assert Settings.model_fields["LLM_OUTBOUND_ENABLED"].default is False


@pytest.mark.asyncio
async def test_direct_client_without_permit_never_posts(memory, monkeypatch):
    async with SiliconFlowClient() as client:
        post = mock_post(client, monkeypatch)
        with pytest.raises(LLMNotAuthorized):
            await client.chat("private text")
        post.assert_not_called()


@pytest.mark.asyncio
async def test_valid_grant_then_revocation_is_checked_before_every_post(memory, monkeypatch):
    row = grant(memory)
    permit = await service.require_authorization(memory.db, report_context(memory.report))
    async with SiliconFlowClient(authorization=permit) as client:
        post = mock_post(client, monkeypatch)
        assert await client.chat("private text") == "result"
        row.revoked_at = utc_now_naive()
        memory.session.commit()
        with pytest.raises(LLMNotAuthorized):
            await client.chat("second request")
        assert post.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change",
    [
        "disabled",
        "title",
        "content",
        "endpoint",
        "model",
        "provider",
        "policy",
        "inactive",
        "role",
        "deleted",
    ],
)
async def test_changed_context_or_config_denies_http(memory, monkeypatch, change):
    row = grant(memory)
    permit = await service.require_authorization(memory.db, report_context(memory.report))
    async with SiliconFlowClient(authorization=permit) as client:
        post = mock_post(client, monkeypatch)
        if change == "disabled":
            monkeypatch.setattr(settings, "LLM_OUTBOUND_ENABLED", False)
        elif change in {"title", "content"}:
            setattr(memory.report, change, "changed but stored content_hash is untouched")
        elif change in {"endpoint", "model", "provider"}:
            field = {"endpoint": "LLM_BASE_URL", "model": "LLM_MODEL", "provider": "LLM_PROVIDER"}[
                change
            ]
            monkeypatch.setattr(
                settings,
                field,
                "https://other.example.test/chat" if change == "endpoint" else "other",
            )
        elif change == "policy":
            row.policy_version = 0
        elif change == "inactive":
            memory.user.is_active = False
        elif change == "role":
            memory.user.role = RoleEnum.teacher
        else:
            memory.session.delete(memory.report)
        memory.session.commit()
        with pytest.raises(LLMNotAuthorized):
            await client.chat("private text")
        post.assert_not_called()


@pytest.mark.asyncio
async def test_regrant_does_not_resurrect_old_permit(memory):
    row = grant(memory)
    context = report_context(memory.report)
    permit = await service.require_authorization(memory.db, context)
    row.revoked_at = utc_now_naive()
    memory.session.commit()
    grant(memory)
    with pytest.raises(LLMNotAuthorized):
        await service.verify_permit(
            permit,
            provider=settings.LLM_PROVIDER,
            endpoint=settings.LLM_BASE_URL,
            model=settings.LLM_MODEL,
        )
    assert (
        await service.require_authorization(memory.db, context)
    ).authorization_id != permit.authorization_id


@pytest.mark.asyncio
@pytest.mark.parametrize("scope", list(LLMScope))
async def test_scope_cannot_be_substituted(memory, scope):
    context = report_context(memory.report)
    other = (
        LLMScope.relevance_sample
        if scope == LLMScope.report_generation
        else LLMScope.report_generation
    )
    grant(memory, LLMContext(scope, context.target_key, context.document_hash))
    with pytest.raises(LLMNotAuthorized):
        await service.require_authorization(
            memory.db, LLMContext(other, context.target_key, context.document_hash)
        )


@pytest.mark.asyncio
async def test_unauthorized_relevance_never_constructs_client(memory, monkeypatch):
    constructed = []
    monkeypatch.setattr(relevance, "SiliconFlowClient", lambda **kwargs: constructed.append(kwargs))
    with pytest.raises(LLMNotAuthorized):
        await relevance.evaluate_china_relevance(
            "Title", "Original text", source_id=2, normalized_url="https://example.test/doc"
        )
    assert constructed == []


@pytest.mark.asyncio
@pytest.mark.parametrize("length", [100, 16000])
async def test_relevance_sends_only_authorized_sample(memory, monkeypatch, length):
    content = "a" * 4000 + "b" * 8000 + "c" * 4000 if length > 12000 else "x" * length
    context = LLMContext(
        LLMScope.relevance_sample,
        candidate_target_key(2, "https://example.test/doc"),
        document_hash("Title", content),
    )
    row = grant(memory, context)
    captures = []

    class FakeClient:
        def __init__(self, *, authorization):
            assert authorization == LLMPermit(row.id, context)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def chat(self, **kwargs):
            captures.append(kwargs["prompt"])
            return '{"relevance":"direct","reason":"sample"}'

    monkeypatch.setattr(relevance, "SiliconFlowClient", FakeClient)
    result = await relevance.evaluate_china_relevance(
        "Title", content, source_id=2, normalized_url="https://example.test/doc"
    )
    assert result["is_china_related"] is True
    assert len(captures) == 1
    assert relevance._sample_report_content(content) in captures[0]
    if length > 12000:
        assert content not in captures[0]
    for changed in [
        (3, "https://example.test/doc", content),
        (2, "https://example.test/other", content),
        (2, "https://example.test/doc", content + "changed"),
    ]:
        with pytest.raises(LLMNotAuthorized):
            await relevance.evaluate_china_relevance(
                "Title", changed[2], source_id=changed[0], normalized_url=changed[1]
            )
    assert len(captures) == 1


@pytest.mark.asyncio
async def test_unapproved_and_stale_reports_do_not_starve_scheduler(memory):
    grant(memory)
    memory.report.content = "changed"
    second = Report(
        id=2,
        source_id=1,
        title="Second",
        url="https://example.test/2",
        content="body",
        crawl_status="success",
        ai_status="pending",
    )
    memory.session.add(second)
    memory.session.commit()
    grant(memory, report_context(second))
    ids = await service.authorized_report_ids(memory.db, [Report.ai_status == "pending"], 1)
    assert ids == [2]


@pytest.mark.asyncio
async def test_scheduler_with_no_grants_does_not_dispatch(memory, monkeypatch):
    monkeypatch.setattr(report_tasks, "AsyncSessionLocal", lambda: memory.db)
    assert await report_tasks._enqueue_ai_chunk_tasks(10, 50) == []
    assert memory.report.ai_status == "pending"


@pytest.mark.asyncio
async def test_authorized_scheduler_enqueues_only_the_approved_report(memory, monkeypatch):
    from app.workers import ai_tasks

    grant(memory)
    unapproved = Report(
        id=2,
        source_id=1,
        title="Unapproved",
        url="https://example.test/2",
        content="body",
        crawl_status="success",
        ai_status="pending",
    )
    memory.session.add(unapproved)
    memory.session.commit()
    monkeypatch.setattr(report_tasks, "AsyncSessionLocal", lambda: memory.db)
    dispatch = Mock()
    monkeypatch.setattr(ai_tasks.ai_chunk_task, "delay", dispatch)
    ids = await report_tasks._enqueue_ai_chunk_tasks(10, 50)
    assert len(ids) == 2
    assert dispatch.call_count == 2
    assert all(memory.session.get(ReportAIChunk, chunk_id).report_id == 1 for chunk_id in ids)
    assert unapproved.ai_status == "pending"
    assert memory.report.ai_status == "processing"


@pytest.mark.asyncio
async def test_disabled_workers_do_not_touch_database_or_dispatch(monkeypatch):
    from app.services.ai import report_ai_chunk_runner, report_ai_finalizer_runner

    def forbidden():
        raise AssertionError("Unexpected database or queue access")

    monkeypatch.setattr(settings, "LLM_OUTBOUND_ENABLED", False)
    for module in (report_tasks, report_ai_chunk_runner, report_ai_finalizer_runner):
        monkeypatch.setattr(module, "AsyncSessionLocal", forbidden)
    assert await report_tasks._enqueue_ai_chunk_tasks(10, 50) == []
    assert (await run_report_ai_chunk(1)).status == "blocked"
    assert (await run_report_ai_finalization(1)).status == "blocked"


@pytest.mark.asyncio
async def test_manual_retry_without_grant_does_not_reset_state_or_queue(memory, monkeypatch):
    from fastapi import HTTPException

    from app.api.v1 import reports

    memory.report.ai_status = "failed"
    memory.report.review_status = "approved"
    get_report = AsyncMock(return_value=memory.report)
    delay = AsyncMock(side_effect=AssertionError("No dispatch permitted"))
    monkeypatch.setattr(reports.report_service, "get_report", get_report)
    monkeypatch.setattr(reports.enqueue_ai_chunk_tasks_task, "delay", delay)
    with pytest.raises(HTTPException) as error:
        await reports.retry_report_ai(1, memory.db, memory.user)
    assert error.value.status_code == 403
    assert memory.report.ai_status == "failed"
    assert memory.report.review_status == "approved"
    delay.assert_not_called()


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://user:password@example.test/chat",
        "https://example.test/chat?key=secret",
        "https://example.test/chat#secret",
        "file:///tmp/model",
    ],
)
def test_preview_destination_rejects_secrets_without_echo(memory, monkeypatch, endpoint):
    monkeypatch.setattr(settings, "LLM_BASE_URL", endpoint)
    with pytest.raises(LLMNotAuthorized) as error:
        service.current_destination()
    assert endpoint not in str(error.value)


def add_chunk(memory, chunk_type="translation", status="queued", index=1):
    chunk = ReportAIChunk(
        report_id=memory.report.id,
        chunk_type=chunk_type,
        chunk_index=index,
        chunk_count=1,
        source_start=0,
        source_end=len(memory.report.content),
        report_content_hash=hashlib.sha256(memory.report.content.encode()).hexdigest(),
        status=status,
        retry_count=1,
        output_text="notes" if status == "success" else None,
    )
    memory.session.add(chunk)
    memory.session.commit()
    return chunk


@pytest.mark.asyncio
async def test_queued_chunk_without_grant_rolls_back_claim(memory, monkeypatch):
    from app.services.ai import report_ai_chunk_runner as runner

    chunk = add_chunk(memory)
    monkeypatch.setattr(runner, "AsyncSessionLocal", lambda: memory.db)
    result = await runner.run_report_ai_chunk(chunk.id)
    assert result.status == "blocked"
    assert chunk.status == "queued"
    assert chunk.retry_count == 1


@pytest.mark.asyncio
async def test_revocation_after_chunk_claim_does_not_consume_retry(memory, monkeypatch):
    from app.services.ai import report_ai_chunk_runner as runner

    chunk = add_chunk(memory)
    row = grant(memory)
    monkeypatch.setattr(runner, "AsyncSessionLocal", lambda: memory.db)

    async def revoke_then_generate(client, execution_input):
        row.revoked_at = utc_now_naive()
        memory.session.commit()
        return await client.chat(execution_input.content)

    monkeypatch.setattr(runner, "generate_report_ai_chunk_output", revoke_then_generate)
    result = await runner.run_report_ai_chunk(chunk.id)
    assert result.status == "blocked"
    assert chunk.status == "pending"
    assert chunk.retry_count == 1


@pytest.mark.asyncio
async def test_finalizer_unapproved_and_revoked_do_not_consume_retry(memory, monkeypatch):
    from app.services.ai import report_ai_finalizer_runner as runner

    add_chunk(memory, "translation", "success")
    add_chunk(memory, "analysis", "success")
    monkeypatch.setattr(runner, "AsyncSessionLocal", lambda: memory.db)
    assert (await runner.run_report_ai_finalization(1)).status == "blocked"
    assert memory.report.ai_retry_count == 0
    row = grant(memory)

    async def revoke_then_generate(client, **kwargs):
        row.revoked_at = utc_now_naive()
        memory.session.commit()
        try:
            await client.chat(kwargs["analysis_notes"])
        except LLMNotAuthorized as exc:
            return runner.FinalReportOutputResult(None, None, (exc,))
        raise AssertionError("Revoked finalizer called HTTP")

    monkeypatch.setattr(runner, "_generate_final_report_outputs", revoke_then_generate)
    result = await runner.run_report_ai_finalization(1)
    assert result.status == "blocked"
    assert memory.report.ai_status == "pending"
    assert memory.report.ai_retry_count == 0


@pytest.mark.asyncio
async def test_finalizer_refuses_old_notes_even_with_new_version_grant(memory, monkeypatch):
    from app.services.ai import report_ai_finalizer_runner as runner

    add_chunk(memory, "translation", "success")
    add_chunk(memory, "analysis", "success")
    memory.report.content = "new body"
    memory.session.commit()
    grant(memory)
    monkeypatch.setattr(runner, "AsyncSessionLocal", lambda: memory.db)
    assert (await runner.run_report_ai_finalization(1)).status == "blocked"
    assert memory.report.ai_retry_count == 0


@pytest.mark.asyncio
async def test_model_probe_respects_disabled_switch(memory, monkeypatch):
    from app.scripts.check_siliconflow_models import check_model

    monkeypatch.setattr(settings, "LLM_OUTBOUND_ENABLED", False)
    with pytest.raises(LLMNotAuthorized):
        await check_model("test-model")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,args",
    [
        ("generate_translation", ("Title", "body")),
        ("generate_analysis_notes", ("Title", "body", 1, 1)),
        ("generate_summary_from_notes", ("Title", "notes")),
        ("generate_commentary_from_notes", ("Title", "notes")),
    ],
)
async def test_authorization_denial_bypasses_all_model_retry_loops(method, args):
    from app.services.ai import report_ai_service

    client = SimpleNamespace(chat=AsyncMock(side_effect=LLMNotAuthorized("revoked")))
    with pytest.raises(LLMNotAuthorized):
        await getattr(report_ai_service, method)(client, *args)
    assert client.chat.await_count == 1
