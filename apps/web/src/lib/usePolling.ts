import { useState, useEffect, useRef, useCallback } from 'react';

export interface PollingOptions {
  intervalMs?: number;
  backgroundIntervalMs?: number;
  enabled?: boolean;
}

export interface PollingState<T> {
  data: T | null;
  latencyMs: number | null;
  pollCount: number;
  error: Error | null;
  isReconnecting: boolean;
  refetch: () => Promise<void>;
}

export function usePolling<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  options: PollingOptions = {}
): PollingState<T> {
  const {
    intervalMs = 2000,
    backgroundIntervalMs = 5000,
    enabled = true,
  } = options;

  const [data, setData] = useState<T | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [pollCount, setPollCount] = useState<number>(0);
  const [error, setError] = useState<Error | null>(null);
  const [isReconnecting, setIsReconnecting] = useState<boolean>(false);

  const consecutiveFailuresRef = useRef<number>(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const isMountedRef = useRef<boolean>(true);

  const getEffectiveInterval = useCallback(() => {
    const isHidden = typeof document !== 'undefined' && document.visibilityState === 'hidden';
    const base = isHidden ? backgroundIntervalMs : intervalMs;

    if (consecutiveFailuresRef.current > 0) {
      // Exponential backoff up to 10 seconds
      return Math.min(base * Math.pow(1.5, consecutiveFailuresRef.current), 10000);
    }
    return base;
  }, [intervalMs, backgroundIntervalMs]);

  const executePoll = useCallback(async () => {
    if (!enabled) return;

    // Abort previous in-flight request if still pending
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const start = performance.now();
    try {
      const result = await fetcher(controller.signal);
      const elapsed = Math.round(performance.now() - start);

      if (isMountedRef.current) {
        setData(result);
        setLatencyMs(elapsed);
        setPollCount((prev) => prev + 1);
        setError(null);
        setIsReconnecting(false);
        consecutiveFailuresRef.current = 0;
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        // Request was aborted deliberately — ignore
        return;
      }

      if (isMountedRef.current) {
        consecutiveFailuresRef.current += 1;
        setError(err instanceof Error ? err : new Error(String(err)));
        setIsReconnecting(true);
      }
    } finally {
      if (isMountedRef.current && enabled) {
        const nextInterval = getEffectiveInterval();
        timerRef.current = setTimeout(executePoll, nextInterval);
      }
    }
  }, [fetcher, enabled, getEffectiveInterval]);

  useEffect(() => {
    isMountedRef.current = true;
    executePoll();

    const handleVisibilityChange = () => {
      // Clear current timer and re-evaluate immediately when tab returns to focus
      if (document.visibilityState === 'visible') {
        if (timerRef.current) clearTimeout(timerRef.current);
        executePoll();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      isMountedRef.current = false;
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      if (timerRef.current) clearTimeout(timerRef.current);
      if (abortControllerRef.current) abortControllerRef.current.abort();
    };
  }, [executePoll]);

  return {
    data,
    latencyMs,
    pollCount,
    error,
    isReconnecting,
    refetch: executePoll,
  };
}
