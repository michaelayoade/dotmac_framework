/**
 * Global Test Setup
 * Configures testing environment and global mocks
 */

import 'jest-canvas-mock';
import 'fake-indexeddb/auto';
import { TextEncoder, TextDecoder } from 'util';

// Global polyfills for Node.js test environment
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder as any;

// Mock Web APIs not available in Node.js
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock IntersectionObserver
global.IntersectionObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock ResizeObserver
global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock PerformanceObserver
global.PerformanceObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock Performance API
Object.defineProperty(global.performance, 'mark', {
  writable: true,
  value: jest.fn(),
});

Object.defineProperty(global.performance, 'measure', {
  writable: true,
  value: jest.fn(),
});

Object.defineProperty(global.performance, 'getEntriesByName', {
  writable: true,
  value: jest.fn().mockReturnValue([{ duration: 100 }]),
});

Object.defineProperty(global.performance, 'getEntriesByType', {
  writable: true,
  value: jest.fn().mockReturnValue([]),
});

Object.defineProperty(global.performance, 'timeOrigin', {
  writable: true,
  value: Date.now(),
});

// Mock Navigator API extensions
Object.defineProperty(navigator, 'onLine', {
  writable: true,
  value: true,
});

Object.defineProperty(navigator, 'connection', {
  writable: true,
  value: {
    effectiveType: '4g',
    downlink: 10,
    rtt: 50,
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
  },
});

Object.defineProperty(navigator, 'deviceMemory', {
  writable: true,
  value: 8,
});

// Mock Notification API
global.Notification = jest.fn().mockImplementation(() => ({
  permission: 'granted',
  requestPermission: jest.fn().mockResolvedValue('granted'),
})) as any;

Object.defineProperty(Notification, 'permission', {
  writable: true,
  value: 'granted',
});

// Mock ServiceWorker
Object.defineProperty(navigator, 'serviceWorker', {
  writable: true,
  value: {
    register: jest.fn().mockResolvedValue({}),
    ready: Promise.resolve({}),
    controller: null,
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
  },
});

// Mock Geolocation API
Object.defineProperty(navigator, 'geolocation', {
  writable: true,
  value: {
    getCurrentPosition: jest.fn().mockImplementation((success) => {
      success({
        coords: {
          latitude: 40.7128,
          longitude: -74.0060,
          accuracy: 100,
        },
        timestamp: Date.now(),
      });
    }),
    watchPosition: jest.fn(),
    clearWatch: jest.fn(),
  },
});

// Mock UserAgent Camera API
Object.defineProperty(navigator, 'mediaDevices', {
  writable: true,
  value: {
    getUserMedia: jest.fn().mockResolvedValue({
      getVideoTracks: () => [{
        stop: jest.fn(),
        getSettings: () => ({ width: 640, height: 480 }),
      }],
      getAudioTracks: () => [],
    }),
    enumerateDevices: jest.fn().mockResolvedValue([]),
  },
});

// Mock Battery API
Object.defineProperty(navigator, 'getBattery', {
  writable: true,
  value: jest.fn().mockResolvedValue({
    level: 0.8,
    charging: false,
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
  }),
});

// Mock Vibration API
Object.defineProperty(navigator, 'vibrate', {
  writable: true,
  value: jest.fn(),
});

// Mock Web Share API
Object.defineProperty(navigator, 'share', {
  writable: true,
  value: jest.fn().mockResolvedValue(undefined),
});

Object.defineProperty(navigator, 'canShare', {
  writable: true,
  value: jest.fn().mockReturnValue(true),
});

// Mock Storage APIs
Object.defineProperty(navigator, 'storage', {
  writable: true,
  value: {
    estimate: jest.fn().mockResolvedValue({
      quota: 1000000000,
      usage: 100000,
    }),
    persist: jest.fn().mockResolvedValue(true),
  },
});

// Mock Crypto API
Object.defineProperty(global, 'crypto', {
  value: {
    getRandomValues: jest.fn().mockImplementation((arr: any) => {
      for (let i = 0; i < arr.length; i++) {
        arr[i] = Math.floor(Math.random() * 256);
      }
      return arr;
    }),
    subtle: {
      digest: jest.fn().mockResolvedValue(new ArrayBuffer(32)),
    },
  },
});

// Mock URL.createObjectURL
global.URL.createObjectURL = jest.fn().mockReturnValue('mock-object-url');
global.URL.revokeObjectURL = jest.fn();

// Mock Blob constructor
global.Blob = jest.fn().mockImplementation((content, options) => ({
  size: content.reduce((acc: number, item: string) => acc + item.length, 0),
  type: options?.type || 'text/plain',
  arrayBuffer: jest.fn().mockResolvedValue(new ArrayBuffer(8)),
  text: jest.fn().mockResolvedValue(content.join('')),
})) as any;

// Mock File constructor
global.File = jest.fn().mockImplementation((content, filename, options) => ({
  ...new (global.Blob as any)(content, options),
  name: filename,
  lastModified: Date.now(),
})) as any;

// Mock FileReader
global.FileReader = jest.fn().mockImplementation(() => ({
  readAsDataURL: jest.fn().mockImplementation(function() {
    this.onload({ target: { result: 'data:image/png;base64,mock-data' } });
  }),
  readAsText: jest.fn().mockImplementation(function() {
    this.onload({ target: { result: 'mock text content' } });
  }),
  readAsArrayBuffer: jest.fn().mockImplementation(function() {
    this.onload({ target: { result: new ArrayBuffer(8) } });
  }),
})) as any;

// Mock console methods for cleaner test output
const originalError = console.error;
const originalWarn = console.warn;

console.error = (...args: any[]) => {
  // Suppress known test warnings
  if (
    args[0]?.includes?.('Warning: ReactDOM.render is deprecated') ||
    args[0]?.includes?.('Warning: componentWillReceiveProps') ||
    args[0]?.includes?.('act(...) is not supported')
  ) {
    return;
  }
  originalError.call(console, ...args);
};

console.warn = (...args: any[]) => {
  // Suppress known test warnings
  if (
    args[0]?.includes?.('componentWillMount') ||
    args[0]?.includes?.('componentWillReceiveProps')
  ) {
    return;
  }
  originalWarn.call(console, ...args);
};

// Mock fetch globally
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({}),
    text: () => Promise.resolve(''),
  })
) as jest.Mock;

// Set up test environment variables
process.env.NODE_ENV = 'test';
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
process.env.NEXT_PUBLIC_MOCK_DATA_ENABLED = 'true';
process.env.NEXT_PUBLIC_DEBUG_LOGGING_ENABLED = 'false';