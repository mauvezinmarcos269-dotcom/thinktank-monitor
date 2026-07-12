#!/usr/bin/env python
import asyncio
from getpass import getpass

from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.user import RoleEnum, User


async def create_superuser():
    print("=" * 50)
    print("创建超级用户")
    print("=" * 50)
    
    email = input("请输入邮箱: ").strip()
    if not email:
        print("邮箱不能为空")
        return
    
    password = getpass("请输入密码: ")
    if not password:
        print("密码不能为空")
        return
    
    confirm = getpass("请再次输入密码: ")
    if password != confirm:
        print("两次密码输入不一致")
        return
    
    if len(password) < 8:
        print("密码长度至少 8 位")
        return
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"用户 {email} 已存在")
            return
        
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            role=RoleEnum.admin,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        print(f"超级用户创建成功！")
        print(f"ID: {user.id}")
        print(f"邮箱: {user.email}")
        print(f"角色: {user.role}")


if __name__ == "__main__":
    import asyncio
    import selectors
    import sys

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(create_superuser())