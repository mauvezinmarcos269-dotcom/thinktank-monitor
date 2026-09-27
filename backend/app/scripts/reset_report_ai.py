import argparse
import asyncio
import json
import sys

from sqlalchemy import delete, select

from app.core.status import ReportAIStatus
from app.db.session import AsyncSessionLocal
from app.models.report import Report
from app.models.report_ai_chunk import ReportAIChunk


async def reset_report_ai(
    report_id: int,
) -> dict[str, int | str | None]:
    """
    清空指定报告的 AI 输出和分块。

    不删除报告正文、PDF 元数据、抓取状态或来源信息。
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Report).where(Report.id == report_id)
        )
        report = result.scalar_one_or_none()

        if report is None:
            return {
                "status": "not_found",
                "report_id": report_id,
                "error": "Report does not exist",
            }

        old_ai_status = report.ai_status
        old_translation_length = len(report.translation or "")
        old_summary_length = len(report.summary or "")
        old_commentary_length = len(report.commentary or "")

        delete_result = await db.execute(
            delete(ReportAIChunk).where(
                ReportAIChunk.report_id == report_id
            )
        )

        report.translation = None
        report.summary = None
        report.commentary = None
        report.ai_generated_at = None
        report.ai_status = ReportAIStatus.pending.value
        report.ai_retry_count = 0

        await db.commit()

        return {
            "status": "reset",
            "report_id": report_id,
            "old_ai_status": old_ai_status,
            "deleted_chunks": delete_result.rowcount or 0,
            "old_translation_length": old_translation_length,
            "old_summary_length": old_summary_length,
            "old_commentary_length": old_commentary_length,
            "new_ai_status": report.ai_status,
        }


async def main_async(
    report_id: int,
) -> int:
    result = await reset_report_ai(report_id)

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )

    if result["status"] == "not_found":
        return 1

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="清空指定报告的 AI 输出和分块，保留已抓取正文。",
    )

    parser.add_argument(
        "report_id",
        type=int,
        help="需要重置 AI 结果的报告 ID",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    exit_code = asyncio.run(
        main_async(
            report_id=args.report_id,
        )
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
