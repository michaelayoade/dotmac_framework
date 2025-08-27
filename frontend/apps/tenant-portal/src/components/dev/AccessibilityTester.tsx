/**
 * Accessibility Testing Component
 * Development tool for testing and validating accessibility compliance
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { 
  AccessibilityTester, 
  auditAccessibility, 
  type AccessibilityAuditResult, 
  type AccessibilityIssue 
} from '@/lib/accessibility-testing';
import { AccessibleButton } from '@/components/ui/AccessibleForm';

// Only show in development
const isDev = process.env.NODE_ENV === 'development';

interface AccessibilityTesterComponentProps {
  container?: HTMLElement;
  autoRun?: boolean;
  position?: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left';
}

export function AccessibilityTesterComponent({
  container,
  autoRun = false,
  position = 'bottom-right',
}: AccessibilityTesterComponentProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [auditResult, setAuditResult] = useState<AccessibilityAuditResult | null>(null);
  const [selectedIssue, setSelectedIssue] = useState<AccessibilityIssue | null>(null);
  const [tester, setTester] = useState<AccessibilityTester | null>(null);

  // Only render in development
  if (!isDev) return null;

  useEffect(() => {
    const testContainer = container || document.body;
    const accessibilityTester = new AccessibilityTester(testContainer);
    setTester(accessibilityTester);

    if (autoRun) {
      runAudit(accessibilityTester);
    }
  }, [container, autoRun]);

  const runAudit = useCallback(async (testerInstance?: AccessibilityTester) => {
    if (!testerInstance && !tester) return;
    
    setIsLoading(true);
    try {
      const result = await (testerInstance || tester)!.runFullAudit();
      setAuditResult(result);
    } catch (error) {
      console.error('Accessibility audit failed:', error);
    } finally {
      setIsLoading(false);
    }
  }, [tester]);

  const highlightElement = useCallback((issue: AccessibilityIssue) => {
    // Remove previous highlights
    document.querySelectorAll('.a11y-highlight').forEach(el => {
      el.classList.remove('a11y-highlight');
    });

    // Add highlight to current element
    issue.element.classList.add('a11y-highlight');
    issue.element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setSelectedIssue(issue);
  }, []);

  const clearHighlights = useCallback(() => {
    document.querySelectorAll('.a11y-highlight').forEach(el => {
      el.classList.remove('a11y-highlight');
    });
    setSelectedIssue(null);
  }, []);

  const getPositionClasses = () => {
    const base = 'fixed z-50';
    switch (position) {
      case 'bottom-right':
        return `${base} bottom-4 right-4`;
      case 'bottom-left':
        return `${base} bottom-4 left-4`;
      case 'top-right':
        return `${base} top-4 right-4`;
      case 'top-left':
        return `${base} top-4 left-4`;
      default:
        return `${base} bottom-4 right-4`;
    }
  };

  const getIssueColor = (impact: string) => {
    switch (impact) {
      case 'critical':
        return 'text-red-700 bg-red-100 border-red-200';
      case 'serious':
        return 'text-orange-700 bg-orange-100 border-orange-200';
      case 'moderate':
        return 'text-yellow-700 bg-yellow-100 border-yellow-200';
      case 'minor':
        return 'text-blue-700 bg-blue-100 border-blue-200';
      default:
        return 'text-gray-700 bg-gray-100 border-gray-200';
    }
  };

  return (
    <>
      {/* Add CSS for highlighting */}
      <style jsx global>{`
        .a11y-highlight {
          outline: 3px solid #ff0000 !important;
          outline-offset: 2px !important;
          position: relative !important;
        }
        .a11y-highlight::before {
          content: '⚠️ A11Y Issue';
          position: absolute;
          top: -30px;
          left: 0;
          background: #ff0000;
          color: white;
          padding: 2px 6px;
          font-size: 12px;
          border-radius: 3px;
          z-index: 1000;
        }
      `}</style>

      <div className={getPositionClasses()}>
        {!isOpen && (
          <AccessibleButton
            onClick={() => setIsOpen(true)}
            variant="secondary"
            className="rounded-full w-12 h-12 shadow-lg border-2 border-blue-500"
            aria-label="Open accessibility tester"
          >
            <span className="text-lg">♿</span>
          </AccessibleButton>
        )}

        {isOpen && (
          <div className="bg-white border border-gray-300 rounded-lg shadow-xl max-w-md w-80 max-h-96 overflow-hidden">
            {/* Header */}
            <div className="bg-blue-600 text-white p-3 flex justify-between items-center">
              <h3 className="font-semibold text-sm">Accessibility Tester</h3>
              <div className="flex gap-2">
                <AccessibleButton
                  onClick={() => runAudit()}
                  disabled={isLoading}
                  variant="ghost"
                  size="sm"
                  className="text-white hover:bg-blue-700 px-2 py-1"
                >
                  {isLoading ? '...' : '🔄'}
                </AccessibleButton>
                <AccessibleButton
                  onClick={() => {
                    clearHighlights();
                    setIsOpen(false);
                  }}
                  variant="ghost"
                  size="sm"
                  className="text-white hover:bg-blue-700 px-2 py-1"
                >
                  ✕
                </AccessibleButton>
              </div>
            </div>

            {/* Content */}
            <div className="p-3">
              {isLoading && (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
                  <div className="text-sm text-gray-600">Running accessibility audit...</div>
                </div>
              )}

              {!isLoading && !auditResult && (
                <div className="text-center py-8">
                  <div className="text-4xl mb-2">♿</div>
                  <div className="text-sm text-gray-600 mb-4">
                    Click "Run Audit" to test accessibility
                  </div>
                  <AccessibleButton
                    onClick={() => runAudit()}
                    variant="primary"
                    size="sm"
                  >
                    Run Audit
                  </AccessibleButton>
                </div>
              )}

              {auditResult && (
                <div className="space-y-3">
                  {/* Score */}
                  <div className="text-center">
                    <div className={`text-2xl font-bold ${
                      auditResult.score >= 90 ? 'text-green-600' :
                      auditResult.score >= 70 ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {auditResult.score}/100
                    </div>
                    <div className="text-xs text-gray-600">
                      WCAG {auditResult.wcagLevel} Level
                    </div>
                  </div>

                  {/* Summary */}
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {auditResult.summary.critical > 0 && (
                      <div className="bg-red-50 border border-red-200 rounded px-2 py-1">
                        <div className="font-medium text-red-700">Critical</div>
                        <div className="text-red-600">{auditResult.summary.critical}</div>
                      </div>
                    )}
                    {auditResult.summary.serious > 0 && (
                      <div className="bg-orange-50 border border-orange-200 rounded px-2 py-1">
                        <div className="font-medium text-orange-700">Serious</div>
                        <div className="text-orange-600">{auditResult.summary.serious}</div>
                      </div>
                    )}
                    {auditResult.summary.moderate > 0 && (
                      <div className="bg-yellow-50 border border-yellow-200 rounded px-2 py-1">
                        <div className="font-medium text-yellow-700">Moderate</div>
                        <div className="text-yellow-600">{auditResult.summary.moderate}</div>
                      </div>
                    )}
                    {auditResult.summary.minor > 0 && (
                      <div className="bg-blue-50 border border-blue-200 rounded px-2 py-1">
                        <div className="font-medium text-blue-700">Minor</div>
                        <div className="text-blue-600">{auditResult.summary.minor}</div>
                      </div>
                    )}
                  </div>

                  {/* Issues List */}
                  {auditResult.issues.length > 0 && (
                    <div className="max-h-48 overflow-y-auto space-y-1">
                      {auditResult.issues.map((issue, index) => (
                        <button
                          key={index}
                          onClick={() => highlightElement(issue)}
                          className={`w-full text-left p-2 rounded border text-xs transition-colors ${
                            getIssueColor(issue.impact)
                          } hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-blue-500`}
                        >
                          <div className="font-medium">{issue.rule}</div>
                          <div className="truncate">{issue.description}</div>
                          <div className="text-gray-600 mt-1 truncate">
                            {issue.selector}
                          </div>
                        </button>
                      ))}
                    </div>
                  )}

                  {/* No Issues */}
                  {auditResult.issues.length === 0 && (
                    <div className="text-center py-4 text-green-600">
                      <div className="text-2xl mb-1">✅</div>
                      <div className="text-sm font-medium">No accessibility issues found!</div>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-2 pt-2 border-t">
                    <AccessibleButton
                      onClick={clearHighlights}
                      variant="secondary"
                      size="sm"
                      className="flex-1 text-xs"
                    >
                      Clear Highlights
                    </AccessibleButton>
                    <AccessibleButton
                      onClick={() => {
                        if (auditResult && tester) {
                          const report = tester.generateReport(auditResult);
                          console.log(report);
                          
                          // Also try to copy to clipboard
                          if (navigator.clipboard) {
                            navigator.clipboard.writeText(report);
                          }
                        }
                      }}
                      variant="secondary"
                      size="sm"
                      className="flex-1 text-xs"
                    >
                      Export Report
                    </AccessibleButton>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Issue Detail Modal */}
        {selectedIssue && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full m-4">
              <div className="p-4 border-b">
                <div className="flex justify-between items-start">
                  <h3 className="font-semibold">{selectedIssue.rule}</h3>
                  <AccessibleButton
                    onClick={clearHighlights}
                    variant="ghost"
                    size="sm"
                    className="ml-2"
                  >
                    ✕
                  </AccessibleButton>
                </div>
                <div className={`text-sm px-2 py-1 rounded mt-2 inline-block ${
                  getIssueColor(selectedIssue.impact)
                }`}>
                  {selectedIssue.impact.toUpperCase()}
                </div>
              </div>
              
              <div className="p-4 space-y-3">
                <div>
                  <div className="font-medium text-sm mb-1">Description:</div>
                  <div className="text-sm text-gray-700">{selectedIssue.description}</div>
                </div>
                
                <div>
                  <div className="font-medium text-sm mb-1">Element:</div>
                  <code className="text-xs bg-gray-100 p-1 rounded block">
                    {selectedIssue.selector}
                  </code>
                </div>
                
                <div>
                  <div className="font-medium text-sm mb-1">Suggestion:</div>
                  <div className="text-sm text-gray-700">{selectedIssue.suggestion}</div>
                </div>
                
                <div className="pt-2 border-t">
                  <AccessibleButton
                    onClick={clearHighlights}
                    variant="primary"
                    size="sm"
                    className="w-full"
                  >
                    Close
                  </AccessibleButton>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

// Hook for programmatic access
export function useAccessibilityTesting(container?: HTMLElement) {
  const [tester, setTester] = useState<AccessibilityTester | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<AccessibilityAuditResult | null>(null);

  useEffect(() => {
    if (isDev) {
      const testContainer = container || document.body;
      setTester(new AccessibilityTester(testContainer));
    }
  }, [container]);

  const runAudit = useCallback(async () => {
    if (!tester) return null;
    
    setIsLoading(true);
    try {
      const auditResult = await tester.runFullAudit();
      setResult(auditResult);
      return auditResult;
    } catch (error) {
      console.error('Accessibility audit failed:', error);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [tester]);

  const runKeyboardAudit = useCallback(async () => {
    if (!tester) return [];
    return await tester.runKeyboardAudit();
  }, [tester]);

  const runAriaAudit = useCallback(async () => {
    if (!tester) return [];
    return await tester.runAriaAudit();
  }, [tester]);

  return {
    runAudit,
    runKeyboardAudit,
    runAriaAudit,
    isLoading,
    result,
    isDevMode: isDev,
  };
}