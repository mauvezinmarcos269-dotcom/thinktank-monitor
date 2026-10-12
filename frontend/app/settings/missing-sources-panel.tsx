'use client';

import { type ThinkTank } from '@/lib/institution';
import { priorityTierLabels } from '@/lib/status';

type MissingSourcesPanelProps = {
  missingSources: ThinkTank[];
  loading: boolean;
};

export function MissingSourcesPanel({
  missingSources,
  loading,
}: MissingSourcesPanelProps) {
  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <h2>待配置来源机构</h2>
          <p>这些机构已在库中，但还没有启用的自动监测入口。</p>
        </div>
      </div>

      {missingSources.length === 0 && !loading ? (
        <p>所有启用机构都已有 active source。</p>
      ) : (
        <ul>
          {missingSources.map((thinkTank) => (
            <li key={thinkTank.id}>
              <strong>{thinkTank.name}</strong>
              {thinkTank.name_en ? ` / ${thinkTank.name_en}` : ''}
              {' - '}
              {thinkTank.country}
              {' - '}
              {priorityTierLabels[thinkTank.priority_tier]}
              {' - '}
              {thinkTank.is_verified ? '已校对' : '待校对'}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
