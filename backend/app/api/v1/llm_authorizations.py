from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.config import settings
from app.core.llm_authorization import LLMNotAuthorized, LLMScope
from app.db.session import get_db
from app.models.llm_authorization import LLMAuthorization
from app.models.user import RoleEnum, User
from app.schemas.llm_authorization import (
    LLMAuthorizationPreview,
    LLMAuthorizationRead,
    LLMAuthorizationRequest,
)
from app.services.llm_authorization_service import (
    POLICY_VERSION,
    LLMDestination,
    authorization_query,
    authorization_target,
    current_destination,
    revoke_target_authorizations,
)

router = APIRouter()
Admin = Annotated[User, Depends(require_roles(RoleEnum.admin))]
Db = Annotated[AsyncSession, Depends(get_db)]


async def _target(db, scope, target_id, *, lock=False, require_document=True):
    try:
        return await authorization_target(
            db, scope, target_id, lock=lock, require_document=require_document
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except LLMNotAuthorized as exc:
        raise HTTPException(409, str(exc)) from exc


def _destination():
    try:
        return current_destination()
    except LLMNotAuthorized as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/preview", response_model=LLMAuthorizationPreview)
async def preview_authorization(
    scope: LLMScope, target_id: Annotated[int, Query(gt=0)], db: Db, _: Admin
):
    context, target = await _target(db, scope, target_id)
    destination = _destination()
    grant = await db.scalar(authorization_query(context, destination))
    return LLMAuthorizationPreview(
        scope=scope,
        target_id=target_id,
        title=target.title or "",
        document_hash=context.document_hash,
        content_length=(
            len(target.content or "")
            if scope == LLMScope.report_generation
            else target.content_length
        ),
        data_scope=(
            "报告标题、全文翻译/分析分块及派生分析笔记；包括同一版本的重试和最终汇总"
            if scope == LLMScope.report_generation
            else "报告标题及最多12000字符正文抽样；短正文将全部发送；仅限同一来源、URL和文档版本"
        ),
        provider=destination.provider,
        endpoint=destination.endpoint,
        model=destination.model,
        policy_version=POLICY_VERSION,
        outbound_enabled=settings.LLM_OUTBOUND_ENABLED,
        authorized=grant is not None,
    )


@router.get("", response_model=list[LLMAuthorizationRead])
async def authorization_history(
    scope: LLMScope,
    target_id: Annotated[int, Query(gt=0)],
    db: Db,
    _: Admin,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    context, _ = await _target(db, scope, target_id, require_document=False)
    return (
        await db.scalars(
            select(LLMAuthorization)
            .where(
                LLMAuthorization.scope == scope.value,
                LLMAuthorization.target_key == context.target_key,
            )
            .order_by(LLMAuthorization.id.desc())
            .limit(limit)
        )
    ).all()


@router.post("", response_model=LLMAuthorizationRead, status_code=201)
async def grant_authorization(payload: LLMAuthorizationRequest, db: Db, user: Admin):
    context, _ = await _target(db, payload.scope, payload.target_id, lock=True)
    destination = _destination()
    if context.document_hash != payload.document_hash or destination != LLMDestination(
        payload.provider, payload.endpoint, payload.model
    ):
        raise HTTPException(409, "文档版本或 LLM 目标已变化，请重新预览并确认。")
    # Serialize grants on the target and retire earlier grants, keeping an audit trail.
    await revoke_target_authorizations(db, context, user.id)
    grant = LLMAuthorization(
        scope=payload.scope.value,
        target_key=context.target_key,
        document_hash=context.document_hash,
        policy_version=POLICY_VERSION,
        provider=destination.provider,
        endpoint=destination.endpoint,
        model=destination.model,
        candidate_id=payload.target_id if payload.scope == LLMScope.relevance_sample else None,
        report_id=context.report_id,
        granted_by=user.id,
    )
    db.add(grant)
    await db.commit()
    await db.refresh(grant)
    return grant


@router.post("/revoke")
async def revoke_authorization(
    scope: LLMScope, target_id: Annotated[int, Query(gt=0)], db: Db, user: Admin
):
    context, _ = await _target(db, scope, target_id, lock=True, require_document=False)
    count = await revoke_target_authorizations(db, context, user.id)
    await db.commit()
    return {"revoked_count": count}
