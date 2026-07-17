import asyncio
from typing import Any

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.source import Source, SourceTypeEnum
from app.models.think_tank import OrganizationTypeEnum, ThinkTank

SEED_THINK_TANKS: list[dict[str, Any]] = [
    # =========================
    # 美国重点智库
    # =========================
    {
        "key": "brookings",
        "name": "布鲁金斯学会",
        "name_en": "Brookings Institution",
        "country": "美国",
        "website": "https://www.brookings.edu/",
        "organization_type": OrganizationTypeEnum.think_tank,
        "is_key": True,
        "description": "美国知名公共政策研究机构，重点关注外交、安全、经济、治理和全球发展议题。",
    },
    {
        "key": "heritage",
        "name": "美国传统基金会",
        "name_en": "The Heritage Foundation",
        "country": "美国",
        "website": "https://www.heritage.org/",
        "organization_type": OrganizationTypeEnum.foundation,
        "is_key": True,
        "description": "美国保守主义公共政策研究机构。",
    },
    {
        "key": "cfr",
        "name": "美国外交关系协会",
        "name_en": "Council on Foreign Relations",
        "country": "美国",
        "website": "https://www.cfr.org/",
        "organization_type": OrganizationTypeEnum.think_tank,
        "is_key": True,
        "description": "美国外交政策与国际事务研究机构。",
    },
    {
        "key": "cato",
        "name": "卡托研究所",
        "name_en": "Cato Institute",
        "country": "美国",
        "website": "https://www.cato.org/",
        "organization_type": OrganizationTypeEnum.think_tank,
        "is_key": True,
        "description": "美国自由意志主义公共政策研究机构。",
    },
    {
        "key": "csis",
        "name": "战略与国际问题研究中心",
        "name_en": "Center for Strategic and International Studies",
        "country": "美国",
        "website": "https://www.csis.org/",
        "organization_type": OrganizationTypeEnum.think_tank,
        "is_key": True,
        "description": "美国国际战略、安全与公共政策研究机构。",
    },
    {
        "key": "aei",
        "name": "美国企业研究所",
        "name_en": "American Enterprise Institute",
        "country": "美国",
        "website": "https://www.aei.org/",
        "organization_type": OrganizationTypeEnum.think_tank,
        "is_key": True,
        "description": "美国公共政策、经济和国际事务研究机构。",
    },
    {
        "key": "rand",
        "name": "兰德公司",
        "name_en": "RAND Corporation",
        "country": "美国",
        "website": "https://www.rand.org/",
        "organization_type": OrganizationTypeEnum.think_tank,
        "is_key": True,
        "description": "美国政策研究与战略分析机构。",
    },
    {
        "key": "carnegie",
        "name": "卡内基国际和平基金会",
        "name_en": "Carnegie Endowment for International Peace",
        "country": "美国",
        "website": "https://carnegieendowment.org/",
        "organization_type": OrganizationTypeEnum.think_tank,
        "is_key": True,
        "description": "国际和平、安全、地区政治与全球治理研究机构。",
    },
    {
        "key": "atlantic_council",
        "name": "大西洋理事会",
        "name_en": "Atlantic Council",
        "country": "美国",
        "website": "https://www.atlanticcouncil.org/",
        "organization_type": OrganizationTypeEnum.think_tank,
        "is_key": True,
        "description": "跨大西洋关系、安全、能源、技术和国际经济研究机构。",
    },
    {
        "key": "hoover",
        "name": "胡佛研究所",
        "name_en": "Hoover Institution",
        "country": "美国",
        "website": "https://www.hoover.org/",
        "organization_type": OrganizationTypeEnum.think_tank,
        "is_key": True,
        "description": "斯坦福大学附属公共政策研究机构。",
    },
    {
        "key": "piie",
        "name": "彼得森国际经济研究所",
        "name_en": "Peterson Institute for International Economics",
        "country": "美国",
        "website": "https://www.piie.com/",
        "organization_type": OrganizationTypeEnum.think_tank,
        "is_key": True,
        "description": "国际经济、贸易、金融和宏观经济政策研究机构。",
    },
    {
        "key": "wilson",
        "name": "威尔逊中心",
        "name_en": "Woodrow Wilson International Center for Scholars",
        "country": "美国",
        "website": "https://www.wilsoncenter.org/",
        "organization_type": OrganizationTypeEnum.think_tank,
        "is_key": True,
        "description": "国际关系和公共政策研究机构。",
    },
    {
        "key": "cap",
        "name": "美国进步中心",
        "name_en": "Center for American Progress",
        "country": "美国",
        "website": "https://www.americanprogress.org/",
        "organization_type": OrganizationTypeEnum.think_tank,
        "is_key": True,
        "description": "美国进步主义公共政策研究机构。",
    },
    {
        "key": "nber",
        "name": "美国国家经济研究局",
        "name_en": "National Bureau of Economic Research",
        "country": "美国",
        "website": "https://www.nber.org/",
        "organization_type": OrganizationTypeEnum.research_institute,
        "is_key": True,
        "description": "美国经济研究机构，重点发布工作论文与经济研究成果。",
    },
    # =========================
    # 欧洲重点智库
    # =========================
    {
        "key": "bruegel",
        "name": "布鲁盖尔研究所",
        "name_en": "Bruegel",
        "country": "比利时",
        "website": "https://www.bruegel.org/",
        "organization_type": OrganizationTypeEnum.think_tank,
        "is_key": True,
        "description": "欧洲经济政策、贸易、能源与数字政策研究机构。",
    },
    {
        "key": "chatham_house",
        "name": "英国皇家国际事务研究所",
        "name_en": "Chatham House",
        "country": "英国",
        "website": "https://www.chathamhouse.org/",
        "organization_type": OrganizationTypeEnum.think_tank,
        "is_key": True,
        "description": "英国国际事务和全球治理研究机构。",
    },
    {
        "key": "cepr",
        "name": "经济政策研究中心",
        "name_en": "Centre for Economic Policy Research",
        "country": "英国",
        "website": "https://cepr.org/",
        "organization_type": OrganizationTypeEnum.think_tank,
        "is_key": True,
        "description": "欧洲经济政策研究网络。",
    },
    {
        "key": "ifri",
        "name": "法国国际关系研究所",
        "name_en": "French Institute of International Relations",
        "country": "法国",
        "website": "https://www.ifri.org/",
        "organization_type": OrganizationTypeEnum.think_tank,
        "is_key": True,
        "description": "法国国际关系、安全、欧洲与地区问题研究机构。",
    },
    {
        "key": "swp",
        "name": "德国国际与安全事务研究所",
        "name_en": "German Institute for International and Security Affairs",
        "country": "德国",
        "website": "https://www.swp-berlin.org/",
        "organization_type": OrganizationTypeEnum.think_tank,
        "is_key": True,
        "description": "德国外交与安全政策研究机构。",
    },
    {
        "key": "dgap",
        "name": "德国外交关系委员会",
        "name_en": "German Council on Foreign Relations",
        "country": "德国",
        "website": "https://dgap.org/",
        "organization_type": OrganizationTypeEnum.think_tank,
        "is_key": True,
        "description": "德国外交政策与国际关系研究机构。",
    },
    {
        "key": "ecfr",
        "name": "欧洲对外关系委员会",
        "name_en": "European Council on Foreign Relations",
        "country": "英国",
        "website": "https://ecfr.eu/",
        "organization_type": OrganizationTypeEnum.think_tank,
        "is_key": True,
        "description": "欧洲外交政策与国际战略研究机构。",
    },
    {
        "key": "iiss",
        "name": "国际战略研究所",
        "name_en": "International Institute for Strategic Studies",
        "country": "英国",
        "website": "https://www.iiss.org/",
        "organization_type": OrganizationTypeEnum.think_tank,
        "is_key": True,
        "description": "国际安全、防务与战略研究机构。",
    },
    {
        "key": "sipri",
        "name": "斯德哥尔摩国际和平研究所",
        "name_en": "Stockholm International Peace Research Institute",
        "country": "瑞典",
        "website": "https://www.sipri.org/",
        "organization_type": OrganizationTypeEnum.research_institute,
        "is_key": True,
        "description": "国际和平、安全、军费、军贸和军控研究机构。",
    },
    # =========================
    # 亚洲重点机构
    # =========================
    {
        "key": "jiia",
        "name": "日本国际问题研究所",
        "name_en": "Japan Institute of International Affairs",
        "country": "日本",
        "website": "https://www.jiia.or.jp/",
        "organization_type": OrganizationTypeEnum.think_tank,
        "is_key": True,
        "description": "日本外交、安全与国际关系研究机构。",
    },
    {
        "key": "rieti",
        "name": "日本经济产业研究所",
        "name_en": "Research Institute of Economy, Trade and Industry",
        "country": "日本",
        "website": "https://www.rieti.go.jp/",
        "organization_type": OrganizationTypeEnum.research_institute,
        "is_key": True,
        "description": "日本经济、贸易、产业与创新政策研究机构。",
    },
    {
        "key": "eria",
        "name": "东盟与东亚经济研究所",
        "name_en": "Economic Research Institute for ASEAN and East Asia",
        "country": "印度尼西亚",
        "website": "https://www.eria.org/",
        "organization_type": OrganizationTypeEnum.international_organization,
        "is_key": True,
        "description": "东盟与东亚区域经济、产业和政策研究机构。",
    },
    {
        "key": "kdi",
        "name": "韩国开发研究院",
        "name_en": "Korea Development Institute",
        "country": "韩国",
        "website": "https://www.kdi.re.kr/",
        "organization_type": OrganizationTypeEnum.research_institute,
        "is_key": True,
        "description": "韩国经济与发展政策研究机构。",
    },
    {
        "key": "kiep",
        "name": "韩国对外经济政策研究院",
        "name_en": "Korea Institute for International Economic Policy",
        "country": "韩国",
        "website": "https://www.kiep.go.kr/",
        "organization_type": OrganizationTypeEnum.research_institute,
        "is_key": True,
        "description": "韩国国际经济、贸易和区域政策研究机构。",
    },
    {
        "key": "siis",
        "name": "上海国际问题研究院",
        "name_en": "Shanghai Institutes for International Studies",
        "country": "中国",
        "website": "https://www.siis.org.cn/",
        "organization_type": OrganizationTypeEnum.think_tank,
        "is_key": True,
        "description": "中国国际关系、外交和全球治理研究机构。",
    },
    {
        "key": "cicir",
        "name": "中国现代国际关系研究院",
        "name_en": "China Institutes of Contemporary International Relations",
        "country": "中国",
        "website": "https://www.cicir.ac.cn/",
        "organization_type": OrganizationTypeEnum.research_institute,
        "is_key": True,
        "description": "中国国际战略与国际关系研究机构。",
    },
    # =========================
    # 德国四大学会/联合会
    # =========================
    {
        "key": "leibniz",
        "name": "莱布尼茨学会",
        "name_en": "Leibniz Association",
        "country": "德国",
        "website": "https://www.leibniz-gemeinschaft.de/",
        "organization_type": OrganizationTypeEnum.research_association,
        "is_key": True,
        "description": "德国四大国家级非大学科研机构体系之一，覆盖经济社会科学、自然科学、生命科学、工程与空间科学等领域。",
    },
    {
        "key": "max_planck",
        "name": "马克斯·普朗克学会",
        "name_en": "Max Planck Society",
        "country": "德国",
        "website": "https://www.mpg.de/",
        "organization_type": OrganizationTypeEnum.research_association,
        "is_key": True,
        "description": "德国四大国家级非大学科研机构体系之一，重点从事基础科学研究。",
    },
    {
        "key": "helmholtz",
        "name": "黑姆霍兹联合会",
        "name_en": "Helmholtz Association",
        "country": "德国",
        "website": "https://www.helmholtz.de/",
        "organization_type": OrganizationTypeEnum.research_association,
        "is_key": True,
        "description": "德国四大国家级非大学科研机构体系之一，重点从事大科学工程、能源、环境、健康和航空航天研究。",
    },
    {
        "key": "fraunhofer",
        "name": "弗劳恩霍夫协会",
        "name_en": "Fraunhofer-Gesellschaft",
        "country": "德国",
        "website": "https://www.fraunhofer.de/",
        "organization_type": OrganizationTypeEnum.research_association,
        "is_key": True,
        "description": "德国四大国家级非大学科研机构体系之一，重点从事应用研究、产业创新和技术转移。",
    },
    # =========================
    # 莱布尼茨学会重点研究所
    # =========================
    {
        "key": "ifo",
        "name": "ifo经济研究所",
        "name_en": "ifo Institute",
        "country": "德国",
        "website": "https://www.ifo.de/",
        "organization_type": OrganizationTypeEnum.research_institute,
        "parent_key": "leibniz",
        "is_key": True,
        "description": "德国经济研究机构，重点关注宏观经济、商业景气、财政和产业政策。",
    },
    {
        "key": "ifw_kiel",
        "name": "基尔世界经济研究所",
        "name_en": "Kiel Institute for the World Economy",
        "country": "德国",
        "website": "https://www.ifw-kiel.de/",
        "organization_type": OrganizationTypeEnum.research_institute,
        "parent_key": "leibniz",
        "is_key": True,
        "description": "德国国际经济、贸易、发展 and 全球经济治理研究机构。",
    },
    {
        "key": "diw",
        "name": "德国经济研究所",
        "name_en": "German Institute for Economic Research",
        "country": "德国",
        "website": "https://www.diw.de/",
        "organization_type": OrganizationTypeEnum.research_institute,
        "parent_key": "leibniz",
        "is_key": True,
        "description": "德国经济政策、劳动力 market、能源、气候和社会政策研究机构。",
    },
    {
        "key": "rwi",
        "name": "莱布尼茨经济研究所",
        "name_en": "RWI - Leibniz Institute for Economic Research",
        "country": "德国",
        "website": "https://www.rwi-essen.de/",
        "organization_type": OrganizationTypeEnum.research_institute,
        "parent_key": "leibniz",
        "is_key": True,
        "description": "德国经济研究机构，重点研究能源、健康、教育、劳动力和区域经济。",
    },
    {
        "key": "iwh",
        "name": "哈雷经济研究所",
        "name_en": "Halle Institute for Economic Research",
        "country": "德国",
        "website": "https://www.iwh-halle.de/",
        "organization_type": OrganizationTypeEnum.research_institute,
        "parent_key": "leibniz",
        "is_key": True,
        "description": "德国宏观经济、金融稳定、生产率和结构转型研究机构。",
    },
    {
        "key": "wzb",
        "name": "柏林社会科学研究中心",
        "name_en": "WZB Berlin Social Science Center",
        "country": "德国",
        "website": "https://www.wzb.eu/",
        "organization_type": OrganizationTypeEnum.research_institute,
        "parent_key": "leibniz",
        "is_key": True,
        "description": "德国社会科学研究机构，关注政治、社会不平等、数字化、市场与治理。",
    },
    {
        "key": "giga",
        "name": "德国全球与区域研究中心",
        "name_en": "German Institute for Global and Area Studies",
        "country": "德国",
        "website": "https://www.giga-hamburg.de/",
        "organization_type": OrganizationTypeEnum.research_institute,
        "parent_key": "leibniz",
        "is_key": True,
        "description": "德国全球与区域研究机构，重点研究亚洲、非洲、拉丁美洲、中东和全球治理。",
    },
    {
        "key": "zew",
        "name": "欧洲经济研究中心",
        "name_en": "ZEW - Leibniz Centre for European Economic Research",
        "country": "德国",
        "website": "https://www.zew.de/",
        "organization_type": OrganizationTypeEnum.research_institute,
        "parent_key": "leibniz",
        "is_key": True,
        "description": "研究欧洲经济政策、创新、数字经济和金融市场。",
    },
    # =========================
    # 马克斯·普朗克学会重点研究所
    # =========================
    {
        "key": "mpi_ic",
        "name": "马克斯·普朗克创新与竞争研究所",
        "name_en": "Max Planck Institute for Innovation and Competition",
        "country": "德国",
        "website": "https://www.ip.mpg.de/",
        "organization_type": OrganizationTypeEnum.research_institute,
        "parent_key": "max_planck",
        "is_key": True,
        "description": "重点研究创新、知识产权、竞争、数字经济和监管政策。",
    },
    {
        "key": "mpi_social",
        "name": "马克斯·普朗克社会法与社会政策研究所",
        "name_en": "Max Planck Institute for Social Law and Social Policy",
        "country": "德国",
        "website": "https://www.mpisoc.mpg.de/",
        "organization_type": OrganizationTypeEnum.research_institute,
        "parent_key": "max_planck",
        "is_key": True,
        "description": "重点研究社会法、社会政策、福利制度演变以及国际社会政策比较。",
    },
    # =========================
    # 黑姆霍兹联合会重点研究中心
    # =========================
    {
        "key": "dlr",
        "name": "德国航空航天中心",
        "name_en": "German Aerospace Center",
        "country": "德国",
        "website": "https://www.dlr.de/",
        "organization_type": OrganizationTypeEnum.research_institute,
        "parent_key": "helmholtz",
        "is_key": True,
        "description": "德国国家级航空航天研究机构，重点关注航天、能源、交通与气候治理技术。",
    },
    {
        "key": "fzj",
        "name": "于利希研究中心",
        "name_en": "Forschungszentrum Jülich",
        "country": "德国",
        "website": "https://www.fz-juelich.de/",
        "organization_type": OrganizationTypeEnum.research_institute,
        "parent_key": "helmholtz",
        "is_key": True,
        "description": "重点从事能源转型、气候研究、超级计算、脑科学和信息技术的跨学科研究。",
    },
    # =========================
    # 弗劳恩霍夫协会重点研究所
    # =========================
    {
        "key": "fraunhofer_isi",
        "name": "弗劳恩霍夫系统与创新研究所",
        "name_en": "Fraunhofer Institute for Systems and Innovation Research",
        "country": "德国",
        "website": "https://www.isi.fraunhofer.de/",
        "organization_type": OrganizationTypeEnum.research_institute,
        "parent_key": "fraunhofer",
        "is_key": True,
        "description": "重点研究创新体系、技术政策、能源转型、产业与未来 market。",
    },
    {
        "key": "fraunhofer_imw",
        "name": "弗劳恩霍夫国际管理与知识经济研究所",
        "name_en": "Fraunhofer Center for International Management and Knowledge Economy",
        "country": "德国",
        "website": "https://www.imw.fraunhofer.de/",
        "organization_type": OrganizationTypeEnum.research_institute,
        "parent_key": "fraunhofer",
        "is_key": True,
        "description": "重点研究国际管理、知识经济、数字化转型和区域创新。",
    },
    {
        "key": "fraunhofer_sit",
        "name": "弗劳恩霍夫安全信息技术研究所",
        "name_en": "Fraunhofer Institute for Secure Information Technology",
        "country": "德国",
        "website": "https://www.sit.fraunhofer.de/",
        "organization_type": OrganizationTypeEnum.research_institute,
        "parent_key": "fraunhofer",
        "is_key": True,
        "description": "重点研究网络安全、信息安全、隐私保护和可信数字基础设施。",
    },
    {
        "key": "fraunhofer_iao",
        "name": "弗劳恩霍夫工业工程研究所",
        "name_en": "Fraunhofer Institute for Industrial Engineering",
        "country": "德国",
        "website": "https://www.iao.fraunhofer.de/",
        "organization_type": OrganizationTypeEnum.research_institute,
        "parent_key": "fraunhofer",
        "is_key": True,
        "description": "重点关注人工智能、数字化转型、企业创新与未来工作模式。",
    },
]


