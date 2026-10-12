'use client';

import {
  type InstitutionStats,
  type SourceHealthSummary,
} from '@/lib/institution';

type SettingsOverviewPanelsProps = {
  stats: InstitutionStats | null;
  sourceHealthSummary: SourceHealthSummary | null;
};

export function SettingsOverviewPanels({
  stats,
  sourceHealthSummary,
}: SettingsOverviewPanelsProps) {
  return (
    <>
      {stats ? (
        <section className="panel">
          <div className="section-heading">
            <div>
              <h2>来源配置概览</h2>
              <p>用于判断监测网络是否覆盖了重点智库和机构。</p>
            </div>
          </div>

          <ul className="stats-grid">
            <li className="stat-card">
              机构总数
              <span className="stat-value">{stats.total_think_tanks}</span>
            </li>
            <li className="stat-card">
              重点机构
              <span className="stat-value">{stats.key_think_tanks}</span>
            </li>
            <li className="stat-card">
              来源总数
              <span className="stat-value">{stats.total_sources}</span>
            </li>
            <li className="stat-card">
              启用来源
              <span className="stat-value">{stats.active_sources}</span>
            </li>
            <li className="stat-card">
              待配置来源机构
              <span className="stat-value">{stats.missing_active_sources}</span>
            </li>
          </ul>
        </section>
      ) : null}

      {sourceHealthSummary ? (
        <section className="panel">
          <div className="section-heading">
            <div>
              <h2>来源健康概览</h2>
              <p>优先处理失败、未抓取和需关注来源，减少漏报和噪声。</p>
            </div>
          </div>

          <ul className="stats-grid">
            <li className="stat-card">
              正常来源
              <span className="stat-value">
                {sourceHealthSummary.healthy_sources}
              </span>
            </li>
            <li className="stat-card">
              需关注
              <span className="stat-value">
                {sourceHealthSummary.warning_sources}
              </span>
            </li>
            <li className="stat-card">
              抓取失败
              <span className="stat-value">
                {sourceHealthSummary.failed_sources}
              </span>
            </li>
            <li className="stat-card">
              未抓取
              <span className="stat-value">
                {sourceHealthSummary.never_crawled_sources}
              </span>
            </li>
            <li className="stat-card">
              停用来源
              <span className="stat-value">
                {sourceHealthSummary.disabled_sources}
              </span>
            </li>
          </ul>
        </section>
      ) : null}
    </>
  );
}
