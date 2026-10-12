from app.scripts.refetch_original_fulltext import find_original_fulltext_links


def test_find_original_fulltext_links_prefers_continue_reading_external_link() -> None:
    html = """
<html>
  <body>
    <article>
      <a href="/about">About</a>
      <a href="https://asiasociety.org/policy/report">
        Continue reading at Asia Society.
      </a>
      <a href="https://example.com/related">Related story</a>
    </article>
  </body>
</html>
"""

    candidates = find_original_fulltext_links(
        html,
        "https://www.aei.org/research-products/report/example/",
        preferred_domains={"asiasociety.org"},
    )

    assert candidates
    assert candidates[0].url == "https://asiasociety.org/policy/report"
    assert candidates[0].label == "Continue reading at Asia Society."


def test_find_original_fulltext_links_ignores_unscored_links() -> None:
    html = """
<html>
  <body>
    <a href="https://www.aei.org/about">About AEI</a>
    <a href="/newsletter">Newsletter</a>
  </body>
</html>
"""

    assert (
        find_original_fulltext_links(
            html,
            "https://www.aei.org/research-products/report/example/",
        )
        == []
    )
