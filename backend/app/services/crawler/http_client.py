import httpx


async def fetch_html(url:str):

    async with httpx.AsyncClient(
        timeout=20
    ) as client:

        response = await client.get(
            url,
            headers={
                "User-Agent":
                "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        return response.text
