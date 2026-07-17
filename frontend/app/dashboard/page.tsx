import { AppShell } from '@/components/app-shell';

export default function DashboardPage() {
  return (
    <AppShell>
      <h1>监测仪表盘</h1>
      <p>欢迎使用 ThinkTank Monitor。</p>

      <section>
        <h2>系统概览</h2>
        <ul>
          <li>已接入智库：0</li>
          <li>已收录报告：0</li>
          <li>待处理采集任务：0</li>
        </ul>
      </section>
    </AppShell>
  );
}