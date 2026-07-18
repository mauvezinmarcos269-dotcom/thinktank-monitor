from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import RoleEnum, User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
)


credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="无法验证登录状态，请重新登录。",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    解析 Bearer Token，并查询数据库获取当前有效用户。

    使用方式：
        @router.get("/me")
        async def me(current_user: User = Depends(get_current_user)):
            return current_user
    """
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise credentials_exception

        user = await db.get(User, int(user_id))
    except (ValueError, TypeError):
        raise credentials_exception

    if user is None or not user.is_active:
        raise credentials_exception

    return user


def require_roles(*allowed_roles: RoleEnum) -> Callable:
    """
    创建角色权限依赖。

    使用方式：
        @router.get(
            "/admin-only",
            dependencies=[Depends(require_roles(RoleEnum.admin))],
        )
    """

    async def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="当前账号没有执行此操作的权限。",
            )
        return current_user

    return role_checker
