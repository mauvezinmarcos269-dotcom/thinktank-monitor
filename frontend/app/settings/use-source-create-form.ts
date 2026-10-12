'use client';

import { type FormEvent, useEffect, useState } from 'react';

import {
  createThinkTankSource,
  triggerSourceCrawl,
  type SourceCreateInput,
  type ThinkTank,
} from '@/lib/institution';

import { crawlableSourceTypes } from './settings-page-utils';

type UseSourceCreateFormParams = {
  thinkTanks: ThinkTank[];
  missingSources: ThinkTank[];
  loadSettings: () => Promise<void>;
  setErrorMessage: (message: string | null) => void;
  setSuccessMessage: (message: string | null) => void;
};

export function useSourceCreateForm({
  thinkTanks,
  missingSources,
  loadSettings,
  setErrorMessage,
  setSuccessMessage,
}: UseSourceCreateFormParams) {
  const [selectedThinkTankId, setSelectedThinkTankId] = useState('');
  const [sourceType, setSourceType] =
    useState<SourceCreateInput['source_type']>('rss');
  const [sourceUrl, setSourceUrl] = useState('');
  const [crawlFrequencyMinutes, setCrawlFrequencyMinutes] = useState(1440);
  const [crawlAfterCreate, setCrawlAfterCreate] = useState(true);
  const [submittingSource, setSubmittingSource] = useState(false);

  useEffect(() => {
    setSelectedThinkTankId((current) => {
      if (current) {
        return current;
      }

      const firstMissingSource = missingSources[0];
      const firstThinkTank = thinkTanks[0];
      return String(firstMissingSource?.id ?? firstThinkTank?.id ?? '');
    });
  }, [missingSources, thinkTanks]);

  async function handleCreateSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    const thinkTankId = Number(selectedThinkTankId);

    if (!thinkTankId) {
      setErrorMessage('请选择机构。');
      return;
    }

    if (!sourceUrl.trim()) {
      setErrorMessage('请输入来源 URL。');
      return;
    }

    setSubmittingSource(true);

    try {
      const createdSource = await createThinkTankSource(thinkTankId, {
        source_type: sourceType,
        url: sourceUrl.trim(),
        crawl_frequency_minutes: crawlFrequencyMinutes,
        is_active: true,
      });

      if (crawlAfterCreate && crawlableSourceTypes.has(sourceType)) {
        const response = await triggerSourceCrawl(createdSource.id);
        setSuccessMessage(`${response.message} 任务 ID：${response.task_id}`);
      } else if (crawlAfterCreate) {
        setSuccessMessage('来源已添加；该类型暂不支持立即试抓。');
      } else {
        setSuccessMessage('来源已添加。');
      }

      setSourceUrl('');
      await loadSettings();
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '来源添加失败。'
      );
    } finally {
      setSubmittingSource(false);
    }
  }

  return {
    selectedThinkTankId,
    sourceType,
    sourceUrl,
    crawlFrequencyMinutes,
    crawlAfterCreate,
    submittingSource,
    setSelectedThinkTankId,
    setSourceType,
    setSourceUrl,
    setCrawlFrequencyMinutes,
    setCrawlAfterCreate,
    handleCreateSource,
  };
}
