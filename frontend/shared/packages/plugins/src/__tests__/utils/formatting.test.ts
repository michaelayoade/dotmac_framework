import {
  formatPluginStatus,
  formatPluginKey,
  parsePluginKey,
  formatPluginVersion,
  formatPluginUptime,
  formatPluginSize,
  formatDownloadCount,
  formatPluginRating,
  formatLastActivity,
  getPluginStatusClasses,
} from '../../utils/formatting';
import { PluginStatus } from '../../types';

describe('Plugin Formatting Utils', () => {
  describe('formatPluginStatus', () => {
    it('should format active status', () => {
      expect(formatPluginStatus(PluginStatus.ACTIVE)).toBe('Active');
    });

    it('should format error status', () => {
      expect(formatPluginStatus(PluginStatus.ERROR)).toBe('Error');
    });

    it('should format initializing status', () => {
      expect(formatPluginStatus(PluginStatus.INITIALIZING)).toBe('Initializing...');
    });
  });

  describe('formatPluginKey and parsePluginKey', () => {
    it('should format plugin key', () => {
      expect(formatPluginKey('com.example', 'test-plugin')).toBe('com.example.test-plugin');
    });

    it('should parse plugin key', () => {
      const result = parsePluginKey('com.example.test-plugin');
      expect(result.domain).toBe('com.example');
      expect(result.name).toBe('test-plugin');
    });

    it('should parse complex domain plugin key', () => {
      const result = parsePluginKey('com.example.subdomain.test-plugin');
      expect(result.domain).toBe('com.example.subdomain');
      expect(result.name).toBe('test-plugin');
    });

    it('should throw error for invalid plugin key', () => {
      expect(() => parsePluginKey('invalid')).toThrow('Invalid plugin key format');
    });
  });

  describe('formatPluginVersion', () => {
    it('should format version with prefix', () => {
      expect(formatPluginVersion('1.0.0')).toBe('v1.0.0');
    });

    it('should format version without prefix', () => {
      expect(formatPluginVersion('1.0.0', false)).toBe('1.0.0');
    });
  });

  describe('formatPluginUptime', () => {
    it('should format uptime in seconds', () => {
      expect(formatPluginUptime(45)).toBe('45s');
    });

    it('should format uptime in minutes', () => {
      expect(formatPluginUptime(125)).toBe('2m 5s');
    });

    it('should format uptime in hours', () => {
      expect(formatPluginUptime(3665)).toBe('1h 1m');
    });

    it('should handle undefined uptime', () => {
      expect(formatPluginUptime(undefined)).toBe('N/A');
    });

    it('should handle zero uptime', () => {
      expect(formatPluginUptime(0)).toBe('N/A');
    });
  });

  describe('formatPluginSize', () => {
    it('should format bytes', () => {
      expect(formatPluginSize(500)).toBe('500 B');
    });

    it('should format kilobytes', () => {
      expect(formatPluginSize(1536)).toBe('1.5 KB');
    });

    it('should format megabytes', () => {
      expect(formatPluginSize(1572864)).toBe('1.5 MB');
    });

    it('should format gigabytes', () => {
      expect(formatPluginSize(1610612736)).toBe('1.5 GB');
    });
  });

  describe('formatDownloadCount', () => {
    it('should format small numbers', () => {
      expect(formatDownloadCount(500)).toBe('500');
    });

    it('should format thousands', () => {
      expect(formatDownloadCount(1500)).toBe('1.5K');
    });

    it('should format millions', () => {
      expect(formatDownloadCount(1500000)).toBe('1.5M');
    });
  });

  describe('formatPluginRating', () => {
    it('should format rating as number', () => {
      expect(formatPluginRating(4.67)).toBe('4.7');
    });

    it('should format rating with stars', () => {
      const result = formatPluginRating(4.3, true);
      expect(result).toContain('★★★★');
      expect(result).toContain('(4.3)');
    });

    it('should handle half stars', () => {
      const result = formatPluginRating(3.7, true);
      expect(result).toContain('★★★½');
    });
  });

  describe('formatLastActivity', () => {
    it('should return "Never" for undefined', () => {
      expect(formatLastActivity(undefined)).toBe('Never');
    });

    it('should format valid date', () => {
      // Mock returns "2 minutes ago" from setup
      expect(formatLastActivity('2023-01-01T00:00:00Z')).toBe('2 minutes ago');
    });

    it('should handle invalid date', () => {
      expect(formatLastActivity('invalid-date')).toBe('Unknown');
    });
  });

  describe('getPluginStatusClasses', () => {
    it('should return correct classes for active status', () => {
      const classes = getPluginStatusClasses(PluginStatus.ACTIVE);
      expect(classes).toContain('bg-green-100');
      expect(classes).toContain('text-green-800');
    });

    it('should return correct classes for error status', () => {
      const classes = getPluginStatusClasses(PluginStatus.ERROR);
      expect(classes).toContain('bg-red-100');
      expect(classes).toContain('text-red-800');
    });

    it('should return correct classes for inactive status', () => {
      const classes = getPluginStatusClasses(PluginStatus.INACTIVE);
      expect(classes).toContain('bg-gray-100');
      expect(classes).toContain('text-gray-800');
    });
  });
});
