'use client';

import { useEffect, useState } from 'react';
import { AppShell } from '@/components/app-shell';
import {
  fetchDashboard,
  type DashboardData,
} from '@/lib/dashboard';

type SourceHealthMetricKey =
  | 'healthy_sources'
  | 'warning_sources'
  | 'failed_sources'
  | 'never_crawled_sources'
  | 'disabled_sources';

const sourceHealthLabels: Record<SourceHealthMetricKey, string> = {
  healthy_sources: '健康来源',
  warning_sources: '需关注',
  failed_sources: '失败来源',
  never_crawled_sources: '尚未抓取',
  disabled_sources: '已停用',
};

function formatDateTime(value: string | null): string {
  if (!value) {
    return '无记录';
  }

  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value));
}

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);

  useEffect(() => {
    async function loadDashboard() {
      try {
        const data = await fetchDashboard();
        setDashboard(data);
        setErrorMessage(null);
      } catch (error) {
        console.error(
          '[Dashboard] 数据加载失败:',
          error
        );
        setErrorMessage(
          error instanceof Error ? error.message : '仪表盘数据加载失败。'
        );
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, []);

  if (loading) {
    return (
      <AppShell>
        <div className="panel">加载中...</div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="page-header">
        <h1>监测仪表盘</h1>
        <p>全球智库涉华研究监测、翻译、分析和提醒的统一入口。</p>
      </div>

      {errorMessage && <p className="message-error">{errorMessage}</p>}

      <section className="panel">
        <h2>系统概览</h2>

        <ul className="stats-grid">
          <li className="stat-card">
            已接入智库
            <span className="stat-value">
              {dashboard?.overview.think_tanks ?? 0}
            </span>
          </li>

          <li className="stat-card">
            已配置来源
            <span className="stat-value">
              {dashboard?.overview.sources ?? 0}
            </span>
          </li>

          <li className="stat-card">
            已收录报告
            <span className="stat-value">
              {dashboard?.overview.reports ?? 0}
            </span>
          </li>

          <li className="stat-card">
            抓取任务
            <span className="stat-value">
              {(dashboard?.overview.pending_crawl_runs ?? 0) +
                (dashboard?.overview.running_crawl_runs ?? 0)}
            </span>
            <span className="muted">
              待执行 {dashboard?.overview.pending_crawl_runs ?? 0} / 运行中{' '}
              {dashboard?.overview.running_crawl_runs ?? 0}
            </span>
          </li>

          <li className="stat-card">
            AI 处理队列
            <span className="stat-value">
              {(dashboard?.overview.pending_ai_reports ?? 0) +
                (dashboard?.overview.running_ai_reports ?? 0)}
            </span>
            <span className="muted">
              失败 {dashboard?.overview.failed_ai_reports ?? 0}
            </span>
          </li>

          <li className="stat-card">
            未读通知
            <span className="stat-value">
              {dashboard?.overview.unread_notifications ?? 0}
            </span>
          </li>
        </ul>
      </section>

      <section className="panel">
        <h2>来源健康</h2>

        <ul className="stats-grid">
          <li className="stat-card">
            活跃来源
            <span className="stat-value">
              {dashboard?.source_health.active_sources ?? 0}
            </span>
            <span className="muted">
              总计 {dashboard?.source_health.total_sources ?? 0}
            </span>
          </li>

          {Object.entries(sourceHealthLabels).map(([key, label]) => (
            <li className="stat-card" key={key}>
              {label}
              <span className="stat-value">
                {dashboard?.source_health[key as SourceHealthMetricKey] ?? 0}
              </span>
            </li>
          ))}
        </ul>

        <h3>最近失败原因</h3>
        {dashboard?.source_health.recent_failures.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>机构</th>
                  <th>来源</th>
                  <th>最近抓取</th>
                  <th>失败原因</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.source_health.recent_failures.map((failure) => (
                  <tr key={failure.source_id}>
                    <td>{failure.think_tank_name}</td>
                    <td>{failure.url}</td>
                    <td>{formatDateTime(failure.last_crawled_at)}</td>
                    <td>{failure.last_error ?? '最近一次抓取失败'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted">暂无失败来源。</p>
        )}
      </section>

      <section className="panel">
        <h2>候选报告统计</h2>

        <div className="status-line">
          <span className="badge">
            全部 {dashboard?.crawl_candidates.total ?? 0}
          </span>
          {dashboard?.crawl_candidates.by_status.map((item) => (
            <span className="badge" key={item.code ?? item.label}>
              {item.label} {item.count}
            </span>
          ))}
        </div>

        <h3>主要跳过原因</h3>
        {dashboard?.crawl_candidates.by_skip_reason.length ? (
          <div className="status-line">
            {dashboard.crawl_candidates.by_skip_reason.map((item) => (
              <span
                className="badge badge-warning"
                key={item.code ?? item.label}
              >
                {item.label} {item.count}
              </span>
            ))}
          </div>
        ) : (
          <p className="muted">暂无跳过记录。</p>
        )}
      </section>
    </AppShell>
  );
}
