'use client';

import { type FormEvent } from 'react';

import { type SourceCreateInput, type ThinkTank } from '@/lib/institution';

type SourceTypeOption = {
  value: SourceCreateInput['source_type'];
  label: string;
};

type SourceCreateFormProps = {
  thinkTanks: ThinkTank[];
  selectedThinkTankId: string;
  sourceType: SourceCreateInput['source_type'];
  sourceUrl: string;
  crawlFrequencyMinutes: number;
  crawlAfterCreate: boolean;
  submittingSource: boolean;
  sourceTypeOptions: SourceTypeOption[];
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onThinkTankChange: (value: string) => void;
  onSourceTypeChange: (value: SourceCreateInput['source_type']) => void;
  onSourceUrlChange: (value: string) => void;
  onCrawlFrequencyChange: (value: number) => void;
  onCrawlAfterCreateChange: (value: boolean) => void;
};

export function SourceCreateForm({
  thinkTanks,
  selectedThinkTankId,
  sourceType,
  sourceUrl,
  crawlFrequencyMinutes,
  crawlAfterCreate,
  submittingSource,
  sourceTypeOptions,
  onSubmit,
  onThinkTankChange,
  onSourceTypeChange,
  onSourceUrlChange,
  onCrawlFrequencyChange,
  onCrawlAfterCreateChange,
}: SourceCreateFormProps) {
  return (
    <form className="form-grid" onSubmit={onSubmit}>
      <div className="form-field">
        <label htmlFor="think-tank-id">机构</label>
        <select
          id="think-tank-id"
          value={selectedThinkTankId}
          onChange={(event) => onThinkTankChange(event.target.value)}
          disabled={submittingSource}
          required
        >
          <option value="">请选择机构</option>
          {thinkTanks.map((thinkTank) => (
            <option key={thinkTank.id} value={thinkTank.id}>
              {thinkTank.name} / {thinkTank.country}
            </option>
          ))}
        </select>
      </div>

      <div className="form-field">
        <label htmlFor="source-type">来源类型</label>
        <select
          id="source-type"
          value={sourceType}
          onChange={(event) =>
            onSourceTypeChange(
              event.target.value as SourceCreateInput['source_type']
            )
          }
          disabled={submittingSource}
        >
          {sourceTypeOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <div className="form-field">
        <label htmlFor="source-url">URL</label>
        <input
          id="source-url"
          type="url"
          value={sourceUrl}
          onChange={(event) => onSourceUrlChange(event.target.value)}
          placeholder="https://example.org/feed/"
          disabled={submittingSource}
          required
        />
      </div>

      <div className="form-field">
        <label htmlFor="crawl-frequency">抓取频率（分钟）</label>
        <input
          id="crawl-frequency"
          type="number"
          min={5}
          max={43200}
          value={crawlFrequencyMinutes}
          onChange={(event) =>
            onCrawlFrequencyChange(Number(event.target.value))
          }
          disabled={submittingSource}
        />
      </div>

      <div className="form-field">
        <label htmlFor="crawl-after-create">
          <input
            id="crawl-after-create"
            type="checkbox"
            checked={crawlAfterCreate}
            onChange={(event) =>
              onCrawlAfterCreateChange(event.target.checked)
            }
            disabled={submittingSource}
          />
          添加后立即试抓
        </label>
      </div>

      <button type="submit" disabled={submittingSource}>
        {submittingSource ? '正在提交……' : '添加来源'}
      </button>
    </form>
  );
}
