from dataclasses import dataclass
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.llm_authorization import (
    LLMContext,
    LLMNotAuthorized,
    LLMPermit,
    LLMScope,
    candidate_target_key,
    report_context,
)
from app.db.session import AsyncSessionLocal
from app.models.crawl_candidate import CrawlCandidate
from app.models.llm_authorization import LLMAuthorization
from app.models.report import Report
from app.models.source import Source
from app.models.user import RoleEnum, User
from app.utils.datetime import utc_now_naive

POLICY_VERSION = 1


@dataclass(frozen=True)
class LLMDestination:
    provider: str
    endpoint: str
    model: str


def current_destination() -> LLMDestination:
    endpoint = settings.LLM_BASE_URL.strip()
    parsed = urlsplit(endpoint)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or not settings.LLM_MODEL.strip()
        or not settings.LLM_PROVIDER.strip()
    ):
        raise LLMNotAuthorized("LLM 目标未配置完整，或 URL 含凭据/查询参数；不能授权外发。")
    return LLMDestination(settings.LLM_PROVIDER, endpoint, settings.LLM_MODEL)


def authorization_query(context: LLMContext, destination: LLMDestination):
    return (
        select(LLMAuthorization)
        .join(User, User.id == LLMAuthorization.granted_by)
        .where(
            LLMAuthorization.scope == context.scope.value,
            LLMAuthorization.target_key == context.target_key,
            LLMAuthorization.document_hash == context.document_hash,
            LLMAuthorization.policy_version == POLICY_VERSION,
            LLMAuthorization.provider == destination.provider,
            LLMAuthorization.endpoint == destination.endpoint,
            LLMAuthorization.model == destination.model,
            LLMAuthorization.revoked_at.is_(None),
            User.is_active.is_(True),
            User.role == RoleEnum.admin,
        )
        .order_by(LLMAuthorization.id.desc())
        .limit(1)
    )


async def require_authorization(db: AsyncSession, context: LLMContext) -> LLMPermit:
    if not settings.LLM_OUTBOUND_ENABLED:
        raise LLMNotAuthorized("LLM 外发总开关已关闭。")
    grant = await db.scalar(authorization_query(context, current_destination()))
    if grant is None:
        raise LLMNotAuthorized("缺少匹配当前用途、文档版本和 LLM 目标的有效外发授权。")
    return LLMPermit(grant.id, context)


async def load_report_permit(report_id: int) -> LLMPermit:
    if not settings.LLM_OUTBOUND_ENABLED:
        raise LLMNotAuthorized("LLM 外发总开关已关闭。")
    async with AsyncSessionLocal() as db:
        report = await db.get(Report, report_id)
        if report is None:
            raise LLMNotAuthorized("报告不存在，不能外发。")
        return await require_authorization(db, report_context(report))


async def authorized_report_ids(db: AsyncSession, conditions: list, limit: int) -> list[int]:
    if not settings.LLM_OUTBOUND_ENABLED or limit <= 0:
        return []
    destination = current_destination()
    rows = await db.stream(
        select(Report, LLMAuthorization)
        .join(LLMAuthorization, LLMAuthorization.report_id == Report.id)
        .join(User, User.id == LLMAuthorization.granted_by)
        .where(
            *conditions,
            LLMAuthorization.scope == LLMScope.report_generation.value,
            LLMAuthorization.policy_version == POLICY_VERSION,
            LLMAuthorization.provider == destination.provider,
            LLMAuthorization.endpoint == destination.endpoint,
            LLMAuthorization.model == destination.model,
            LLMAuthorization.revoked_at.is_(None),
            User.is_active.is_(True),
            User.role == RoleEnum.admin,
        )
        .order_by(Report.id)
        .execution_options(yield_per=20)
    )
    ids: list[int] = []
    try:
        async for report, grant in rows:
            if not report.content:
                continue
            context = report_context(report)
            if (
                grant.target_key == context.target_key
                and grant.document_hash == context.document_hash
                and report.id not in ids
            ):
                ids.append(report.id)
                if len(ids) >= limit:
                    break
    finally:
        await rows.close()
    return ids


async def verify_permit(
    permit: LLMPermit | None, *, provider: str, endpoint: str, model: str
) -> None:
    # Never cache this check: a permit can be revoked between chunks or retries.
    if not settings.LLM_OUTBOUND_ENABLED:
        raise LLMNotAuthorized("LLM 外发总开关已关闭。")
    if permit is None:
        raise LLMNotAuthorized("LLM 请求未携带外发授权。")
    destination = current_destination()
    if destination != LLMDestination(provider, endpoint, model):
        raise LLMNotAuthorized("LLM 目标已变化，请重新确认授权。")
    async with AsyncSessionLocal() as db:
        context = permit.context
        if context.scope == LLMScope.report_generation:
            report = await db.get(Report, context.report_id)
            if report is None or report_context(report) != context:
                raise LLMNotAuthorized("报告标题或正文已变化，请重新确认授权。")
        grant = await db.scalar(
            authorization_query(context, destination).where(
                LLMAuthorization.id == permit.authorization_id
            )
        )
        if grant is None:
            raise LLMNotAuthorized("外发授权已撤销、失效或不匹配；请求已阻止。")


async def authorization_target(
    db: AsyncSession,
    scope: LLMScope,
    target_id: int,
    *,
    lock: bool = False,
    require_document: bool = True,
) -> tuple[LLMContext, Report | CrawlCandidate]:
    if scope == LLMScope.report_generation:
        target = await db.get(Report, target_id, with_for_update=lock)
        if target is None:
            raise LookupError("报告不存在")
        if not require_document and not target.content:
            return LLMContext(scope, str(target.id), "", target.id), target
        return report_context(target), target
    target = await db.get(CrawlCandidate, target_id)
    if target is None:
        raise LookupError("候选不存在")
    if lock:
        # Candidate versions in different crawl runs share a source/URL identity.
        await db.get(Source, target.source_id, with_for_update=True)
        await db.refresh(target)
    if require_document and (not target.document_hash or not target.content_length):
        raise LLMNotAuthorized("候选尚无有效文档版本，请先完成文档提取。")
    return (
        LLMContext(
            LLMScope.relevance_sample,
            candidate_target_key(target.source_id, target.normalized_url or target.url),
            target.document_hash or "",
        ),
        target,
    )


async def revoke_target_authorizations(db: AsyncSession, context: LLMContext, actor_id: int) -> int:
    grants = (
        await db.scalars(
            select(LLMAuthorization)
            .where(
                LLMAuthorization.scope == context.scope.value,
                LLMAuthorization.target_key == context.target_key,
                LLMAuthorization.revoked_at.is_(None),
            )
            .with_for_update()
        )
    ).all()
    now = utc_now_naive()
    for grant in grants:
        grant.revoked_at = now
        grant.revoked_by = actor_id
    await db.flush()
    return len(grants)
