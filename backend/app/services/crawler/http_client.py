import httpx


async def fetch_html(url: str) -> str:
    """获取网页、RSS 或 Atom 内容，允许站点的正常重定向。"""
    async with httpx.AsyncClient(
        timeout=20,
        follow_redirects=True,
    ) as client:
        response = await client.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(compatible; ThinkTankMonitor/1.0; "
                    "+https://localhost)"
                ),
                "Accept": (
                    "application/rss+xml, "
                    "application/atom+xml, "
                    "application/xml, "
                    "text/xml, "
                    "text/html;q=0.9, "
                    "*/*;q=0.8"
                ),
            },
        )

        response.raise_for_status()

        return response.text
