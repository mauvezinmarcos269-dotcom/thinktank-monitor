from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext

from app.core.config import settings
from app.models.user import RoleEnum

password_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def get_password_hash(password: str) -> str:
    """将明文密码转换为 bcrypt 哈希。"""
    return password_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码是否匹配数据库中的 bcrypt 哈希。"""
    return password_context.verify(plain_password, hashed_password)


def create_access_token(
    *,
    user_id: int,
    role: RoleEnum,
    expires_delta: timedelta | None = None,
) -> str:
    """
    创建 JWT Access Token。

    sub: 用户 ID，JWT 规范中通常使用字符串。
    role: 用户角色，便于前端显示和后端快速获取声明。
    exp: 过期时间。
    """
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role.value,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """验证签名、算法和过期时间后返回 JWT Payload。"""
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except InvalidTokenError as exc:
        raise ValueError("无效或已过期的访问令牌") from exc
