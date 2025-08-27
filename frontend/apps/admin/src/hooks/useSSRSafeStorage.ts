/**
 * SSR-Safe Storage Hooks
 * Provides safe access to browser storage APIs with proper hydration handling
 */

import { useState, useEffect, useCallback } from 'react';

/**
 * SSR-safe localStorage hook
 * Returns the value, setter, and loading state
 * Prevents hydration mismatches by waiting for client-side hydration
 */
export function useLocalStorage<T>(
  key: string,
  defaultValue: T,
  options?: {
    serialize?: (value: T) => string;
    deserialize?: (value: string) => T;
  }
): [T, (value: T) => void, boolean] {
  const serialize = options?.serialize ?? JSON.stringify;
  const deserialize = options?.deserialize ?? JSON.parse;

  const [storedValue, setStoredValue] = useState<T>(defaultValue);
  const [isLoading, setIsLoading] = useState(true);

  // Load value from localStorage on client-side hydration
  useEffect(() => {
    if (typeof window === 'undefined') {
      setIsLoading(false);
      return;
    }

    try {
      const item = localStorage.getItem(key);
      if (item !== null) {
        setStoredValue(deserialize(item));
      }
    } catch (error) {
      console.warn(`Error reading localStorage key "${key}":`, error);
      setStoredValue(defaultValue);
    } finally {
      setIsLoading(false);
    }
  }, [key, defaultValue, deserialize]);

  // Update localStorage and state
  const setValue = useCallback((value: T) => {
    if (typeof window === 'undefined') {
      console.warn('Attempted to set localStorage on server side');
      return;
    }

    try {
      setStoredValue(value);
      localStorage.setItem(key, serialize(value));
    } catch (error) {
      console.warn(`Error setting localStorage key "${key}":`, error);
    }
  }, [key, serialize]);

  return [storedValue, setValue, isLoading];
}

/**
 * SSR-safe sessionStorage hook
 */
export function useSessionStorage<T>(
  key: string,
  defaultValue: T,
  options?: {
    serialize?: (value: T) => string;
    deserialize?: (value: string) => T;
  }
): [T, (value: T) => void, boolean] {
  const serialize = options?.serialize ?? JSON.stringify;
  const deserialize = options?.deserialize ?? JSON.parse;

  const [storedValue, setStoredValue] = useState<T>(defaultValue);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (typeof window === 'undefined') {
      setIsLoading(false);
      return;
    }

    try {
      const item = sessionStorage.getItem(key);
      if (item !== null) {
        setStoredValue(deserialize(item));
      }
    } catch (error) {
      console.warn(`Error reading sessionStorage key "${key}":`, error);
      setStoredValue(defaultValue);
    } finally {
      setIsLoading(false);
    }
  }, [key, defaultValue, deserialize]);

  const setValue = useCallback((value: T) => {
    if (typeof window === 'undefined') {
      console.warn('Attempted to set sessionStorage on server side');
      return;
    }

    try {
      setStoredValue(value);
      sessionStorage.setItem(key, serialize(value));
    } catch (error) {
      console.warn(`Error setting sessionStorage key "${key}":`, error);
    }
  }, [key, serialize]);

  return [storedValue, setValue, isLoading];
}

/**
 * Simple hook to check if we're on the client side
 * Useful for conditionally rendering client-only components
 */
export function useIsClient(): boolean {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  return isClient;
}

/**
 * Hook for safely accessing window object
 */
export function useWindow() {
  const isClient = useIsClient();
  return isClient ? window : undefined;
}

/**
 * SSR-safe cookie hook (for auth tokens)
 * This is more reliable for authentication than localStorage
 */
export function useCookieValue(
  name: string,
  defaultValue: string = ''
): [string, boolean] {
  const [value, setValue] = useState<string>(defaultValue);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (typeof document === 'undefined') {
      setIsLoading(false);
      return;
    }

    try {
      const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith(`${name}=`))
        ?.split('=')[1] || defaultValue;
      
      setValue(cookieValue);
    } catch (error) {
      console.warn(`Error reading cookie "${name}":`, error);
      setValue(defaultValue);
    } finally {
      setIsLoading(false);
    }
  }, [name, defaultValue]);

  return [value, isLoading];
}

/**
 * DEPRECATED: Use useSecureAuth hook instead
 * This hook had security vulnerabilities with localStorage fallback
 */
export function useAuthToken(): [string | null, (token: string | null) => void, boolean] {
  console.warn('useAuthToken is deprecated. Use useSecureAuth hook instead.');
  
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (typeof window === 'undefined') {
      setIsLoading(false);
      return;
    }

    try {
      // Only try cookie (SSR-safe) - removed localStorage fallback for security
      const cookieToken = document.cookie
        .split('; ')
        .find(row => row.startsWith('auth-token='))
        ?.split('=')[1];

      setToken(cookieToken || null);
    } catch (error) {
      console.warn('Error reading auth token:', error);
      setToken(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const updateToken = useCallback((newToken: string | null) => {
    console.warn('updateToken is deprecated. Use useSecureAuth login/logout methods instead.');
    setToken(newToken);
    
    if (typeof window === 'undefined') return;

    try {
      if (newToken) {
        // Only store in cookie - removed localStorage for security
        document.cookie = `auth-token=${newToken}; path=/; max-age=${7 * 24 * 60 * 60}; samesite=strict`;
      } else {
        // Clear cookie
        document.cookie = 'auth-token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
        
        // SECURITY: No localStorage tokens to remove - using secure cookies only
      }
    } catch (error) {
      console.warn('Error updating auth token:', error);
    }
  }, []);

  return [token, updateToken, isLoading];
}

/**
 * Hook to prevent rendering until client-side hydration is complete
 * Useful for components that must be client-only
 */
export function useClientOnly() {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  return isClient;
}