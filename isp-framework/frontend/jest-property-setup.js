/**
 * Jest setup specifically for property-based tests
 * Handles userEvent clipboard issues and provides utilities for AI-first testing
 */

import { jest } from '@jest/globals';

// Mock userEvent setup to prevent clipboard redefinition errors
let originalDefineProperty;

beforeAll(() => {
  // Store original defineProperty
  originalDefineProperty = Object.defineProperty;
  
  // Mock defineProperty to handle clipboard redefinition gracefully
  Object.defineProperty = function(obj, prop, descriptor) {
    if (prop === 'clipboard' && obj === navigator) {
      // Skip clipboard redefinition for userEvent in property-based tests
      if (obj.hasOwnProperty(prop)) {
        return obj;
      }
    }
    return originalDefineProperty.call(this, obj, prop, descriptor);
  };
});

afterAll(() => {
  // Restore original defineProperty
  if (originalDefineProperty) {
    Object.defineProperty = originalDefineProperty;
  }
});

// Property-based test utilities
global.propertyTestUtils = {
  // Clean component state between property test runs
  cleanupComponent: () => {
    // Clear any lingering DOM state
    document.body.innerHTML = '';
    
    // Clear navigator clipboard if it exists
    if ('clipboard' in navigator) {
      try {
        delete navigator.clipboard;
      } catch (e) {
        // Ignore errors - clipboard cleanup is best effort
      }
    }
    
    // Clear all mocks
    jest.clearAllMocks();
  },
  
  // Safe userEvent setup for property tests
  safeUserEventSetup: async () => {
    try {
      const { userEvent } = await import('@testing-library/user-event');
      return userEvent.setup({
        // Disable clipboard to avoid redefinition errors
        writeToClipboard: false,
        readFromClipboard: false,
      });
    } catch (error) {
      // Fallback to fireEvent if userEvent fails
      const { fireEvent } = await import('@testing-library/react');
      return {
        click: fireEvent.click,
        type: (element, text) => fireEvent.change(element, { target: { value: text } }),
        clear: (element) => fireEvent.change(element, { target: { value: '' } }),
      };
    }
  }
};

// Enhanced error handling for property tests
const originalConsoleError = console.error;
console.error = (...args) => {
  // Filter out clipboard redefinition warnings in property tests
  const message = args[0];
  if (typeof message === 'string' && message.includes('clipboard')) {
    return;
  }
  
  // Filter out userEvent warnings that are expected in property tests
  if (typeof message === 'string' && message.includes('userEvent')) {
    return;
  }
  
  originalConsoleError(...args);
};

export default {};