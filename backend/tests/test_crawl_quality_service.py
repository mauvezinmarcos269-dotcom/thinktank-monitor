from app.services.crawl_quality_service import CrawlQualityStats


def test_quality_summary_is_empty_when_nothing_was_skipped() -> None:
    stats = CrawlQualityStats(
        raw_candidates=2,
        unique_candidates=2,
        saved_reports=2,
    )

    assert stats.to_summary() is None


def test_quality_summary_includes_skip_counts_and_samples() -> None:
    stats = CrawlQualityStats(
        raw_candidates=5,
        unique_candidates=4,
        saved_reports=1,
        duplicate_in_feed=1,
        duplicate_existing=1,
        document_failed=1,
        non_china_related=1,
    )
    stats.add_sample("PDF 获取或页数/文本检查失败", "https://example.org/a", "报告页数不足")
    stats.add_sample("非涉华", "https://example.org/b", "主题无关")

    summary = stats.to_summary()

    assert summary is not None
    assert "原始候选 5 条" in summary
    assert "有效去重后 4 条" in summary
    assert "入库 1 条" in summary
    assert "同一来源内重复 1 条" in summary
    assert "已入库重复 1 条" in summary
    assert "PDF 获取或页数/文本检查失败 1 条" in summary
    assert "非涉华 1 条" in summary
    assert "https://example.org/a" in summary
