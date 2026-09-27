from datetime import datetime
from urllib.parse import urlsplit
from xml.etree import ElementTree

from app.models import Source
from app.models.source import SourceTypeEnum
from app.services.crawler.brookings_parser import parse_brookings_reports
from app.services.crawler.cap_parser import parse_cap_reports
from app.services.crawler.chatham_house_parser import parse_chatham_house_reports
from app.services.crawler.content_extractor import extract_report_pdf_url
from app.services.crawler.csis_analysis_parser import parse_csis_reports
from app.services.crawler.ecfr_parser import parse_ecfr_reports
from app.services.crawler.http_client import fetch_html, fetch_resource
from app.services.crawler.nber_parser import parse_nber_working_papers
from app.services.crawler.report_candidate_filter import has_china_signal
from app.services.crawler.rss_parser import parse_rss_articles
from app.services.crawler.us_core_parser import (
    CORE_SITE_CONFIGS,
    CoreSiteConfig,
    parse_core_site_reports,
)

BROOKINGS_DISCOVERY_URLS = (
    "https://www.brookings.edu/",
    "https://www.brookings.edu/regions/asia-the-pacific/china/",
)
CAP_DISCOVERY_URLS = (
    "https://www.americanprogress.org/",
    "https://www.americanprogress.org/topic/china/",
    "https://www.americanprogress.org/topic/foreign-policy-and-security/",
)
CSIS_DISCOVERY_URLS = (
    "https://www.csis.org/",
    "https://www.csis.org/analysis",
    "https://www.csis.org/analysis?f%5B0%5D=content_type%3Areport",
    "https://www.csis.org/regions/asia/china",
    "https://www.csis.org/programs/china-power-project",
)
CSIS_SITEMAP_URL = "https://www.csis.org/sitemap.xml"
CSIS_SITEMAP_MAX_PAGE_FETCHES = 20
NBER_DISCOVERY_URLS = (
    "https://www.nber.org/api/v1/search?q=China",
)
CHATHAM_HOUSE_DISCOVERY_URLS = (
    "https://www.chathamhouse.org/",
    "https://www.chathamhouse.org/publications",
    "https://www.chathamhouse.org/research/regions/asia-pacific/china",
)
ECFR_DISCOVERY_URLS = (
    "https://ecfr.eu/topic/china/",
    "https://ecfr.eu/category/china/",
    "https://ecfr.eu/publications/",
    "https://ecfr.eu/",
)

DISCOVERY_FETCH_TIMEOUT_SECONDS = 20.0

CORE_US_SITE_CONFIG_BY_HOST: dict[str, CoreSiteConfig] = {
    host: config
    for config in CORE_SITE_CONFIGS.values()
    for host in config.hosts
}


