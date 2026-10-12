from app.core.status import CrawlCandidateSkipReason
from app.services.crawl_quality_service import CrawlQualityStats
from app.services.crawler.candidate_intake import intake_crawl_candidates


class _FakeDb:
    def __init__(self) -> None:
        self.added = []

    def add(self, value) -> None:
        self.added.append(value)


def test_intake_preflight_skips_document_failure_without_processing_queue() -> None:
    quality_stats = CrawlQualityStats(raw_candidates=2)
    db = _FakeDb()

    result = intake_crawl_candidates(
        db,  # type: ignore[arg-type]
        parsed_articles=[
            {
                "title": "China no PDF",
                "url": "https://example.org/reports/china-no-pdf",
                "preflight_skip_reason_code": (
                    CrawlCandidateSkipReason.document_failed.value
                ),
                "preflight_skip_error": (
                    "发现阶段预检：报告详情页中未发现 PDF 链接。"
                ),
            },
            {
                "title": "China PDF",
                "url": "https://example.org/reports/china-pdf",
                "pdf_url": "https://example.org/china-pdf.pdf",
            },
        ],
        crawl_run_id=10,
        source_id=20,
        quality_stats=quality_stats,
    )

    skipped_candidate = db.added[0]
    queued_candidate = db.added[1]

    assert result.unique_candidate_count == 2
    assert list(result.articles_by_url) == [
        "https://example.org/reports/china-pdf",
    ]
    assert skipped_candidate.skip_reason_label == "未发现 PDF 链接"
    assert skipped_candidate.error == "发现阶段预检：报告详情页中未发现 PDF 链接。"
    assert queued_candidate.pdf_url == "https://example.org/china-pdf.pdf"
    assert quality_stats.unique_candidates == 2
    assert quality_stats.document_failed == 1
    assert quality_stats.document_failure_counts == {
        "未发现 PDF 链接": 1,
    }
