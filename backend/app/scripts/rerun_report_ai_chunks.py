import argparse
import asyncio
import json
import sys

from app.db.session import AsyncSessionLocal
from app.models.report_ai_chunk import ReportAIChunk
from app.services.ai.report_ai_chunk_runner import run_report_ai_chunk
from app.services.ai.report_ai_finalizer_runner import run_report_ai_finalization
from app.utils.datetime import utc_now_naive


async def reset_chunk_for_retry(
    chunk_id: int,
) -> str:
    async with AsyncSessionLocal() as db:
        chunk = await db.get(ReportAIChunk, chunk_id)

        if chunk is None:
            return "not_found"

        if chunk.status == "success":
            return "success"

        chunk.status = "failed"
        chunk.last_error = "Manual chunk rerun requested"
        chunk.updated_at = utc_now_naive()

        await db.commit()

    return "reset"


async def main_async(
    chunk_ids: list[int],
    finalize_report_id: int | None,
) -> int:
    results = []

    for chunk_id in chunk_ids:
        reset_status = await reset_chunk_for_retry(chunk_id)

        if reset_status == "not_found":
            results.append(
                {
                    "chunk_id": chunk_id,
                    "status": "not_found",
                }
            )
            continue

        if reset_status == "success":
            results.append(
                {
                    "chunk_id": chunk_id,
                    "status": "already_success",
                }
            )
            continue

        result = await run_report_ai_chunk(chunk_id)
        results.append(
            {
                "chunk_id": result.chunk_id,
                "status": result.status,
                "retry_count": result.retry_count,
                "output_length": result.output_length,
                "error": result.error,
            }
        )

    payload: dict[str, object] = {
        "chunks": results,
    }

    if finalize_report_id is not None:
        final = await run_report_ai_finalization(finalize_report_id)
        payload["finalization"] = {
            "report_id": finalize_report_id,
            "status": final.status,
            "retry_count": final.retry_count,
            "translation_length": final.translation_length,
            "summary_length": final.summary_length,
            "commentary_length": final.commentary_length,
            "error": final.error,
        }

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )

    failed = [
        item
        for item in results
        if item["status"] not in {
            "success",
            "already_success",
        }
    ]

    if failed:
        return 2

    if (
        finalize_report_id is not None
        and payload.get("finalization", {}).get("status")
        != "success"
    ):
        return 3

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="重跑指定 AI 分块，可选执行报告 finalizer。",
    )

    parser.add_argument(
        "chunk_ids",
        type=int,
        nargs="+",
        help="需要重跑的 AI chunk ID",
    )

    parser.add_argument(
        "--finalize-report-id",
        type=int,
        default=None,
        help="所有 chunk 成功后尝试 finalizer 的报告 ID",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    exit_code = asyncio.run(
        main_async(
            chunk_ids=args.chunk_ids,
            finalize_report_id=args.finalize_report_id,
        )
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
