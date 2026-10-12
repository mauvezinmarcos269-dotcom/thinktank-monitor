'use client';

import { useState } from 'react';

import { triggerSourceCrawl } from '@/lib/institution';

type UseSourceCrawlActionsParams = {
  loadSettings: () => Promise<void>;
  setErrorMessage: (message: string | null) => void;
  setSuccessMessage: (message: string | null) => void;
};

export function useSourceCrawlActions({
  loadSettings,
  setErrorMessage,
  setSuccessMessage,
}: UseSourceCrawlActionsParams) {
  const [crawlingSourceId, setCrawlingSourceId] = useState<number | null>(null);

  async function handleTriggerCrawl(sourceId: number) {
    setErrorMessage(null);
    setSuccessMessage(null);
    setCrawlingSourceId(sourceId);

    try {
      const response = await triggerSourceCrawl(sourceId);
      setSuccessMessage(`${response.message} 任务 ID：${response.task_id}`);
      await loadSettings();
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '抓取任务提交失败。'
      );
    } finally {
      setCrawlingSourceId(null);
    }
  }

  return {
    crawlingSourceId,
    handleTriggerCrawl,
  };
}
