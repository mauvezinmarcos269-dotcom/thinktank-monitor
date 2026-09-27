import asyncio
from typing import Any

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.source import Source, SourceTypeEnum
from app.models.think_tank import (
    OrganizationTypeEnum,
    PriorityTierEnum,
    RegionFocusEnum,
    ThinkTank,
)
from app.scripts.seed_thinktank_data import SEED_THINK_TANKS
from app.scripts.source_governance import derive_source_governance


async def get_or_create_think_tank(
    db: Any,
    *,
    key: str,
    name: str,
    name_en: str | None,
    country: str,
    website: str | None,
    description: str | None,
    organization_type: OrganizationTypeEnum,
    priority_tier: PriorityTierEnum,
    region_focus: RegionFocusEnum,
    parent_id: int | None,
    is_key: bool,
    is_verified: bool,
) -> ThinkTank:
    result = await db.execute(select(ThinkTank).where(ThinkTank.key == key))
    think_tank = result.scalar_one_or_none()

    # 如果机构已存在，同步更新所有属性
    if think_tank is not None:
        think_tank.name = name
        think_tank.name_en = name_en
        think_tank.country = country
        think_tank.website = website
        think_tank.description = description
        think_tank.organization_type = organization_type
        think_tank.priority_tier = priority_tier
        think_tank.region_focus = region_focus
        think_tank.parent_id = parent_id
        think_tank.is_key = is_key
        think_tank.is_verified = is_verified

        await db.flush()
        return think_tank

    # 如果机构不存在，创建时显式指定 key
    think_tank = ThinkTank(
        key=key,
        name=name,
        name_en=name_en,
        country=country,
        website=website,
        description=description,
        organization_type=organization_type,
        priority_tier=priority_tier,
        region_focus=region_focus,
        parent_id=parent_id,
        is_key=is_key,
        is_verified=is_verified,
        is_active=True,
    )

    db.add(think_tank)
    await db.flush()

    return think_tank


async def ensure_website_source(
    db: Any,
    *,
    think_tank: ThinkTank,
    website: str | None,
) -> None:
    if not website:
        return

    # Source.url 在数据库中是全局唯一约束；同一个入口不重复挂到多个机构。
    result = await db.execute(
        select(Source).where(
            Source.url == website,
        )
    )
    source = result.scalar_one_or_none()

    if source is not None:
        return

    source = Source(
        think_tank_id=think_tank.id,
        source_type=SourceTypeEnum.website,
        url=website,
        crawl_frequency_minutes=1440,
        is_active=True,
    )

    db.add(source)


async def ensure_rss_source(
    db: Any,
    *,
    think_tank: ThinkTank,
    rss_url: str | None,
) -> None:
    if not rss_url:
        return

    # Source.url 在数据库中是全局唯一约束；同一个订阅源只保留一个归属。
    result = await db.execute(
        select(Source).where(
            Source.url == rss_url,
        )
    )
    source = result.scalar_one_or_none()

    if source is not None:
        return

    source = Source(
        think_tank_id=think_tank.id,
        source_type=SourceTypeEnum.rss,
        url=rss_url,
        crawl_frequency_minutes=1440,
        is_active=True,
    )

    db.add(source)


async def seed_thinktanks() -> None:
    created_or_existing: dict[str, ThinkTank] = {}

    print("开始初始化与同步机构数据...")

    async with AsyncSessionLocal() as db:
        for item in SEED_THINK_TANKS:
            parent_id: int | None = None
            parent_key = item.get("parent_key")

            if parent_key:
                parent = created_or_existing.get(parent_key)

                if parent is None:
                    raise RuntimeError(f"无法找到上级机构：{parent_key}")

                parent_id = parent.id

            priority_tier, region_focus, is_verified = derive_source_governance(
                item
            )

            think_tank = await get_or_create_think_tank(
                db=db,
                key=item["key"],
                name=item["name"],
                name_en=item.get("name_en"),
                country=item["country"],
                website=item.get("website"),
                description=item.get("description"),
                organization_type=item["organization_type"],
                priority_tier=priority_tier,
                region_focus=region_focus,
                parent_id=parent_id,
                is_key=item.get("is_key", False),
                is_verified=is_verified,
            )

            created_or_existing[item["key"]] = think_tank

            await ensure_website_source(
                db=db,
                think_tank=think_tank,
                website=item.get("website"),
            )

            await ensure_rss_source(
                db=db,
                think_tank=think_tank,
                rss_url=item.get("rss"),
            )

            print(f"[OK] {think_tank.id} ({think_tank.key}): {think_tank.name}")

        await db.commit()

    print("机构与官网来源初始化及数据同步完成。")


if __name__ == "__main__":
    asyncio.run(seed_thinktanks())