async def get_or_create_think_tank(
    db: Any,
    *,
    key: str, # 新增参数
    name: str,
    name_en: str | None,
    country: str,
    website: str | None,
    description: str | None,
    organization_type: OrganizationTypeEnum,
    parent_id: int | None,
    is_key: bool,
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
        think_tank.parent_id = parent_id
        think_tank.is_key = is_key

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
        parent_id=parent_id,
        is_key=is_key,
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

    result = await db.execute(select(Source).where(Source.url == website))
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

            # 调用更新后的 get_or_create，传入 item['key']
            think_tank = await get_or_create_think_tank(
                db=db,
                key=item["key"],
                name=item["name"],
                name_en=item.get("name_en"),
                country=item["country"],
                website=item.get("website"),
                description=item.get("description"),
                organization_type=item["organization_type"],
                parent_id=parent_id,
                is_key=item.get("is_key", False),
            )

            created_or_existing[item["key"]] = think_tank

            await ensure_website_source(
                db=db,
                think_tank=think_tank,
                website=item.get("website"),
            )

            print(f"[OK] {think_tank.id} ({think_tank.key}): " f"{think_tank.name}")

        await db.commit()

    print("机构与官网来源初始化及数据同步完成。")


if __name__ == "__main__":
    asyncio.run(seed_thinktanks())
