from bs4 import BeautifulSoup


def parse_articles(
    html: str
) -> list[dict]:
    """
    解析网页文章

    返回:
    [
        {
            "title": "...",
            "url": "...",
        }
    ]
    """

    if not html:
        return []


    soup = BeautifulSoup(
        html,
        "html.parser"
    )


    articles = []


    # 提取所有链接
    for a in soup.find_all("a"):

        title = a.get_text(
            strip=True
        )

        href = a.get(
            "href"
        )


        if not title:
            continue


        if not href:
            continue


        articles.append(
            {
                "title": title,
                "url": href,
            }
        )


    return articles
