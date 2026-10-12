'use client';

import { useCallback, useEffect, useState } from 'react';

import {
  fetchInstitutionStats,
  fetchMissingSourceThinkTanks,
  fetchSourceHealth,
  fetchThinkTanks,
  type InstitutionStats,
  type SourceHealth,
  type SourceHealthSummary,
  type ThinkTank,
} from '@/lib/institution';

import { sortSourceHealth } from './settings-page-utils';

export function useSettingsData() {
  const [stats, setStats] = useState<InstitutionStats | null>(null);
  const [thinkTanks, setThinkTanks] = useState<ThinkTank[]>([]);
  const [sourceHealth, setSourceHealth] = useState<SourceHealth[]>([]);
  const [sourceHealthSummary, setSourceHealthSummary] =
    useState<SourceHealthSummary | null>(null);
  const [missingSources, setMissingSources] = useState<ThinkTank[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const loadSettings = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);

    try {
      const [statsData, thinkTanksData, missingSourceData, sourceHealthData] =
        await Promise.all([
          fetchInstitutionStats(),
          fetchThinkTanks(),
          fetchMissingSourceThinkTanks(),
          fetchSourceHealth(),
        ]);

      setStats(statsData);
      setThinkTanks(thinkTanksData);
      setMissingSources(missingSourceData);
      setSourceHealth(sortSourceHealth(sourceHealthData.items));
      setSourceHealthSummary(sourceHealthData.summary);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '系统设置加载失败。'
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  return {
    stats,
    thinkTanks,
    sourceHealth,
    sourceHealthSummary,
    missingSources,
    loading,
    errorMessage,
    successMessage,
    setErrorMessage,
    setSuccessMessage,
    loadSettings,
  };
}
