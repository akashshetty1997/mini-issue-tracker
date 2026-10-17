"use client";

import { useCallback, useEffect, useRef } from "react";

/** Returns a function that calls `callback` only after `delayMs` without further calls. */
export function useDebouncedCallback<Args extends unknown[]>(
  callback: (...args: Args) => void,
  delayMs: number,
) {
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const latestCallback = useRef(callback);

  useEffect(() => {
    latestCallback.current = callback;
  }, [callback]);

  useEffect(() => () => clearTimeout(timer.current), []);

  return useCallback(
    (...args: Args) => {
      clearTimeout(timer.current);
      timer.current = setTimeout(() => latestCallback.current(...args), delayMs);
    },
    [delayMs],
  );
}
