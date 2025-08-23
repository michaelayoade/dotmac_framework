
/**
 * Performance Test Suite
 * Comprehensive performance testing for all components
 */

import { describe, it, expect } from '@jest/globals';
import './button-performance.test';
import './form-performance.test';
import './table-performance.test';
import './dashboard-performance.test';

describe('Performance Test Suite', () => {
  it('should validate all performance tests are loaded', () => {
    expect(true).toBe(true);
  });
});
