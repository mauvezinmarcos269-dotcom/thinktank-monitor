'use client';

import { useMemo } from 'react';

import { type Source, type ThinkTank } from '@/lib/institution';
import { type Report } from '@/lib/report';
import {
  reportAIStatusLabels,
  reportReviewStatusLabels,
} from '@/lib/status';

import { getDocumentType } from './report-page-utils';

export function useReportPageDerived({
  selected,
  sources,
  thinkTanks,
  thinkTankFilter,
}: {
  selected: Report | null;
  sources: Source[];
  thinkTanks: ThinkTank[];
  thinkTankFilter: number | '';
}) {
  const sourceOptions = useMemo(
    () =>
      thinkTankFilter
        ? sources.filter((source) => source.think_tank_id === thinkTankFilter)
        : sources,
    [sources, thinkTankFilter]
  );
  const sourceById = useMemo(
    () => new Map(sources.map((source) => [source.id, source])),
    [sources]
  );
  const thinkTankById = useMemo(
    () => new Map(thinkTanks.map((thinkTank) => [thinkTank.id, thinkTank])),
    [thinkTanks]
  );
  const selectedDocumentType = selected ? getDocumentType(selected) : null;
  const selectedSource = selected ? sourceById.get(selected.source_id) : null;
  const selectedThinkTank = selectedSource
    ? thinkTankById.get(selectedSource.think_tank_id)
    : null;
  const adminDetailsSummary =
    selected && selectedDocumentType
      ? [
          reportReviewStatusLabels[selected.review_status] ??
            selected.review_status,
          reportAIStatusLabels[selected.ai_status] ?? selected.ai_status,
          selectedDocumentType.label,
        ].join(' · ')
      : '暂无报告';
  const aiActionLabel =
    selected?.ai_status === 'skipped'
      ? '进入 AI 处理'
      : '重试 AI 处理';

  return {
    sourceOptions,
    sourceById,
    thinkTankById,
    selectedDocumentType,
    selectedSource,
    selectedThinkTank,
    adminDetailsSummary,
    aiActionLabel,
  };
}
