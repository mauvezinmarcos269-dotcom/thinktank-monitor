from datetime import datetime

from app.services.crawler.nber_parser import parse_nber_working_papers


def test_parse_nber_working_papers_keeps_china_papers() -> None:
    content = """
{
  "results": [
    {
      "title": "The China Backlash: Quantifying the Narrative Discourse on China",
      "type": "working_paper",
      "url": "/papers/w35539",
      "displaydate": "August 2026"
    },
    {
      "title": "The Annals of China",
      "type": "chapter",
      "url": "/books-and-chapters/business-annals/annals-china"
    },
    {
      "title": "Labor Market Dynamics",
      "type": "working_paper",
      "url": "/papers/w35540",
      "displaydate": "September 12, 2026"
    }
  ]
}
"""

    articles = parse_nber_working_papers(
        content,
        "https://www.nber.org/api/v1/search?q=China",
    )

    assert articles == [
        {
            "title": (
                "The China Backlash: Quantifying the Narrative "
                "Discourse on China"
            ),
            "url": "https://www.nber.org/papers/w35539",
            "published_at": datetime(2026, 8, 1),
            "content_type": "working_paper",
        }
    ]
