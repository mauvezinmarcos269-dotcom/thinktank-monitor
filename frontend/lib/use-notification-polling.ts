'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import { getAccessToken } from '@/lib/auth';

const POLL_INTERVAL_MS = 30_000;
const REQUEST_TIMEOUT_MS = 15_000;

export function useNotificationPolling<T>(
  load: (signal: AbortSignal) => Promise<T>,
  { enabled = true, paused = false } = {}
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<string | null>(null);
  const request = useRef<AbortController | null>(null);

  const cancel = useCallback(() => {
    request.current?.abort();
    request.current = null;
  }, []);

  const refresh = useCallback(
    async (background = false) => {
      if (!enabled || paused || document.hidden || request.current) return;
      if (!getAccessToken()) {
        setLoading(false);
        return;
      }

      const controller = new AbortController();
      request.current = controller;
      let timedOut = false;
      const timeout = window.setTimeout(() => {
        timedOut = true;
        controller.abort();
      }, REQUEST_TIMEOUT_MS);
      if (!background) setLoading(true);

      try {
        const result = await load(controller.signal);
        if (request.current === controller && !controller.signal.aborted) {
          setData(result);
          setError(null);
        }
      } catch (cause) {
        if (request.current === controller && (!controller.signal.aborted || timedOut)) {
          setError(
            timedOut ? '通知刷新超时，保留上次结果。' : cause instanceof Error ? cause.message : '通知刷新失败。'
          );
        }
      } finally {
        window.clearTimeout(timeout);
        if (request.current === controller) {
          request.current = null;
          setLoading(false);
        }
      }
    },
    [enabled, load, paused]
  );

  useEffect(() => {
    setData(null);
    setError(null);
  }, [load]);

  useEffect(() => {
    if (!enabled || paused) {
      setLoading(false);
      return;
    }

    void refresh();
    const timer = window.setInterval(() => void refresh(true), POLL_INTERVAL_MS);
    const handleFocus = () => void refresh(true);
    const handleVisibility = () => {
      if (document.hidden) {
        cancel();
        setLoading(false);
      } else {
        void refresh(true);
      }
    };
    const handleUpdated = () => {
      // A pre-mutation response must not replace the new read state or count.
      cancel();
      void refresh(true);
    };
    window.addEventListener('focus', handleFocus);
    document.addEventListener('visibilitychange', handleVisibility);
    window.addEventListener('thinktank:notifications-updated', handleUpdated);

    return () => {
      window.clearInterval(timer);
      window.removeEventListener('focus', handleFocus);
      document.removeEventListener('visibilitychange', handleVisibility);
      window.removeEventListener('thinktank:notifications-updated', handleUpdated);
      cancel();
    };
  }, [cancel, enabled, paused, refresh]);

  return { data, setData, loading, error, refresh, cancel };
}