async def _fetch_discovery_resource(
    discovery_url: str,
    discovery_errors: list[str],
):
    try:
        return await fetch_resource(
            discovery_url,
            timeout_seconds=DISCOVERY_FETCH_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        discovery_errors.append(
            f"{discovery_url} ({type(exc).__name__}: {exc})"
        )
        return None


def _raise_if_all_discovery_urls_failed(
    *,
    successful_fetch_count: int,
    discovery_errors: list[str],
) -> None:
    if successful_fetch_count > 0 or not discovery_errors:
        return

    raise ValueError(
        "所有发现入口抓取失败："
        + "; ".join(discovery_errors)
    )


async def _fetch_multi_entry_website_articles(
    *,
    discovery_urls: tuple[str, ...],
    parser,
) -> list[dict[str, object]]:
    articles_by_url: dict[str, dict[str, object]] = {}
    discovery_errors: list[str] = []
    successful_fetch_count = 0

    for discovery_url in discovery_urls:
        resource = await _fetch_discovery_resource(
            discovery_url,
            discovery_errors,
        )
        if resource is None:
            continue

        successful_fetch_count += 1

        for article in parser(
            resource.content,
            resource.final_url,
        ):
            url = str(article["url"])
            articles_by_url.setdefault(
                url,
                article,
            )

    _raise_if_all_discovery_urls_failed(
        successful_fetch_count=successful_fetch_count,
        discovery_errors=discovery_errors,
    )
    return list(articles_by_url.values())


def _decode_resource_content(content: str | bytes) -> str:
    if isinstance(content, bytes):
        return content.decode(
            "utf-8",
            errors="ignore",
        )

    return content


def _parse_xml_root(content: str | bytes):
    try:
        return ElementTree.fromstring(
            _decode_resource_content(content)
        )
    except ElementTree.ParseError:
        return None


def _xml_text(node, path: str) -> str:
    value = node.findtext(
        path,
        default="",
        namespaces={
            "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
        },
    )

    return value.strip()


def _parse_sitemap_locations(content: str | bytes) -> list[str]:
    root = _parse_xml_root(content)

    if root is None:
        return []

    return [
        _xml_text(node, "sm:loc")
        for node in root.findall(
            ".//sm:sitemap",
            {
                "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
            },
        )
        if _xml_text(node, "sm:loc")
    ]


def _parse_sitemap_url_entries(content: str | bytes) -> list[tuple[str, str]]:
    root = _parse_xml_root(content)

    if root is None:
        return []

    entries: list[tuple[str, str]] = []

    for node in root.findall(
        ".//sm:url",
        {
            "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
        },
    ):
        loc = _xml_text(node, "sm:loc")

        if not loc:
            continue

        entries.append(
            (
                loc,
                _xml_text(node, "sm:lastmod"),
            )
        )

    return entries


def _parse_iso_datetime(value: str) -> datetime | None:
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        ).replace(tzinfo=None)
    except ValueError:
        return None


def _is_csis_sitemap_analysis_candidate(url: str) -> bool:
    path = urlsplit(url).path.lower()

    return (
        path.startswith("/analysis/")
        and has_china_signal(
            title="",
            url=url,
        )
    )


def _extract_page_title(content: str | bytes) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(
        content,
        "html.parser",
    )
    title_node = soup.select_one("h1")

    if title_node is not None:
        title = " ".join(
            title_node.get_text(
                " ",
                strip=True,
            ).split()
        )

        if title:
            return title

    if soup.title is not None:
        title = " ".join(
            soup.title.get_text(
                " ",
                strip=True,
            ).split()
        )

        if title:
            return title

    return ""


async def _fetch_csis_sitemap_report_articles() -> list[dict[str, object]]:
    """
    CSIS 的筛选页在当前环境容易 403。

    作为保守补充入口，读取公开 sitemap，先筛出 URL 本身带涉华信号的
    /analysis/ 页面，再打开页面确认存在 PDF 链接，才作为候选报告。
    """
    try:
        sitemap_index = await fetch_resource(
            CSIS_SITEMAP_URL,
            timeout_seconds=DISCOVERY_FETCH_TIMEOUT_SECONDS,
        )
    except Exception:
        return []

    sitemap_urls = _parse_sitemap_locations(
        sitemap_index.content
    )
    entries: list[tuple[str, str]] = []

    for sitemap_url in sitemap_urls:
        try:
            sitemap = await fetch_resource(
                sitemap_url,
                timeout_seconds=DISCOVERY_FETCH_TIMEOUT_SECONDS,
            )
        except Exception:
            continue

        entries.extend(
            (
                loc,
                lastmod,
            )
            for loc, lastmod in _parse_sitemap_url_entries(
                sitemap.content
            )
            if _is_csis_sitemap_analysis_candidate(loc)
        )

    entries.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    reports: list[dict[str, object]] = []

    for url, lastmod in entries[:CSIS_SITEMAP_MAX_PAGE_FETCHES]:
        try:
            page = await fetch_resource(
                url,
                timeout_seconds=DISCOVERY_FETCH_TIMEOUT_SECONDS,
            )
        except Exception:
            continue

        if extract_report_pdf_url(
            page.content,
            page.final_url,
        ) is None:
            continue

        title = _extract_page_title(
            page.content
        )

        if not title:
            continue

        reports.append(
            {
                "title": title,
                "url": page.final_url,
                "published_at": _parse_iso_datetime(
                    lastmod
                ),
                "content_type": "report",
            }
        )

    return reports


