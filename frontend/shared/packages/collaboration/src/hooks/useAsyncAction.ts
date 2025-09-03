import { useState, useCallback } from 'react';

interface UseAsyncActionOptions {
  onSuccess?: () => void;
  onError?: (error: Error) => void;
}

export const useAsyncAction = (
  action: () => Promise<void>,
  options: UseAsyncActionOptions = {}
) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const execute = useCallback(async () => {
    if (loading) return;

    setLoading(true);
    setError(null);

    try {
      await action();
      options.onSuccess?.();
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      options.onError?.(error);
    } finally {
      setLoading(false);
    }
  }, [action, loading, options]);

  const reset = useCallback(() => {
    setError(null);
    setLoading(false);
  }, []);

  return {
    execute,
    loading,
    error,
    reset,
  };
};
