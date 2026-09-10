from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    report_id: int | None
    event_type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime


class NotificationUnreadCount(BaseModel):
    unread_count: int
