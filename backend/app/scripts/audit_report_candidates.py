import asyncio
from collections import Counter

from sqlalchemy import or_, select

from app.db.session import AsyncSessionLocal
from app.models.report import Report
from app.services.crawler.report_document_service import (
    fetch_report_document,
)

SOURCE_ID = 51


def classify_error(message: str) -> str:
    if "未发现 PDF 链接" in message:
        return "no_pdf"

    if "报告页数不足" in message:
        return "too_short"

    return "other_error"


async def main() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Report)
            .where(
                Report.source_id == SOURCE_ID,
                or_(
                    Report.url.like(
                        "%/in-depth-research-reports/report/%"
                    ),
                    Report.url.like(
                        "%/in-depth-research-reports/issue-brief/%"
                    ),
                ),
            )
            .order_by(Report.id.desc())
        )

        reports = result.scalars().all()

    print("candidate count:", len(reports))
    print()

    accepted = []
    rejected = []
    reason_counter = Counter()

    for report in reports:
        try:
            document = await fetch_report_document(
                report.url
            )

            accepted.append(
                (
                    report.id,
                    report.title,
                    document.page_count,
                    len(document.text),
                    document.pdf_url,
                )
            )

            print(
                f"{report.id:>4} | ACCEPT | "
                f"{document.page_count:>3} pages | "
                f"{len(document.text):>7} chars | "
                f"{report.title}"
            )

        except Exception as exc:
            error_message = str(exc)
            reason = classify_error(error_message)

            reason_counter[reason] += 1

            rejected.append(
                (
                    report.id,
                    report.title,
                    reason,
                    error_message,
                )
            )

            print(
                f"{report.id:>4} | REJECT | "
                f"{reason:<11} | "
                f"{report.title}"
            )

    print()
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)

    print("total candidates:", len(reports))
    print("accepted:", len(accepted))
    print("rejected:", len(rejected))

    for reason, count in sorted(
        reason_counter.items()
    ):
        print(
            f"rejected {reason}:",
            count,
        )

    print()
    print("=" * 100)
    print("ACCEPTED REPORTS")
    print("=" * 100)

    for (
        report_id,
        title,
        page_count,
        text_length,
        pdf_url,
    ) in accepted:
        print()
        print("ID:", report_id)
        print("TITLE:", title)
        print("PAGES:", page_count)
        print("TEXT CHARS:", text_length)
        print("PDF:", pdf_url)


if __name__ == "__main__":
    asyncio.run(main())
