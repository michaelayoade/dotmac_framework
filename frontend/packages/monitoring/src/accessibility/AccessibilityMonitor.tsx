/**
 * Accessibility Monitoring System
 *
 * Monitors component accessibility, runs automated tests,
 * and provides real-time feedback on accessibility issues
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import axe, { AxeResults, type Result } from 'axe-core';

// Accessibility issue types
export interface AccessibilityIssue {
  id: string;
  impact: 'minor' | 'moderate' | 'serious' | 'critical';
  description: string;
  help: string;
  helpUrl: string;
  nodes: {
    html: string;
    target: string[] | any;
    failureSummary?: string | undefined;
  }[];
}

export interface AccessibilityReport {
  componentName: string;
  timestamp: Date;
  violations: AccessibilityIssue[];
  passes: number;
  incomplete: AccessibilityIssue[];
  url: string;
  summary: {
    total: number;
    critical: number;
    serious: number;
    moderate: number;
    minor: number;
  };
}

export interface AccessibilityMonitorProps {
  children: React.ReactNode;
  componentName?: string;
  onReport?: (report: AccessibilityReport) => void;
  rules?: string[]; // Specific axe rules to run
  tags?: string[]; // Axe tags to include (e.g., 'wcag2a', 'wcag2aa', 'wcag21aa')
  disabled?: boolean;
  runOnMount?: boolean;
  runOnUpdate?: boolean;
  debounceMs?: number;
}

export function AccessibilityMonitor({
  children,
  componentName = 'UnknownComponent',
  onReport,
  rules,
  tags = ['wcag2a', 'wcag2aa', 'wcag21aa'],
  disabled = false,
  runOnMount = true,
  runOnUpdate = false,
  debounceMs = 1000,
}: AccessibilityMonitorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<NodeJS.Timeout>();
  const [isRunning, setIsRunning] = useState(false);

  // Run accessibility audit
  const runAudit = useCallback(async () => {
    if (disabled || !containerRef.current || isRunning) return;

    setIsRunning(true);

    try {
      const config: any = {
        ...(rules ? { rules: Object.fromEntries(rules.map((rule) => [rule, { enabled: true }])) } : {}),
        tags: tags,
      };

      const results: any = await axe.run(containerRef.current, config);

      // Transform results into our format
      const violations: AccessibilityIssue[] = results.violations.map((violation: any) => ({
        id: violation.id,
        impact: violation.impact as 'minor' | 'moderate' | 'serious' | 'critical',
        description: violation.description,
        help: violation.help,
        helpUrl: violation.helpUrl,
        nodes: violation.nodes.map((node: any) => ({
          html: node.html,
          target: Array.isArray(node.target) ? node.target : [String(node.target)],
          failureSummary: node.failureSummary,
        })),
      }));

      const incomplete: AccessibilityIssue[] = results.incomplete.map((incomplete: any) => ({
        id: incomplete.id,
        impact: incomplete.impact as 'minor' | 'moderate' | 'serious' | 'critical',
        description: incomplete.description,
        help: incomplete.help,
        helpUrl: incomplete.helpUrl,
        nodes: incomplete.nodes.map((node: any) => ({
          html: node.html,
          target: Array.isArray(node.target) ? node.target : [String(node.target)],
          failureSummary: node.failureSummary,
        })),
      }));

      // Calculate summary
      const summary = {
        total: violations.length,
        critical: violations.filter((v) => v.impact === 'critical').length,
        serious: violations.filter((v) => v.impact === 'serious').length,
        moderate: violations.filter((v) => v.impact === 'moderate').length,
        minor: violations.filter((v) => v.impact === 'minor').length,
      };

      const report: AccessibilityReport = {
        componentName,
        timestamp: new Date(),
        violations,
        passes: results.passes.length,
        incomplete,
        url: window.location.href,
        summary,
      };

      if (onReport) {
        onReport(report);
      }

      // Log to console in development
      if (process.env.NODE_ENV === 'development' && violations.length > 0) {
        console.group(`🔍 Accessibility Issues in ${componentName}`);
        violations.forEach((violation) => {
          console.error(`${violation.impact.toUpperCase()}: ${violation.description}`);
          console.log(`Help: ${violation.help}`);
          console.log(`More info: ${violation.helpUrl}`);
        });
        console.groupEnd();
      }
    } catch (error) {
      console.error('Accessibility audit failed:', error);
    } finally {
      setIsRunning(false);
    }
  }, [componentName, disabled, rules, tags, onReport, isRunning]);

  // Debounced audit runner
  const runDebouncedAudit = useCallback(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(runAudit, debounceMs);
  }, [runAudit, debounceMs]);

  // Run audit on mount
  useEffect(() => {
    if (runOnMount && !disabled) {
      // Small delay to ensure DOM is ready
      setTimeout(runAudit, 100);
    }
  }, [runOnMount, disabled, runAudit]);

  // Run audit on updates
  useEffect(() => {
    if (runOnUpdate && !disabled) {
      runDebouncedAudit();
    }
  });

  // Cleanup
  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

  if (disabled) {
    return <>{children}</>;
  }

  return (
    <div ref={containerRef} data-accessibility-monitor={componentName}>
      {children}
    </div>
  );
}

// Hook for manual accessibility testing
export function useAccessibilityTesting(componentName?: string) {
  const [lastReport, setLastReport] = useState<AccessibilityReport | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const runTest = useCallback(
    async (
      element: HTMLElement,
      options: {
        rules?: string[];
        tags?: string[];
      } = {}
    ): Promise<AccessibilityReport> => {
      setIsRunning(true);

      try {
        const { rules, tags = ['wcag2a', 'wcag2aa', 'wcag21aa'] } = options;

        const config: any = {
          ...(rules ? { rules: Object.fromEntries(rules.map((rule) => [rule, { enabled: true }])) } : {}),
          tags: tags,
        };

        const results: any = await axe.run(element, config);

        const violations: AccessibilityIssue[] = results.violations.map((violation: any) => ({
          id: violation.id,
          impact: violation.impact as 'minor' | 'moderate' | 'serious' | 'critical',
          description: violation.description,
          help: violation.help,
          helpUrl: violation.helpUrl,
          nodes: violation.nodes.map((node: any) => ({
            html: node.html,
            target: Array.isArray(node.target) ? node.target : [String(node.target)],
            failureSummary: node.failureSummary,
          })),
        }));

        const incomplete: AccessibilityIssue[] = results.incomplete.map((incomplete: any) => ({
          id: incomplete.id,
          impact: incomplete.impact as 'minor' | 'moderate' | 'serious' | 'critical',
          description: incomplete.description,
          help: incomplete.help,
          helpUrl: incomplete.helpUrl,
          nodes: incomplete.nodes.map((node: any) => ({
            html: node.html,
            target: Array.isArray(node.target) ? node.target : [String(node.target)],
            failureSummary: node.failureSummary,
          })),
        }));

        const summary = {
          total: violations.length,
          critical: violations.filter((v) => v.impact === 'critical').length,
          serious: violations.filter((v) => v.impact === 'serious').length,
          moderate: violations.filter((v) => v.impact === 'moderate').length,
          minor: violations.filter((v) => v.impact === 'minor').length,
        };

        const report: AccessibilityReport = {
          componentName: componentName || 'Manual Test',
          timestamp: new Date(),
          violations,
          passes: results.passes.length,
          incomplete,
          url: window.location.href,
          summary,
        };

        setLastReport(report);
        return report;
      } finally {
        setIsRunning(false);
      }
    },
    [componentName]
  );

  return {
    runTest,
    lastReport,
    isRunning,
  };
}

// HOC for automatic accessibility monitoring
export function withAccessibilityMonitoring<P extends object>(
  Component: React.ComponentType<P>,
  options: Omit<AccessibilityMonitorProps, 'children'> = {}
) {
  const WrappedComponent = React.forwardRef<any, P>((props, ref) => {
    const componentName =
      options.componentName || Component.displayName || Component.name || 'Anonymous';

    return (
      <AccessibilityMonitor {...options} componentName={componentName}>
        <Component {...(props as P)} ref={ref} />
      </AccessibilityMonitor>
    );
  });

  WrappedComponent.displayName = `withAccessibilityMonitoring(${Component.displayName || Component.name})`;

  return WrappedComponent;
}

// Accessibility report aggregator
export class AccessibilityAggregator {
  private reports: AccessibilityReport[] = [];
  private listeners: ((report: AccessibilityReport) => void)[] = [];

  addReport(report: AccessibilityReport) {
    this.reports.push(report);
    this.listeners.forEach((listener) => listener(report));

    // Keep only last 500 reports to prevent memory issues
    if (this.reports.length > 500) {
      this.reports = this.reports.slice(-500);
    }
  }

  onReport(listener: (report: AccessibilityReport) => void) {
    this.listeners.push(listener);

    return () => {
      const index = this.listeners.indexOf(listener);
      if (index > -1) {
        this.listeners.splice(index, 1);
      }
    };
  }

  getReports(componentName?: string): AccessibilityReport[] {
    if (componentName) {
      return this.reports.filter((report) => report.componentName === componentName);
    }
    return this.reports;
  }

  getLatestReport(componentName?: string): AccessibilityReport | null {
    const reports = this.getReports(componentName);
    return reports.length > 0 ? reports[reports.length - 1] ?? null : null;
  }

  getSummaryStats(): {
    totalComponents: number;
    componentsWithIssues: number;
    totalViolations: number;
    criticalIssues: number;
    seriousIssues: number;
  } {
    const componentNames = new Set(this.reports.map((r) => r.componentName));
    const componentsWithIssues = new Set(
      this.reports.filter((r) => r.violations.length > 0).map((r) => r.componentName)
    );

    const totalViolations = this.reports.reduce((sum, r) => sum + r.summary.total, 0);
    const criticalIssues = this.reports.reduce((sum, r) => sum + r.summary.critical, 0);
    const seriousIssues = this.reports.reduce((sum, r) => sum + r.summary.serious, 0);

    return {
      totalComponents: componentNames.size,
      componentsWithIssues: componentsWithIssues.size,
      totalViolations,
      criticalIssues,
      seriousIssues,
    };
  }

  clear() {
    this.reports = [];
  }
}

// Global accessibility aggregator instance
export const accessibilityAggregator = new AccessibilityAggregator();

// Utility functions for accessibility testing
export const AccessibilityUtils = {
  // Check if element is properly labeled
  hasProperLabeling: (element: HTMLElement): boolean => {
    return !!(
      element.getAttribute('aria-label') ||
      element.getAttribute('aria-labelledby') ||
      element.querySelector('label') ||
      element.getAttribute('title')
    );
  },

  // Check if interactive element is keyboard accessible
  isKeyboardAccessible: (element: HTMLElement): boolean => {
    const tagName = element.tagName.toLowerCase();
    const interactiveTags = ['button', 'a', 'input', 'select', 'textarea'];

    if (interactiveTags.includes(tagName)) {
      return true;
    }

    const tabIndex = element.getAttribute('tabindex');
    return tabIndex !== null && tabIndex !== '-1';
  },

  // Check color contrast (simplified - for full contrast checking use axe-core)
  hasGoodContrast: (foreground: string, background: string): boolean => {
    // This is a simplified check - real contrast calculation is complex
    // For production use, rely on axe-core's color-contrast rule
    const fgLuma = getRelativeLuminance(foreground);
    const bgLuma = getRelativeLuminance(background);

    const ratio = (Math.max(fgLuma, bgLuma) + 0.05) / (Math.min(fgLuma, bgLuma) + 0.05);
    return ratio >= 4.5; // WCAG AA standard for normal text
  },

  // Get all focusable elements within a container
  getFocusableElements: (container: HTMLElement): HTMLElement[] => {
    const focusableSelectors = [
      'a[href]',
      'button:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      'textarea:not([disabled])',
      '[tabindex]:not([tabindex="-1"])',
      '[contenteditable="true"]',
    ].join(', ');

    return Array.from(container.querySelectorAll(focusableSelectors)) as HTMLElement[];
  },
};

// Helper function for luminance calculation
function getRelativeLuminance(color: string): number {
  // This is a simplified version - full implementation would handle all color formats
  // For production, use a proper color library
  const rgb = hexToRgb(color);
  if (!rgb) return 0;

  const rsRGB = rgb.r / 255;
  const gsRGB = rgb.g / 255;
  const bsRGB = rgb.b / 255;

  const r = rsRGB <= 0.03928 ? rsRGB / 12.92 : Math.pow((rsRGB + 0.055) / 1.055, 2.4);
  const g = gsRGB <= 0.03928 ? gsRGB / 12.92 : Math.pow((gsRGB + 0.055) / 1.055, 2.4);
  const b = bsRGB <= 0.03928 ? bsRGB / 12.92 : Math.pow((bsRGB + 0.055) / 1.055, 2.4);

  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? {
        r: parseInt(result[1] ?? '0', 16),
        g: parseInt(result[2] ?? '0', 16),
        b: parseInt(result[3] ?? '0', 16),
      }
    : null;
}
