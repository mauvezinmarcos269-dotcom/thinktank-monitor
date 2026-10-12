from app.services.crawler.content_extractor import extract_report_pdf_url


def test_extract_report_pdf_url_accepts_full_text_pdf_link() -> None:
    html = """
<html>
  <body>
    <a href="https://assets.carnegieendowment.org/files/Zhao_Nuclear%20Knot.pdf">
      Full Text (PDF)
    </a>
  </body>
</html>
"""

    pdf_url = extract_report_pdf_url(
        html,
        "https://carnegieendowment.org/research/2026/09/china-nuclear-report",
    )

    assert pdf_url == (
        "https://assets.carnegieendowment.org/files/Zhao_Nuclear%20Knot.pdf"
    )


def test_extract_report_pdf_url_rejects_full_text_non_pdf_link() -> None:
    html = """
<html>
  <body>
    <a href="https://example.org/full-text">Full Text</a>
  </body>
</html>
"""

    assert (
        extract_report_pdf_url(
            html,
            "https://carnegieendowment.org/research/2026/09/china-report",
        )
        is None
    )
