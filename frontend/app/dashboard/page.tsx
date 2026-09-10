'use client';

import { useEffect, useState } from 'react';
import { AppShell } from '@/components/app-shell';
import { apiRequest } from '@/lib/api';

interface ThinkTankStats {
  think_tanks?: number;
  total_think_tanks?: number;
}

type ReportsResponse =
  | {
      total?: number;
      items?: unknown[];
    }
  | unknown[];

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);

  const [stats, setStats] = useState({
    thinkTanks: 0,
    reports: 0,
    tasks: 0,
  });

  useEffect(() => {
    async function loadDashboard() {
      try {
        const tanks =
          await apiRequest<ThinkTankStats>(
            '/api/v1/think-tanks/statistics'
          );

        const reports =
          await apiRequest<ReportsResponse>(
            '/api/v1/reports'
          );

        setStats({
          thinkTanks:
            tanks.think_tanks ??
            tanks.total_think_tanks ??
            0,

          reports:
            Array.isArray(reports)
              ? reports.length
              : reports.total ??
                reports.items?.length ??
                0,

          tasks: 0,
        });
      } catch (error) {
        console.error(
          '[Dashboard] 数据加载失败:',
          error
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

      <section className="panel">
        <h2>系统概览</h2>

        <ul className="stats-grid">
          <li className="stat-card">
            已接入智库
            <span className="stat-value">{stats.thinkTanks}</span>
          </li>

          <li className="stat-card">
            已收录报告
            <span className="stat-value">{stats.reports}</span>
          </li>

          <li className="stat-card">
            待处理采集任务
            <span className="stat-value">{stats.tasks}</span>
          </li>
        </ul>
      </section>
    </AppShell>
  );
}
