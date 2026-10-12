import { apiRequest } from '@/lib/api';
import { type NotificationEventType } from '@/lib/status';

export type DailySummaryFailureSource = {
  source_id: number;
  think_tank_name: string;
  source_url?: string | null;
  reason?: string | null;
};

export type NotificationPayload = {
  daily_summary?: {
    lookback_hours?: number;
    failed_sources?: number;
    failure_sources?: DailySummaryFailureSource[];
  };
};

export type Notification = {
  id: number;
  user_id: number;
  report_id: number | null;
  event_type: NotificationEventType | string;
  title: string;
  message: string;
  payload: NotificationPayload | null;
  is_read: boolean;
  created_at: string;
};

export type NotificationUnreadCount = {
  unread_count: number;
};

export async function fetchNotifications(params?: {
  eventType?: NotificationEventType | '';
  signal?: AbortSignal;
}): Promise<Notification[]> {
  const query = new URLSearchParams({
    limit: '100',
  });

  if (params?.eventType) {
    query.set('event_type', params.eventType);
  }

  return apiRequest<Notification[]>(`/api/v1/notifications?${query.toString()}`, {
    signal: params?.signal,
  });
}

export async function fetchUnreadNotificationCount(signal?: AbortSignal): Promise<number> {
  const response = await apiRequest<NotificationUnreadCount>('/api/v1/notifications/unread-count', { signal });

  return response.unread_count;
}

export async function markNotificationRead(notificationId: number): Promise<Notification> {
  return apiRequest<Notification>(`/api/v1/notifications/${notificationId}/read`, {
    method: 'POST',
  });
}

export async function markAllNotificationsRead(): Promise<{
  updated_count: number;
}> {
  return apiRequest<{ updated_count: number }>('/api/v1/notifications/read-all', {
    method: 'POST',
  });
}
