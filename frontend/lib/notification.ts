import { apiRequest } from '@/lib/api';
import { type NotificationEventType } from '@/lib/status';

export type Notification = {
  id: number;
  user_id: number;
  report_id: number | null;
  event_type: NotificationEventType | string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
};

export type NotificationUnreadCount = {
  unread_count: number;
};

export async function fetchNotifications(params?: {
  eventType?: NotificationEventType | '';
}): Promise<Notification[]> {
  const query = new URLSearchParams({
    limit: '100',
  });

  if (params?.eventType) {
    query.set('event_type', params.eventType);
  }

  return apiRequest<Notification[]>(`/api/v1/notifications?${query.toString()}`);
}

export async function fetchUnreadNotificationCount(): Promise<number> {
  const response = await apiRequest<NotificationUnreadCount>(
    '/api/v1/notifications/unread-count'
  );

  return response.unread_count;
}

export async function markNotificationRead(
  notificationId: number
): Promise<Notification> {
  return apiRequest<Notification>(
    `/api/v1/notifications/${notificationId}/read`,
    {
      method: 'POST',
    }
  );
}

export async function markAllNotificationsRead(): Promise<{
  updated_count: number;
}> {
  return apiRequest<{ updated_count: number }>('/api/v1/notifications/read-all', {
    method: 'POST',
  });
}
