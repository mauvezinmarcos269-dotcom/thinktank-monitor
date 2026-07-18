from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    CurrentUserResponse,
    TokenResponse,
)

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="用户登录",
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    使用邮箱和密码登录，并返回 JWT Access Token。

    为避免泄露账号是否存在，邮箱不存在、账号禁用、密码错误
    均返回相同的 401 错误信息。
    """
    # OAuth2 规范强制使用 username 字段，我们将其对应为数据库中的 email
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="邮箱或密码错误。",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if user is None or not user.is_active:
        raise invalid_credentials

    if not verify_password(
        form_data.password,
        user.hashed_password,
    ):
        raise invalid_credentials

    access_token = create_access_token(
        user_id=user.id,
        role=user.role,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
    )


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="获取当前用户",
)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> CurrentUserResponse:
    """返回当前 Bearer Token 对应的有效用户信息。"""
    return CurrentUserResponse.model_validate(current_user)
