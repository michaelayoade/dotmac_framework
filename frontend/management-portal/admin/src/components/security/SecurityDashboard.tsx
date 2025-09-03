'use client';

import React, { useState, useEffect } from 'react';
import {
  ShieldCheckIcon,
  ShieldExclamationIcon,
  ExclamationTriangleIcon,
  BugAntIcon,
  CheckCircleIcon,
  ClockIcon,
  EyeIcon,
  EyeSlashIcon,
} from '@heroicons/react/24/outline';
import {
  getSecurityScanner,
  SecuritySeverity,
  VulnerabilityType,
  type SecurityVulnerability,
  type SecurityScanResult,
} from '@/lib/security-scanner';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

export function SecurityDashboard() {
  const [scanResult, setScanResult] = useState<SecurityScanResult | null>(null);
  const [scanning, setScanning] = useState(false);
  const [selectedVulnerability, setSelectedVulnerability] = useState<SecurityVulnerability | null>(
    null
  );
  const [showDetails, setShowDetails] = useState(false);
  const [lastScanTime, setLastScanTime] = useState<string>('Never');

  const scanner = getSecurityScanner();

  useEffect(() => {
    // Load latest scan on component mount
    const latest = scanner.getLatestScan();
    if (latest) {
      setScanResult(latest);
      setLastScanTime(new Date(latest.endTime).toLocaleString());
    }
  }, [scanner]);

  const handleScan = async () => {
    setScanning(true);
    try {
      const result = await scanner.performSecurityScan();
      setScanResult(result);
      setLastScanTime(new Date(result.endTime).toLocaleString());
    } catch (error) {
      console.error('Security scan failed:', error);
    } finally {
      setScanning(false);
    }
  };

  const handleAcknowledge = (vulnerabilityId: string) => {
    const success = scanner.acknowledgeVulnerability(vulnerabilityId);
    if (success && scanResult) {
      const updatedVulns = scanResult.vulnerabilities.map((v) =>
        v.id === vulnerabilityId ? { ...v, status: 'acknowledged' as const } : v
      );
      setScanResult({ ...scanResult, vulnerabilities: updatedVulns });
    }
  };

  const getSeverityColor = (severity: SecuritySeverity) => {
    switch (severity) {
      case SecuritySeverity.CRITICAL:
        return 'text-red-600 bg-red-50 border-red-200';
      case SecuritySeverity.HIGH:
        return 'text-orange-600 bg-orange-50 border-orange-200';
      case SecuritySeverity.MEDIUM:
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case SecuritySeverity.LOW:
        return 'text-blue-600 bg-blue-50 border-blue-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getSeverityIcon = (severity: SecuritySeverity) => {
    switch (severity) {
      case SecuritySeverity.CRITICAL:
        return <ExclamationTriangleIcon className='h-5 w-5 text-red-500' />;
      case SecuritySeverity.HIGH:
        return <ShieldExclamationIcon className='h-5 w-5 text-orange-500' />;
      case SecuritySeverity.MEDIUM:
        return <BugAntIcon className='h-5 w-5 text-yellow-500' />;
      case SecuritySeverity.LOW:
        return <ShieldCheckIcon className='h-5 w-5 text-blue-500' />;
      default:
        return <CheckCircleIcon className='h-5 w-5 text-gray-500' />;
    }
  };

  const getVulnerabilityTypeLabel = (type: VulnerabilityType) => {
    return type
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const getRiskScoreColor = (score: number) => {
    if (score >= 80) return 'text-red-600';
    if (score >= 60) return 'text-orange-600';
    if (score >= 30) return 'text-yellow-600';
    return 'text-green-600';
  };

  return (
    <div className='space-y-6'>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div>
          <h1 className='text-2xl font-bold text-gray-900'>Security Dashboard</h1>
          <p className='text-gray-600 mt-1'>Monitor and manage security vulnerabilities</p>
        </div>

        <div className='flex items-center space-x-4'>
          <div className='text-sm text-gray-500'>Last scan: {lastScanTime}</div>
          <button
            onClick={handleScan}
            disabled={scanning}
            className='flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50'
          >
            {scanning ? (
              <>
                <LoadingSpinner size='small' />
                <span>Scanning...</span>
              </>
            ) : (
              <>
                <ShieldCheckIcon className='h-4 w-4' />
                <span>Run Security Scan</span>
              </>
            )}
          </button>
        </div>
      </div>

      {!scanResult ? (
        <div className='text-center py-12'>
          <ShieldCheckIcon className='mx-auto h-12 w-12 text-gray-400' />
          <h2 className='mt-4 text-xl font-semibold text-gray-900'>No Security Scans Available</h2>
          <p className='mt-2 text-gray-600'>
            Run your first security scan to identify vulnerabilities
          </p>
        </div>
      ) : (
        <>
          {/* Summary Cards */}
          <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4'>
            <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
              <div className='flex items-center justify-between'>
                <div>
                  <p className='text-sm font-medium text-gray-600'>Total Vulnerabilities</p>
                  <p className='text-3xl font-bold text-gray-900'>{scanResult.summary.total}</p>
                </div>
                <BugAntIcon className='h-8 w-8 text-gray-400' />
              </div>
            </div>

            <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
              <div className='flex items-center justify-between'>
                <div>
                  <p className='text-sm font-medium text-gray-600'>Risk Score</p>
                  <p className={`text-3xl font-bold ${getRiskScoreColor(scanResult.riskScore)}`}>
                    {scanResult.riskScore}/100
                  </p>
                </div>
                <ExclamationTriangleIcon
                  className={`h-8 w-8 ${getRiskScoreColor(scanResult.riskScore)}`}
                />
              </div>
            </div>

            <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
              <div className='flex items-center justify-between'>
                <div>
                  <p className='text-sm font-medium text-gray-600'>Critical Issues</p>
                  <p className='text-3xl font-bold text-red-600'>{scanResult.summary.critical}</p>
                </div>
                <ShieldExclamationIcon className='h-8 w-8 text-red-400' />
              </div>
            </div>

            <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
              <div className='flex items-center justify-between'>
                <div>
                  <p className='text-sm font-medium text-gray-600'>Scan Duration</p>
                  <p className='text-3xl font-bold text-gray-900'>
                    {Math.round(scanResult.duration / 1000)}s
                  </p>
                </div>
                <ClockIcon className='h-8 w-8 text-gray-400' />
              </div>
            </div>
          </div>

          {/* Severity Breakdown */}
          <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
            <h3 className='text-lg font-medium text-gray-900 mb-4'>Vulnerability Breakdown</h3>
            <div className='space-y-3'>
              {[
                {
                  severity: SecuritySeverity.CRITICAL,
                  count: scanResult.summary.critical,
                  label: 'Critical',
                },
                { severity: SecuritySeverity.HIGH, count: scanResult.summary.high, label: 'High' },
                {
                  severity: SecuritySeverity.MEDIUM,
                  count: scanResult.summary.medium,
                  label: 'Medium',
                },
                { severity: SecuritySeverity.LOW, count: scanResult.summary.low, label: 'Low' },
              ].map(({ severity, count, label }) => (
                <div key={severity} className='flex items-center justify-between'>
                  <div className='flex items-center space-x-3'>
                    {getSeverityIcon(severity)}
                    <span className='font-medium text-gray-900'>{label}</span>
                  </div>
                  <div className='flex items-center space-x-2'>
                    <span className='text-2xl font-bold text-gray-900'>{count}</span>
                    <div className='w-32 bg-gray-200 rounded-full h-2'>
                      <div
                        className={`h-2 rounded-full ${getSeverityColor(severity).split(' ')[2].replace('border-', 'bg-')}`}
                        style={{
                          width: `${scanResult.summary.total > 0 ? (count / scanResult.summary.total) * 100 : 0}%`,
                        }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Compliance Status */}
          <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
            <h3 className='text-lg font-medium text-gray-900 mb-4'>Compliance Status</h3>
            <div className='grid grid-cols-2 md:grid-cols-4 gap-4'>
              {[
                { name: 'OWASP', status: scanResult.complianceStatus.owasp },
                { name: 'GDPR', status: scanResult.complianceStatus.gdpr },
                { name: 'SOX', status: scanResult.complianceStatus.sox },
                { name: 'PCI DSS', status: scanResult.complianceStatus.pci },
              ].map(({ name, status }) => (
                <div
                  key={name}
                  className={`p-4 rounded-lg border ${status ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}
                >
                  <div className='flex items-center space-x-2'>
                    {status ? (
                      <CheckCircleIcon className='h-5 w-5 text-green-500' />
                    ) : (
                      <ExclamationTriangleIcon className='h-5 w-5 text-red-500' />
                    )}
                    <span className={`font-medium ${status ? 'text-green-900' : 'text-red-900'}`}>
                      {name}
                    </span>
                  </div>
                  <p className={`text-sm mt-1 ${status ? 'text-green-700' : 'text-red-700'}`}>
                    {status ? 'Compliant' : 'Non-compliant'}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Vulnerability List */}
          <div className='bg-white rounded-lg shadow-sm border border-gray-200'>
            <div className='px-6 py-4 border-b border-gray-200'>
              <h3 className='text-lg font-medium text-gray-900'>Detected Vulnerabilities</h3>
            </div>

            {scanResult.vulnerabilities.length === 0 ? (
              <div className='p-8 text-center'>
                <CheckCircleIcon className='mx-auto h-12 w-12 text-green-500' />
                <h4 className='mt-4 text-lg font-medium text-gray-900'>
                  No Vulnerabilities Detected
                </h4>
                <p className='mt-2 text-gray-600'>Your application appears to be secure!</p>
              </div>
            ) : (
              <div className='divide-y divide-gray-200'>
                {scanResult.vulnerabilities.map((vulnerability) => (
                  <div key={vulnerability.id} className='p-6 hover:bg-gray-50'>
                    <div className='flex items-start justify-between'>
                      <div className='flex-1'>
                        <div className='flex items-center space-x-3'>
                          {getSeverityIcon(vulnerability.severity)}
                          <div>
                            <h4 className='text-lg font-medium text-gray-900'>
                              {vulnerability.title}
                            </h4>
                            <div className='flex items-center space-x-4 mt-1'>
                              <span
                                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getSeverityColor(vulnerability.severity)}`}
                              >
                                {vulnerability.severity.toUpperCase()}
                              </span>
                              <span className='text-sm text-gray-500'>
                                {getVulnerabilityTypeLabel(vulnerability.type)}
                              </span>
                              {vulnerability.cvssScore && (
                                <span className='text-sm text-gray-500'>
                                  CVSS: {vulnerability.cvssScore}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>

                        <p className='text-gray-700 mt-2'>{vulnerability.description}</p>
                        <p className='text-sm text-gray-500 mt-1'>
                          <strong>Location:</strong> {vulnerability.location}
                        </p>

                        {showDetails && selectedVulnerability?.id === vulnerability.id && (
                          <div className='mt-4 space-y-3'>
                            <div>
                              <h5 className='font-medium text-gray-900'>Impact</h5>
                              <p className='text-sm text-gray-700'>{vulnerability.impact}</p>
                            </div>
                            <div>
                              <h5 className='font-medium text-gray-900'>Remediation</h5>
                              <p className='text-sm text-gray-700'>{vulnerability.remediation}</p>
                            </div>
                            {vulnerability.evidence && (
                              <div>
                                <h5 className='font-medium text-gray-900'>Evidence</h5>
                                <pre className='text-sm text-gray-700 bg-gray-100 p-2 rounded overflow-x-auto'>
                                  {vulnerability.evidence}
                                </pre>
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      <div className='ml-4 flex items-center space-x-2'>
                        <button
                          onClick={() => {
                            if (showDetails && selectedVulnerability?.id === vulnerability.id) {
                              setShowDetails(false);
                              setSelectedVulnerability(null);
                            } else {
                              setShowDetails(true);
                              setSelectedVulnerability(vulnerability);
                            }
                          }}
                          className='text-gray-400 hover:text-gray-600'
                        >
                          {showDetails && selectedVulnerability?.id === vulnerability.id ? (
                            <EyeSlashIcon className='h-5 w-5' />
                          ) : (
                            <EyeIcon className='h-5 w-5' />
                          )}
                        </button>

                        {vulnerability.status === 'detected' && (
                          <button
                            onClick={() => handleAcknowledge(vulnerability.id)}
                            className='px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200'
                          >
                            Acknowledge
                          </button>
                        )}

                        {vulnerability.status === 'acknowledged' && (
                          <span className='px-3 py-1 text-xs bg-yellow-100 text-yellow-700 rounded-md'>
                            Acknowledged
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
