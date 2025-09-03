/**
 * Accessibility Checker Component
 * Developer tool for checking accessibility violations
 */

'use client';

import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  CheckCircle,
  Info,
  X,
  ExternalLink,
  Zap,
  Eye,
  Keyboard,
  Volume2,
} from 'lucide-react';
import {
  useAccessibility,
  type AccessibilityReport,
  type AccessibilityViolation,
} from './AccessibilityProvider';

interface AccessibilityCheckerProps {
  enabled?: boolean;
  autoCheck?: boolean;
  position?: 'bottom-left' | 'bottom-right' | 'top-left' | 'top-right';
}

export function AccessibilityChecker({
  enabled = process.env.NODE_ENV === 'development',
  autoCheck = false,
  position = 'bottom-right',
}: AccessibilityCheckerProps) {
  const { checkAccessibility } = useAccessibility();
  const [isOpen, setIsOpen] = useState(false);
  const [report, setReport] = useState<AccessibilityReport | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const [selectedViolation, setSelectedViolation] = useState<AccessibilityViolation | null>(null);

  // Auto-check on mount and DOM changes
  useEffect(() => {
    if (!enabled || !autoCheck) return;

    const runCheck = async () => {
      setIsChecking(true);
      try {
        const newReport = await checkAccessibility();
        setReport(newReport);
      } catch (error) {
        console.error('Accessibility check failed:', error);
      } finally {
        setIsChecking(false);
      }
    };

    runCheck();

    // Set up observer for DOM changes
    const observer = new MutationObserver((mutations) => {
      const hasSignificantChanges = mutations.some(
        (mutation) => mutation.type === 'childList' || mutation.type === 'attributes'
      );

      if (hasSignificantChanges) {
        // Debounce checks
        clearTimeout((runCheck as any).timeout);
        (runCheck as any).timeout = setTimeout(runCheck, 1000);
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['aria-label', 'aria-labelledby', 'alt', 'role'],
    });

    return () => {
      observer.disconnect();
      clearTimeout((runCheck as any).timeout);
    };
  }, [enabled, autoCheck, checkAccessibility]);

  const handleManualCheck = async () => {
    setIsChecking(true);
    try {
      const newReport = await checkAccessibility();
      setReport(newReport);
      setIsOpen(true);
    } catch (error) {
      console.error('Accessibility check failed:', error);
    } finally {
      setIsChecking(false);
    }
  };

  const highlightElement = (element?: HTMLElement) => {
    // Remove previous highlights
    document.querySelectorAll('.accessibility-highlight').forEach((el) => {
      el.classList.remove('accessibility-highlight');
    });

    if (element) {
      element.classList.add('accessibility-highlight');
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  const getImpactColor = (impact: AccessibilityViolation['impact']) => {
    switch (impact) {
      case 'critical':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'serious':
        return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'moderate':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'minor':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getImpactIcon = (impact: AccessibilityViolation['impact']) => {
    switch (impact) {
      case 'critical':
      case 'serious':
        return <AlertTriangle className='w-4 h-4' />;
      case 'moderate':
        return <Info className='w-4 h-4' />;
      case 'minor':
        return <Info className='w-4 h-4' />;
      default:
        return <Info className='w-4 h-4' />;
    }
  };

  const positionClasses = {
    'bottom-right': 'bottom-4 right-4',
    'bottom-left': 'bottom-4 left-4',
    'top-right': 'top-4 right-4',
    'top-left': 'top-4 left-4',
  };

  if (!enabled) return null;

  return (
    <>
      {/* Highlight styles */}
      <style jsx global>{`
        .accessibility-highlight {
          outline: 3px solid #ff0000 !important;
          outline-offset: 2px !important;
          background-color: rgba(255, 0, 0, 0.1) !important;
        }
      `}</style>

      {/* Floating button */}
      <div className={`fixed z-50 ${positionClasses[position]}`}>
        <button
          onClick={handleManualCheck}
          disabled={isChecking}
          className='bg-blue-600 hover:bg-blue-700 text-white rounded-full p-3 shadow-lg transition-all duration-200 disabled:opacity-50'
          title='Check Accessibility'
          aria-label='Check page accessibility'
        >
          {isChecking ? (
            <div className='w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin' />
          ) : (
            <Eye className='w-6 h-6' />
          )}
        </button>

        {/* Violation count badge */}
        {report && report.violations.length > 0 && (
          <div className='absolute -top-2 -right-2 bg-red-500 text-white text-xs rounded-full w-6 h-6 flex items-center justify-center font-bold'>
            {report.violations.length > 99 ? '99+' : report.violations.length}
          </div>
        )}
      </div>

      {/* Results panel */}
      {isOpen && report && (
        <div className='fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center p-4'>
          <div className='bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col'>
            {/* Header */}
            <div className='flex items-center justify-between p-6 border-b border-gray-200'>
              <div>
                <h2 className='text-xl font-semibold text-gray-900'>Accessibility Report</h2>
                <div className='flex items-center gap-4 mt-2 text-sm'>
                  <span className='flex items-center text-red-600'>
                    <AlertTriangle className='w-4 h-4 mr-1' />
                    {report.violations.length} violations
                  </span>
                  <span className='flex items-center text-green-600'>
                    <CheckCircle className='w-4 h-4 mr-1' />
                    {report.passes} passed
                  </span>
                </div>
              </div>
              <button
                onClick={() => {
                  setIsOpen(false);
                  setSelectedViolation(null);
                  highlightElement();
                }}
                className='text-gray-400 hover:text-gray-600 p-2'
                aria-label='Close accessibility report'
              >
                <X className='w-6 h-6' />
              </button>
            </div>

            {/* Content */}
            <div className='flex-1 overflow-hidden'>
              {report.violations.length === 0 ? (
                <div className='flex flex-col items-center justify-center p-12 text-center'>
                  <CheckCircle className='w-16 h-16 text-green-500 mb-4' />
                  <h3 className='text-xl font-semibold text-gray-900 mb-2'>
                    No Accessibility Violations Found!
                  </h3>
                  <p className='text-gray-600'>
                    This page appears to meet basic accessibility standards.
                  </p>
                </div>
              ) : (
                <div className='flex h-full'>
                  {/* Violations list */}
                  <div className='w-1/2 border-r border-gray-200 overflow-y-auto'>
                    <div className='p-4 border-b border-gray-200 bg-gray-50'>
                      <h3 className='font-medium text-gray-900'>Violations</h3>
                      <p className='text-sm text-gray-600'>
                        Click on a violation to see details and highlight the element
                      </p>
                    </div>
                    <div className='divide-y divide-gray-200'>
                      {report.violations.map((violation) => (
                        <button
                          key={violation.id}
                          onClick={() => {
                            setSelectedViolation(violation);
                            highlightElement(violation.element);
                          }}
                          className={`w-full text-left p-4 hover:bg-gray-50 transition-colors ${
                            selectedViolation?.id === violation.id
                              ? 'bg-blue-50 border-l-4 border-blue-500'
                              : ''
                          }`}
                        >
                          <div className='flex items-start gap-3'>
                            <div
                              className={`mt-0.5 ${getImpactColor(violation.impact).split(' ')[0]}`}
                            >
                              {getImpactIcon(violation.impact)}
                            </div>
                            <div className='flex-1 min-w-0'>
                              <div className='flex items-center gap-2 mb-1'>
                                <span
                                  className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getImpactColor(violation.impact)}`}
                                >
                                  {violation.impact}
                                </span>
                              </div>
                              <h4 className='font-medium text-gray-900 text-sm'>
                                {violation.description}
                              </h4>
                              <p className='text-sm text-gray-600 mt-1 truncate'>
                                {violation.help}
                              </p>
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Violation details */}
                  <div className='w-1/2 overflow-y-auto'>
                    {selectedViolation ? (
                      <div className='p-6'>
                        <div className='mb-6'>
                          <div className='flex items-center gap-2 mb-2'>
                            <span
                              className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getImpactColor(selectedViolation.impact)}`}
                            >
                              {getImpactIcon(selectedViolation.impact)}
                              <span className='ml-1 capitalize'>{selectedViolation.impact}</span>
                            </span>
                          </div>
                          <h3 className='text-lg font-semibold text-gray-900 mb-2'>
                            {selectedViolation.description}
                          </h3>
                        </div>

                        <div className='space-y-6'>
                          <div>
                            <h4 className='font-medium text-gray-900 mb-2'>How to fix this:</h4>
                            <p className='text-gray-600'>{selectedViolation.help}</p>
                          </div>

                          {selectedViolation.helpUrl && (
                            <div>
                              <h4 className='font-medium text-gray-900 mb-2'>Learn more:</h4>
                              <a
                                href={selectedViolation.helpUrl}
                                target='_blank'
                                rel='noopener noreferrer'
                                className='inline-flex items-center text-blue-600 hover:text-blue-500'
                              >
                                View accessibility guidelines
                                <ExternalLink className='w-4 h-4 ml-1' />
                              </a>
                            </div>
                          )}

                          {selectedViolation.element && (
                            <div>
                              <h4 className='font-medium text-gray-900 mb-2'>Element:</h4>
                              <div className='bg-gray-100 rounded-lg p-3'>
                                <code className='text-sm text-gray-800'>
                                  {selectedViolation.element.tagName.toLowerCase()}
                                  {selectedViolation.element.id &&
                                    ` id="${selectedViolation.element.id}"`}
                                  {selectedViolation.element.className &&
                                    ` class="${selectedViolation.element.className}"`}
                                </code>
                              </div>
                              <button
                                onClick={() => highlightElement(selectedViolation.element)}
                                className='mt-2 text-sm text-blue-600 hover:text-blue-500'
                              >
                                Highlight element on page
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    ) : (
                      <div className='flex items-center justify-center h-full text-gray-500'>
                        Select a violation to see details
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className='border-t border-gray-200 p-4 bg-gray-50'>
              <div className='flex items-center justify-between'>
                <div className='text-sm text-gray-600'>
                  This is a basic accessibility check. For comprehensive testing, use tools like
                  axe-core or WAVE.
                </div>
                <div className='flex gap-2'>
                  <button
                    onClick={handleManualCheck}
                    disabled={isChecking}
                    className='px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg disabled:opacity-50'
                  >
                    {isChecking ? 'Checking...' : 'Re-check'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
