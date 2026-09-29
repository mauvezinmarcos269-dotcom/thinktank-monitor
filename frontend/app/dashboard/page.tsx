'use client';

import Link from 'next/link';
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

type WorkbenchItem = {
  label: string;
  value: number;
  helper: string;
  href: string;
  tone: 'primary' | 'warning' | 'danger' | 'neutral';
};

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

function formatPercent(value: number, total: number): string {
  if (total <= 0) {
    return '0%';
  }

  return `${Math.round((value / total) * 100)}%`;
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
        <div className="panel">正在加载仪表盘...</div>
      </AppShell>
    );
  }

  const overview = dashboard?.overview;
  const sourceHealth = dashboard?.source_health;
  const crawlCandidates = dashboard?.crawl_candidates;
  const activeTasks =
    (overview?.pending_crawl_runs ?? 0) +
    (overview?.running_crawl_runs ?? 0) +
    (overview?.pending_ai_reports ?? 0) +
    (overview?.running_ai_reports ?? 0);
  const attentionSources =
    (sourceHealth?.warning_sources ?? 0) +
    (sourceHealth?.failed_sources ?? 0) +
    (sourceHealth?.never_crawled_sources ?? 0);
  const healthyRate = formatPercent(
    sourceHealth?.healthy_sources ?? 0,
    sourceHealth?.active_sources ?? 0
  );
  const candidateStatusTotal =
    crawlCandidates?.by_status.reduce((sum, item) => sum + item.count, 0) ?? 0;
  const skippedCandidateTotal =
    crawlCandidates?.by_skip_reason.reduce((sum, item) => sum + item.count, 0) ??
    0;
  const workbenchItems: WorkbenchItem[] = [
    {
      label: '待复核与交付',
      value: overview?.reports ?? 0,
      helper: '进入报告工作台筛选“待老师复核”和“可直接导出”。',
      href: '/reports',
      tone: 'primary',
    },
    {
      label: '未读提醒',
      value: overview?.unread_notifications ?? 0,
      helper: '查看新报告、AI 完成、需重跑等提醒。',
      href: '/notifications',
      tone: overview?.unread_notifications ? 'warning' : 'neutral',
    },
    {
      label: 'AI 异常',
      value: overview?.failed_ai_reports ?? 0,
      helper: '失败或需重跑的成果应优先排查。',
      href: '/reports',
      tone: overview?.failed_ai_reports ? 'danger' : 'neutral',
    },
    {
      label: '来源需处理',
      value: attentionSources,
      helper: '检查失败、未抓取或质量不稳定的来源。',
      href: '/settings',
      tone: attentionSources ? 'warning' : 'neutral',
    },
  ];

  return (
    <AppShell>
      <div className="page-header">
        <h1>监测仪表盘</h1>
        <p>先处理报告交付，再查看来源健康和候选质量。</p>
      </div>

      {errorMessage && <p className="message-error">{errorMessage}</p>}

      <section className="dashboard-hero" aria-label="今日工作台">
        <div>
          <span className="dashboard-eyebrow">今日工作台</span>
          <h2>从“发现报告”到“交付成果”的运行概览</h2>
          <p>
            当前平台已接入 {overview?.think_tanks ?? 0} 家机构、
            {sourceHealth?.active_sources ?? 0} 个活跃来源，累计收录{' '}
            {overview?.reports ?? 0} 篇报告。
          </p>
        </div>

        <div className="dashboard-hero-actions">
          <Link href="/reports" className="button-primary">
            处理报告
          </Link>
          <Link href="/settings" className="button-secondary">
            查看来源
          </Link>
        </div>
      </section>

      <section className="dashboard-workbench" aria-label="优先处理事项">
        {workbenchItems.map((item) => (
          <Link
            href={item.href}
            className={`workbench-card workbench-card-${item.tone}`}
            key={item.label}
          >
            <span>{item.label}</span>
            <strong>{item.value}</strong>
            <small>{item.helper}</small>
          </Link>
        ))}
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>关键指标</h2>
            <p>用于快速判断平台是否在稳定监测、处理和提醒。</p>
          </div>
          <span className="badge badge-info">运行中任务 {activeTasks}</span>
        </div>

        <ul className="stats-grid">
          <li className="stat-card">
            已接入智库
            <span className="stat-value">
              {overview?.think_tanks ?? 0}
            </span>
          </li>

          <li className="stat-card">
            已配置来源
            <span className="stat-value">
              {overview?.sources ?? 0}
            </span>
          </li>

          <li className="stat-card">
            已收录报告
            <span className="stat-value">
              {overview?.reports ?? 0}
            </span>
          </li>

          <li className="stat-card">
            抓取任务
            <span className="stat-value">
              {(overview?.pending_crawl_runs ?? 0) +
                (overview?.running_crawl_runs ?? 0)}
            </span>
            <span className="muted">
              待执行 {overview?.pending_crawl_runs ?? 0} / 运行中{' '}
              {overview?.running_crawl_runs ?? 0}
            </span>
          </li>

          <li className="stat-card">
            AI 处理队列
            <span className="stat-value">
              {(overview?.pending_ai_reports ?? 0) +
                (overview?.running_ai_reports ?? 0)}
            </span>
            <span className="muted">
              失败 {overview?.failed_ai_reports ?? 0}
            </span>
          </li>

          <li className="stat-card">
            未读通知
            <span className="stat-value">
              {overview?.unread_notifications ?? 0}
            </span>
          </li>
        </ul>
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>来源健康</h2>
            <p>优先关注失败、未抓取和长期无有效候选的来源。</p>
          </div>
          <span className="badge badge-success">健康率 {healthyRate}</span>
        </div>

        <ul className="stats-grid">
          <li className="stat-card">
            活跃来源
            <span className="stat-value">
              {sourceHealth?.active_sources ?? 0}
            </span>
            <span className="muted">
              总计 {sourceHealth?.total_sources ?? 0}
            </span>
          </li>

          {Object.entries(sourceHealthLabels).map(([key, label]) => (
            <li className="stat-card" key={key}>
              {label}
              <span className="stat-value">
                {sourceHealth?.[key as SourceHealthMetricKey] ?? 0}
              </span>
            </li>
          ))}
        </ul>

        <h3>最近失败原因</h3>
        {sourceHealth?.recent_failures.length ? (
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
                {sourceHealth.recent_failures.map((failure) => (
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
        <div className="section-heading">
          <div>
            <h2>候选报告质量</h2>
            <p>用候选状态和跳过原因判断来源是否值得继续放行。</p>
          </div>
          <span className="badge">候选 {crawlCandidates?.total ?? 0}</span>
        </div>

        <div className="status-line">
          <span className="badge">
            全部 {crawlCandidates?.total ?? 0}
          </span>
          {crawlCandidates?.by_status.map((item) => (
            <span className="badge" key={item.code ?? item.label}>
              {item.label} {item.count}
            </span>
          ))}
        </div>

        <p className="muted">
          已分类候选 {candidateStatusTotal} 条，主要跳过记录{' '}
          {skippedCandidateTotal} 条。
        </p>

        <h3>主要跳过原因</h3>
        {crawlCandidates?.by_skip_reason.length ? (
          <div className="status-line">
            {crawlCandidates.by_skip_reason.map((item) => (
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
