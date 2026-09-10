'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

import { AppShell } from '@/components/app-shell';
import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type Notification,
} from '@/lib/notification';

function formatNotificationTime(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function getReportView(eventType: string): string {
  if (eventType.startsWith('report.ai.')) {
    return 'summary';
  }

  return 'content';
}

function notifyUnreadCountChanged() {
  window.dispatchEvent(new Event('thinktank:notifications-updated'));
}

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [markingAll, setMarkingAll] = useState(false);

  async function loadNotifications() {
    setLoading(true);
    setErrorMessage(null);

    try {
      const data = await fetchNotifications();
      setNotifications(data);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '通知加载失败。'
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadNotifications();
  }, []);

  async function handleMarkRead(notificationId: number) {
    setUpdatingId(notificationId);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const updated = await markNotificationRead(notificationId);
      setNotifications((current) =>
        current.map((notification) =>
          notification.id === updated.id ? updated : notification
        )
      );
      notifyUnreadCountChanged();
      setSuccessMessage('通知已标记为已读。');
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '通知更新失败。'
      );
    } finally {
      setUpdatingId(null);
    }
  }

  async function handleMarkAllRead() {
    setMarkingAll(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const response = await markAllNotificationsRead();
      setNotifications((current) =>
        current.map((notification) => ({
          ...notification,
          is_read: true,
        }))
      );
      notifyUnreadCountChanged();
      setSuccessMessage(`已标记 ${response.updated_count} 条通知。`);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '通知更新失败。'
      );
    } finally {
      setMarkingAll(false);
    }
  }

  return (
    <AppShell>
      <div className="page-header">
        <h1>通知提醒</h1>
        <p>查看新报告、AI 完成和失败提醒。</p>
      </div>

      <section className="panel">
      <div className="toolbar">
        <button type="button" onClick={loadNotifications} disabled={loading}>
          {loading ? '刷新中……' : '刷新'}
        </button>
        <button
          type="button"
          onClick={handleMarkAllRead}
          disabled={markingAll || notifications.length === 0}
        >
          {markingAll ? '处理中……' : '全部标记已读'}
        </button>
      </div>

      {loading && <p>正在加载通知……</p>}
      {errorMessage && <p className="message-error">{errorMessage}</p>}
      {successMessage && <p className="message-success">{successMessage}</p>}

      {!loading && notifications.length === 0 ? (
        <p>暂无通知。</p>
      ) : (
        <ul className="notification-list">
          {notifications.map((notification) => (
            <li className="notification-item" key={notification.id}>
              <article>
                <h2>
                  {notification.title}
                  {notification.is_read ? null : (
                    <span className="badge badge-warning">未读</span>
                  )}
                </h2>
                <p>{notification.message}</p>
                <p className="muted">
                  {notification.event_type} /{' '}
                  {formatNotificationTime(notification.created_at)}
                </p>
                {notification.report_id ? (
                  <p>
                    <Link
                      href={`/reports?report_id=${notification.report_id}&view=${getReportView(
                        notification.event_type
                      )}`}
                    >
                      查看报告
                    </Link>
                  </p>
                ) : null}
                {!notification.is_read && (
                  <button
                    type="button"
                    onClick={() => handleMarkRead(notification.id)}
                    disabled={updatingId === notification.id}
                  >
                    {updatingId === notification.id ? '处理中……' : '标记已读'}
                  </button>
                )}
              </article>
            </li>
          ))}
        </ul>
      )}
      </section>
    </AppShell>
  );
}
