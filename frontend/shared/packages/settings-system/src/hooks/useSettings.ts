import { useState, useCallback, useEffect } from 'react';
import { SettingsData, SettingsContext } from '../types';

export interface UseSettingsOptions {
  initialData?: SettingsData;
  persistKey?: string;
  autoSave?: boolean;
  saveDelay?: number;
}

export function useSettings(options: UseSettingsOptions = {}): SettingsContext {
  const { initialData = {}, persistKey, autoSave = false, saveDelay = 500 } = options;

  const [data, setData] = useState<SettingsData>(() => {
    if (persistKey && typeof window !== 'undefined') {
      const stored = localStorage.getItem(persistKey);
      if (stored) {
        try {
          return { ...initialData, ...JSON.parse(stored) };
        } catch {
          return initialData;
        }
      }
    }
    return initialData;
  });

  const [isLoading, setIsLoading] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saveTimeout, setSaveTimeout] = useState<NodeJS.Timeout | null>(null);

  const updateSetting = useCallback(
    (path: string, value: any) => {
      setData((prev) => {
        const keys = path.split('.');
        const newData = { ...prev };
        let current = newData;

        for (let i = 0; i < keys.length - 1; i++) {
          const key = keys[i];
          if (!current[key] || typeof current[key] !== 'object') {
            current[key] = {};
          }
          current[key] = { ...current[key] };
          current = current[key];
        }

        current[keys[keys.length - 1]] = value;
        return newData;
      });

      setIsDirty(true);

      // Clear any existing error for this path
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[path];
        return newErrors;
      });

      // Auto-save with debouncing
      if (autoSave) {
        if (saveTimeout) {
          clearTimeout(saveTimeout);
        }
        const timeout = setTimeout(() => {
          saveSettings();
        }, saveDelay);
        setSaveTimeout(timeout);
      }
    },
    [autoSave, saveDelay, saveTimeout]
  );

  const resetSection = useCallback((sectionId: string) => {
    setData((prev) => {
      const newData = { ...prev };
      delete newData[sectionId];
      return newData;
    });
    setIsDirty(true);
  }, []);

  const saveSettings = useCallback(async (): Promise<boolean> => {
    setIsLoading(true);
    setErrors({});

    try {
      // Persist to localStorage if key provided
      if (persistKey && typeof window !== 'undefined') {
        localStorage.setItem(persistKey, JSON.stringify(data));
      }

      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 500));

      setIsDirty(false);
      setIsLoading(false);
      return true;
    } catch (error) {
      setErrors({ general: 'Failed to save settings' });
      setIsLoading(false);
      return false;
    }
  }, [data, persistKey]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (saveTimeout) {
        clearTimeout(saveTimeout);
      }
    };
  }, [saveTimeout]);

  return {
    data,
    updateSetting,
    resetSection,
    saveSettings,
    isLoading,
    isDirty,
    errors,
  };
}
