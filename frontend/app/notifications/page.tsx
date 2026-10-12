'use client';

import { useCallback, useState } from 'react';
import Link from 'next/link';

import { AppShell } from '@/components/app-shell';
import { formatDailySummaryMessage } from '@/lib/crawl-error';
import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type DailySummaryFailureSource,
  type Notification,
} from '@/lib/notification';
import { formatReportFailureNotification } from '@/lib/report-error';
import { useNotificationPolling } from '@/lib/use-notification-polling';
import { notificationEventTypeLabels, type NotificationEventType } from '@/lib/status';

const notificationEventFilters: NotificationEventType[] = [
  'report.created',
  'report.ai_completed',
  'report.ai_failed',
  'report.fetch_failed',
  'report.review_needs_rerun',
  'daily_summary',
];

const notificationPreviewLength = 180;

function formatNotificationTime(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function getReportView(eventType: string): string {
  if (
    eventType === 'report.ai_completed' ||
    eventType === 'report.ai_failed' ||
    eventType === 'report.review_needs_rerun'
  ) {
    return 'summary';
  }

  return 'content';
}

function getNotificationEventLabel(eventType: string): string {
  return notificationEventTypeLabels[eventType as keyof typeof notificationEventTypeLabels] ?? eventType;
}

function getNotificationMessage(eventType: string, message: string): string {
  if (eventType === 'daily_summary') {
    return formatDailySummaryMessage(message);
  }

  return formatReportFailureNotification(eventType, message);
}

function getNotificationPreview(message: string): string {
  const compactMessage = message.replace(/\s+/g, ' ').trim();

  if (compactMessage.length <= notificationPreviewLength) {
    return compactMessage;
  }

  return `${compactMessage.slice(0, notificationPreviewLength)}...`;
}

function hasLongNotificationMessage(message: string): boolean {
  return message.length > notificationPreviewLength || message.includes('\n');
}

function getDailySummaryFailureCount(message: string): number | null {
  const match = message.match(/当前失败来源\s+(\d+)\s*个/);

  return match ? Number(match[1]) : null;
}

function getDailySummarySourceHealthAction(message: string): { href: string; label: string } {
  const failureCount = getDailySummaryFailureCount(message);
  const params = new URLSearchParams({
    focus: 'source-health',
    source_health: failureCount && failureCount > 0 ? 'crawl_attention' : 'needs_review',
  });

  return {
    href: `/settings?${params.toString()}`,
    label: failureCount && failureCount > 0 ? '查看失败来源' : '查看来源状态',
  };
}

function isDailySummaryFailureSource(value: unknown): value is DailySummaryFailureSource {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const source = value as { source_id?: unknown; think_tank_name?: unknown };

  return (
    typeof source.source_id === 'number' &&
    Number.isFinite(source.source_id) &&
    typeof source.think_tank_name === 'string' &&
    source.think_tank_name.trim().length > 0
  );
}

function getDailySummaryFailureSources(notification: Notification): DailySummaryFailureSource[] {
  if (notification.event_type !== 'daily_summary') {
    return [];
  }

  const failureSources = notification.payload?.daily_summary?.failure_sources;

  if (!Array.isArray(failureSources)) {
    return [];
  }

  return failureSources.filter(isDailySummaryFailureSource).slice(0, 5);
}

function getSourceHealthHref(sourceId: number): string {
  const params = new URLSearchParams({
    focus: 'source-health',
    source_id: String(sourceId),
  });

  return `/settings?${params.toString()}`;
}

function notifyUnreadCountChanged() {
  window.dispatchEvent(new Event('thinktank:notifications-updated'));
}

export default function NotificationsPage() {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [markingAll, setMarkingAll] = useState(false);
  const [eventTypeFilter, setEventTypeFilter] = useState<NotificationEventType | ''>('');

  const loadNotifications = useCallback(
    (signal: AbortSignal) => fetchNotifications({ eventType: eventTypeFilter, signal }),
    [eventTypeFilter]
  );
  const {
    data,
    setData: setNotifications,
    loading,
    error: refreshError,
    refresh,
    cancel,
  } = useNotificationPolling(loadNotifications, {
    paused: updatingId !== null || markingAll,
  });
  const notifications = data ?? [];
  const activeFilterLabel = eventTypeFilter ? getNotificationEventLabel(eventTypeFilter) : '全部类型';
  const unreadNotificationCount = notifications.filter((notification) => !notification.is_read).length;
  const dailySummaryCount = notifications.filter((notification) => notification.event_type === 'daily_summary').length;
  const reportLinkedCount = notifications.filter((notification) => notification.report_id !== null).length;

  function handleEventTypeFilterChange(value: NotificationEventType | '') {
    setEventTypeFilter(value);
    setSuccessMessage(null);
    setErrorMessage(null);
  }

  async function handleMarkRead(notificationId: number) {
    cancel();
    setUpdatingId(notificationId);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const updated = await markNotificationRead(notificationId);
      setNotifications((current) =>
        (current ?? []).map((notification) => (notification.id === updated.id ? updated : notification))
      );
      notifyUnreadCountChanged();
      setSuccessMessage('通知已标记为已读。');
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '通知更新失败。');
    } finally {
      setUpdatingId(null);
    }
  }

  async function handleMarkAllRead() {
    cancel();
    setMarkingAll(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const response = await markAllNotificationsRead();
      setNotifications((current) =>
        (current ?? []).map((notification) => ({
          ...notification,
          is_read: true,
        }))
      );
      notifyUnreadCountChanged();
      setSuccessMessage(`已标记 ${response.updated_count} 条通知。`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '通知更新失败。');
    } finally {
      setMarkingAll(false);
    }
  }

  return (
    <AppShell>
      <div className="page-header">
        <h1>通知提醒</h1>
      </div>

      <section className="panel">
        <div className="toolbar">
          <label>
            类型
            <select
              value={eventTypeFilter}
              onChange={(event) => handleEventTypeFilterChange(event.target.value as NotificationEventType | '')}
              disabled={updatingId !== null || markingAll}
            >
              <option value="">全部</option>
              {notificationEventFilters.map((eventType) => (
                <option key={eventType} value={eventType}>
                  {getNotificationEventLabel(eventType)}
                </option>
              ))}
            </select>
          </label>
          <button type="button" onClick={() => void refresh()} disabled={loading || updatingId !== null || markingAll}>
            {loading ? '刷新中……' : '刷新'}
          </button>
          <button
            type="button"
            onClick={handleMarkAllRead}
            disabled={markingAll || updatingId !== null || notifications.length === 0}
          >
            {markingAll ? '处理中……' : '全部标记已读'}
          </button>
        </div>

        {loading && data === null && <p role="status">正在加载通知……</p>}
        {(errorMessage || refreshError) && (
          <p className="message-error" role="alert">
            {errorMessage || refreshError}
          </p>
        )}
        {successMessage && <p className="message-success">{successMessage}</p>}

        {data !== null ? (
          <div className="notification-overview" aria-label="通知概览">
            <span>
              <strong>{notifications.length}</strong>
              <small>{activeFilterLabel}</small>
            </span>
            <span>
              <strong>{unreadNotificationCount}</strong>
              <small>未读</small>
            </span>
            <span>
              <strong>{dailySummaryCount}</strong>
              <small>采集摘要</small>
            </span>
            <span>
              <strong>{reportLinkedCount}</strong>
              <small>报告入口</small>
            </span>
          </div>
        ) : null}

        {!loading && data !== null && notifications.length === 0 ? (
          <p>暂无通知。</p>
        ) : (
          <ul className="notification-list">
            {notifications.map((notification) => {
              const notificationMessage = getNotificationMessage(notification.event_type, notification.message);
              const isLongMessage = hasLongNotificationMessage(notificationMessage);
              const dailySummaryAction =
                notification.event_type === 'daily_summary'
                  ? getDailySummarySourceHealthAction(notificationMessage)
                  : null;
              const dailySummaryFailureSources = getDailySummaryFailureSources(notification);
              const dailySummaryActionLabel =
                dailySummaryAction && dailySummaryFailureSources.length > 0
                  ? '查看全部失败来源'
                  : dailySummaryAction?.label;

              return (
                <li
                  className={notification.is_read ? 'notification-item' : 'notification-item notification-item-unread'}
                  key={notification.id}
                >
                  <article>
                    <div className="notification-title-row">
                      <h2>{notification.title}</h2>
                      {notification.is_read ? null : <span className="badge badge-warning">未读</span>}
                    </div>
                    <p className="notification-message notification-message-preview">
                      {getNotificationPreview(notificationMessage)}
                    </p>
                    {isLongMessage ? (
                      <details className="notification-message-details">
                        <summary>展开完整通知</summary>
                        <p className="notification-message notification-message-full">{notificationMessage}</p>
                      </details>
                    ) : null}
                    <p className="notification-meta">
                      {getNotificationEventLabel(notification.event_type)} /{' '}
                      {formatNotificationTime(notification.created_at)}
                    </p>
                    {dailySummaryFailureSources.length > 0 ? (
                      <div className="notification-source-links" aria-label="失败来源快捷入口">
                        {dailySummaryFailureSources.map((source) => (
                          <Link
                            className="button-secondary notification-source-link"
                            href={getSourceHealthHref(source.source_id)}
                            key={source.source_id}
                            title={
                              source.reason
                                ? `${source.think_tank_name}：${source.reason}`
                                : source.think_tank_name
                            }
                          >
                            {source.think_tank_name}
                          </Link>
                        ))}
                      </div>
                    ) : null}
                    <div className="notification-actions">
                      {notification.report_id ? (
                        <Link
                          className="button-secondary"
                          href={`/reports?report_id=${notification.report_id}&view=${getReportView(
                            notification.event_type
                          )}&focus=review`}
                        >
                          查看报告
                        </Link>
                      ) : null}
                      {dailySummaryAction ? (
                        <Link className="button-secondary" href={dailySummaryAction.href}>
                          {dailySummaryActionLabel}
                        </Link>
                      ) : null}
                      {!notification.is_read && (
                        <button
                          type="button"
                          onClick={() => handleMarkRead(notification.id)}
                          disabled={updatingId !== null || markingAll}
                        >
                          {updatingId === notification.id ? '处理中……' : '标记已读'}
                        </button>
                      )}
                    </div>
                  </article>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </AppShell>
  );
}