async def _fetch_csis_website_articles(
    source_url: str,
) -> list[dict[str, object]]:
    discovery_urls = (
        source_url,
        *(
            url
            for url in CSIS_DISCOVERY_URLS
            if url != source_url
        ),
    )

    articles = await _fetch_multi_entry_website_articles(
        discovery_urls=discovery_urls,
        parser=parse_csis_reports,
    )

    articles_by_url = {
        str(article["url"]): article
        for article in articles
    }

    for article in await _fetch_csis_sitemap_report_articles():
        articles_by_url.setdefault(
            str(article["url"]),
            article,
        )

    return list(
        articles_by_url.values()
    )


async def fetch_source_articles(
    source: Source,
) -> list[dict[str, object]]:
    """
    根据 Source 类型读取候选报告条目。

    RSS 来源使用通用 RSS parser；website 来源按域名路由到专用解析器。
    """
    if source.source_type == SourceTypeEnum.rss:
        feed_content = await fetch_html(
            source.url
        )

        return parse_rss_articles(
            feed_content,
            source.url,
        )

    if source.source_type == SourceTypeEnum.website:
        hostname = urlsplit(
            source.url
        ).netloc.lower()

        if hostname in {
            "www.csis.org",
            "csis.org",
        }:
            return await _fetch_csis_website_articles(
                source.url
            )

        if hostname in {
            "www.brookings.edu",
            "brookings.edu",
        }:
            discovery_urls = (
                source.url,
                *(
                    url
                    for url in BROOKINGS_DISCOVERY_URLS
                    if url != source.url
                ),
            )
            return await _fetch_multi_entry_website_articles(
                discovery_urls=discovery_urls,
                parser=parse_brookings_reports,
            )

        if hostname in {
            "www.americanprogress.org",
            "americanprogress.org",
        }:
            discovery_urls = (
                source.url,
                *(
                    url
                    for url in CAP_DISCOVERY_URLS
                    if url != source.url
                ),
            )
            return await _fetch_multi_entry_website_articles(
                discovery_urls=discovery_urls,
                parser=parse_cap_reports,
            )

        if hostname in {
            "www.nber.org",
            "nber.org",
        }:
            return await _fetch_multi_entry_website_articles(
                discovery_urls=NBER_DISCOVERY_URLS,
                parser=parse_nber_working_papers,
            )

        if hostname in {
            "www.chathamhouse.org",
            "chathamhouse.org",
        }:
            discovery_urls = (
                source.url,
                *(
                    url
                    for url in CHATHAM_HOUSE_DISCOVERY_URLS
                    if url != source.url
                ),
            )
            return await _fetch_multi_entry_website_articles(
                discovery_urls=discovery_urls,
                parser=parse_chatham_house_reports,
            )

        if hostname in {
            "ecfr.eu",
            "www.ecfr.eu",
        }:
            discovery_urls = (
                source.url,
                *(
                    url
                    for url in ECFR_DISCOVERY_URLS
                    if url != source.url
                ),
            )
            return await _fetch_multi_entry_website_articles(
                discovery_urls=discovery_urls,
                parser=parse_ecfr_reports,
            )

        core_site_config = CORE_US_SITE_CONFIG_BY_HOST.get(
            hostname
        )

        if core_site_config is not None:
            discovery_urls = (
                source.url,
                *(
                    url
                    for url in core_site_config.discovery_urls
                    if url != source.url
                ),
            )

            return await _fetch_multi_entry_website_articles(
                discovery_urls=discovery_urls,
                parser=lambda content, final_url: parse_core_site_reports(
                    content,
                    final_url,
                    core_site_config,
                ),
            )

        raise ValueError(
            "当前尚未配置该 website 来源的专用解析器："
            f"{source.url}"
        )

    raise ValueError(
        "当前不支持此来源类型抓取："
        f"{source.source_type.value}"
    )
