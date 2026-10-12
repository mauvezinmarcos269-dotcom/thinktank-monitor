from __future__ import annotations

from dataclasses import dataclass

import httpx

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 "
    "(Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36 "
    "ThinkTankMonitor/1.0"
)


@dataclass(frozen=True)
class FetchResult:
    """HTTP 下载结果。"""

    content: bytes
    content_type: str
    final_url: str
    status_code: int


async def fetch_resource(
    url: str,
    timeout_seconds: float = 60.0,
) -> FetchResult:
    """
    下载网页、RSS、Atom、PDF 等远程资源。

    返回原始字节以及响应的基本元信息。
    """
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(timeout_seconds),
        follow_redirects=True,
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": (
                "text/html,"
                "application/xhtml+xml,"
                "application/pdf,"
                "application/rss+xml,"
                "application/atom+xml,"
                "application/xml;q=0.9,"
                "text/xml;q=0.9,"
                "*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    return FetchResult(
        content=response.content,
        content_type=response.headers.get(
            "content-type",
            "",
        ),
        final_url=str(response.url),
        status_code=response.status_code,
    )


async def fetch_html(url: str) -> bytes:
    """
    兼容现有调用的网页/RSS下载接口。

    后续新代码统一优先使用 fetch_resource()。
    """
    result = await fetch_resource(
        url,
        timeout_seconds=20.0,
    )
    return result.content
