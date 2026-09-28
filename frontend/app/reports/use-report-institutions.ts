'use client';

import { type Dispatch, type SetStateAction, useEffect, useState } from 'react';

import {
  fetchSources,
  fetchThinkTanks,
  type Source,
  type ThinkTank,
} from '@/lib/institution';

export function useReportInstitutions(
  setListError: Dispatch<SetStateAction<string | null>>
) {
  const [thinkTanks, setThinkTanks] = useState<ThinkTank[]>([]);
  const [sources, setSources] = useState<Source[]>([]);

  useEffect(() => {
    Promise.all([
      fetchThinkTanks(),
      fetchSources(),
    ])
      .then(([nextThinkTanks, nextSources]) => {
        setThinkTanks(nextThinkTanks);
        setSources(nextSources);
      })
      .catch((err: Error) => setListError(err.message));
  }, [setListError]);

  return {
    thinkTanks,
    sources,
  };
}
