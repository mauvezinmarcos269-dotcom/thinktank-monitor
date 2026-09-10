import argparse
import asyncio
import json
import sys

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.report import Report
from app.workers.celery_app import celery_app


async def reset_report(
    report_id: int,
) -> dict[str, int | str | None]:
    """
    清空指定报告的旧正文和抓取状态。

    不删除报告本身，也不修改标题、URL、发布时间、来源等元数据。
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

        old_status = report.crawl_status
        old_content_length = (
            len(report.content)
            if report.content
            else 0
        )

        # 清空旧正文及抓取结果
        report.content = None
        report.content_hash = None
        report.content_fetched_at = None
        report.crawl_error = None
        report.translation = None
        report.summary = None
        report.commentary = None
        report.ai_generated_at = None

        # 恢复为待抓取状态
        report.crawl_status = "pending"

        # 正文被清空后，AI 分析结果也应重新生成
        report.ai_status = "pending"
        report.ai_retry_count = 0

        await db.commit()

        return {
            "status": "reset",
            "report_id": report_id,
            "old_crawl_status": old_status,
            "old_content_length": old_content_length,
            "new_crawl_status": report.crawl_status,
            "new_ai_status": report.ai_status,
        }


async def main_async(
    report_id: int,
    reset_only: bool,
) -> int:
    reset_result = await reset_report(report_id)

    print(
        json.dumps(
            reset_result,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )

    if reset_result["status"] == "not_found":
        return 1

    if reset_only:
        print("报告已重置，但没有提交 Celery 抓取任务。")
        return 0

    # 必须在数据库事务提交后再发送任务，避免 Worker 提前读取旧状态
    task = celery_app.send_task(
        "report.fetch_content",
        args=[report_id],
    )

    print(
        json.dumps(
            {
                "status": "queued",
                "report_id": report_id,
                "task_name": "report.fetch_content",
                "task_id": task.id,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="清空报告旧正文并重新提交网页抓取任务。",
    )

    parser.add_argument(
        "report_id",
        type=int,
        help="需要重新抓取的报告 ID",
    )

    parser.add_argument(
        "--reset-only",
        action="store_true",
        help="只重置数据库状态，不提交 Celery 任务",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    exit_code = asyncio.run(
        main_async(
            report_id=args.report_id,
            reset_only=args.reset_only,
        )
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
