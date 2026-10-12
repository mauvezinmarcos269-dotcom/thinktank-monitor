'use client';

import { useMemo, useState } from 'react';

import { type SourceHealth } from '@/lib/institution';

import {
  getSourceHealthFilterCounts,
  getSourceReviewReason,
  matchesSourceHealthFilter,
  sourceHealthFilterOptions,
  type SourceHealthFilter,
} from './settings-page-utils';

export function useSourceHealthFilters(sourceHealth: SourceHealth[]) {
  const [sourceHealthFilter, setSourceHealthFilter] = useState<SourceHealthFilter>('all');
  const [sourceHealthSearch, setSourceHealthSearch] = useState('');

  const reviewQueue = useMemo(() => {
    return sourceHealth
      .map((source) => ({
        source,
        reason: getSourceReviewReason(source),
      }))
      .filter((item): item is { source: SourceHealth; reason: string } => item.reason !== null)
      .slice(0, 8);
  }, [sourceHealth]);

  const sourceHealthFilterCounts = useMemo(() => getSourceHealthFilterCounts(sourceHealth), [sourceHealth]);

  const filteredSourceHealth = useMemo(() => {
    const keyword = sourceHealthSearch.trim().toLowerCase();

    return sourceHealth.filter((source) => {
      if (!matchesSourceHealthFilter(source, sourceHealthFilter)) {
        return false;
      }

      if (!keyword) {
        return true;
      }

      return [
        String(source.id),
        source.think_tank_name,
        source.think_tank_key,
        source.think_tank_country,
        source.url,
        source.health_reason,
        source.diagnosis_label,
        source.diagnosis_advice,
        source.rollout_advice,
      ]
        .join(' ')
        .toLowerCase()
        .includes(keyword);
    });
  }, [sourceHealth, sourceHealthFilter, sourceHealthSearch]);

  const activeSourceHealthFilterLabel =
    sourceHealthFilterOptions.find((option) => option.value === sourceHealthFilter)?.label ?? '全部';

  function resetSourceHealthFilters() {
    setSourceHealthFilter('all');
    setSourceHealthSearch('');
  }

  return {
    sourceHealthFilter,
    setSourceHealthFilter,
    sourceHealthSearch,
    setSourceHealthSearch,
    reviewQueue,
    sourceHealthFilterCounts,
    filteredSourceHealth,
    activeSourceHealthFilterLabel,
    resetSourceHealthFilters,
  };
}
