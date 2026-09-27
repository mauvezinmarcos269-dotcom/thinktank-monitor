'use client';

import { type SourceHealth } from '@/lib/institution';
import {
  priorityTierLabels,
  regionFocusLabels,
} from '@/lib/status';

type ReviewQueueItem = {
  source: SourceHealth;
  reason: string;
};

type ReviewQueuePanelProps = {
  reviewQueue: ReviewQueueItem[];
  loading: boolean;
  healthBadgeClasses: Record<SourceHealth['health_status'], string>;
  getLatestRun: (
    source: SourceHealth
  ) => SourceHealth['recent_crawl_runs'][number] | null;
  getSaveRate: (run: SourceHealth['recent_crawl_runs'][number]) => number;
  formatDateTime: (value: string | null) => string;
};

export function ReviewQueuePanel({
  reviewQueue,
  loading,
  healthBadgeClasses,
  getLatestRun,
  getSaveRate,
  formatDateTime,
}: ReviewQueuePanelProps) {
  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <h2>候选验收重点</h2>
          <p>这些来源需要先人工看候选质量，再决定是否进入自动入库。</p>
        </div>
      </div>

      {reviewQueue.length === 0 && !loading ? (
        <p>当前没有需要优先人工复核的来源。</p>
      ) : (
        <ul className="review-queue">
          {reviewQueue.map(({ source, reason }) => {
            const latestRun = getLatestRun(source);

            return (
              <li key={source.id}>
                <div>
                  <strong>{source.think_tank_name}</strong>
                  <span className="muted">
                    {' '}
                    / {priorityTierLabels[source.think_tank_priority_tier]} /{' '}
                    {regionFocusLabels[source.think_tank_region_focus]}
                  </span>
                </div>
                <span className={healthBadgeClasses[source.health_status]}>
                  {reason}
                </span>
                <dl>
                  <div>
                    <dt>最近发现</dt>
                    <dd>{latestRun?.found_count ?? 0}</dd>
                  </div>
                  <div>
                    <dt>最近入库</dt>
                    <dd>{latestRun?.saved_count ?? 0}</dd>
                  </div>
                  <div>
                    <dt>保存率</dt>
                    <dd>
                      {latestRun ? `${getSaveRate(latestRun)}%` : '暂无'}
                    </dd>
                  </div>
                  <div>
                    <dt>最近抓取</dt>
                    <dd>{formatDateTime(source.last_crawled_at)}</dd>
                  </div>
                </dl>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
