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
        duplicate_pending=1,
        non_china_related=1,
    )
    stats.add_document_failure_sample(
        "https://example.org/a",
        "报告页数不足：10 页，要求至少 20 页。",
    )
    stats.add_sample("非涉华", "https://example.org/b", "主题无关")

    summary = stats.to_summary()

    assert summary is not None
    assert "原始候选 5 条" in summary
    assert "有效去重后 4 条" in summary
    assert "入库 1 条" in summary
    assert "同一来源内重复 1 条" in summary
    assert "已入库重复 1 条" in summary
    assert "已有待授权候选 1 条" in summary
    assert "PDF 页数不足 1 条" in summary
    assert "非涉华 1 条" in summary
    assert "https://example.org/a" in summary


def test_quality_summary_splits_document_failure_labels() -> None:
    stats = CrawlQualityStats(
        raw_candidates=2,
        unique_candidates=2,
    )

    stats.add_document_failure_sample(
        "https://example.org/no-pdf",
        "报告详情页中未发现 PDF 链接。",
    )
    stats.add_document_failure_sample(
        "https://example.org/short",
        "报告页数不足：10 页，要求至少 20 页。",
    )

    summary = stats.to_summary()

    assert summary is not None
    assert "未发现 PDF 链接 1 条" in summary
    assert "PDF 页数不足 1 条" in summary


def test_quality_summary_preserves_waiting_count_without_failures_or_skips() -> None:
    stats = CrawlQualityStats(raw_candidates=2, unique_candidates=2, pending_relevance=2)

    summary = stats.to_summary()

    assert summary is not None
    assert "待授权 2 条" in summary
    assert "入库 0 条" in summary
    assert "跳过" not in summary
    assert "失败" not in summary
    assert "非涉华" not in summary
    assert stats.relevance_failed == stats.non_china_related == stats.document_failed == 0


def test_quality_summary_separates_waiting_from_actual_failures() -> None:
    stats = CrawlQualityStats(
        raw_candidates=3,
        unique_candidates=3,
        pending_relevance=1,
        relevance_failed=1,
        non_china_related=1,
    )

    summary = stats.to_summary()

    assert summary is not None
    assert "待授权 1 条" in summary
    assert "涉华判断失败 1 条" in summary
    assert "非涉华 1 条" in summary
    assert "待授权" not in summary.split("跳过：", 1)[1]
