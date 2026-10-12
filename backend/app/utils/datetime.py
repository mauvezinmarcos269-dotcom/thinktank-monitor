from datetime import UTC, datetime


def utc_now_naive() -> datetime:
    """返回适用于 TIMESTAMP WITHOUT TIME ZONE (DateTime) 的无时区 UTC 时间。"""
    return datetime.now(UTC).replace(tzinfo=None)

def utc_now_aware() -> datetime:
    """返回适用于 TIMESTAMP WITH TIME ZONE (DateTime(timezone=True)) 的带时区 UTC 时间。"""
    return datetime.now(UTC)
