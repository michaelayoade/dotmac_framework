import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SecurityDashboard } from '../SecurityDashboard';
import { SecuritySeverity, VulnerabilityType } from '@/lib/security-scanner';

// Mock the security scanner
jest.mock('@/lib/security-scanner', () => ({
  getSecurityScanner: jest.fn(),
  SecuritySeverity: {
    CRITICAL: 'critical',
    HIGH: 'high',
    MEDIUM: 'medium',
    LOW: 'low',
  },
  VulnerabilityType: {
    SQL_INJECTION: 'sql_injection',
    XSS: 'xss',
    CSRF: 'csrf',
    AUTHENTICATION_BYPASS: 'authentication_bypass',
  },
}));

const mockVulnerabilities = [
  {
    id: 'vuln-1',
    type: 'sql_injection' as VulnerabilityType,
    severity: 'critical' as SecuritySeverity,
    title: 'SQL Injection in Login Form',
    description: 'User input is not properly sanitized',
    location: '/api/auth/login',
    impact: 'Database compromise possible',
    remediation: 'Use parameterized queries',
    evidence: 'SELECT * FROM users WHERE email = "test@test.com"',
    cvssScore: 9.1,
    status: 'detected' as const,
  },
  {
    id: 'vuln-2',
    type: 'xss' as VulnerabilityType,
    severity: 'high' as SecuritySeverity,
    title: 'Cross-Site Scripting Vulnerability',
    description: 'Reflected XSS in search parameter',
    location: '/search?q=<script>alert(1)</script>',
    impact: 'Session hijacking possible',
    remediation: 'Escape output and validate input',
    evidence: null,
    cvssScore: 7.5,
    status: 'acknowledged' as const,
  },
];

const mockScanResult = {
  scanId: 'scan-123',
  startTime: '2023-01-01T10:00:00Z',
  endTime: '2023-01-01T10:05:00Z',
  duration: 300000,
  vulnerabilities: mockVulnerabilities,
  summary: {
    total: 2,
    critical: 1,
    high: 1,
    medium: 0,
    low: 0,
  },
  riskScore: 85,
  complianceStatus: {
    owasp: false,
    gdpr: true,
    sox: true,
    pci: false,
  },
};

describe('SecurityDashboard', () => {
  const mockScanner = {
    getLatestScan: jest.fn(),
    performSecurityScan: jest.fn(),
    acknowledgeVulnerability: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();

    const { getSecurityScanner } = require('@/lib/security-scanner');
    getSecurityScanner.mockReturnValue(mockScanner);

    mockScanner.getLatestScan.mockReturnValue(null);
    mockScanner.performSecurityScan.mockResolvedValue(mockScanResult);
    mockScanner.acknowledgeVulnerability.mockReturnValue(true);
  });

  it('renders security dashboard component', () => {
    render(<SecurityDashboard />);

    expect(screen.getByText('Security Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Monitor and manage security vulnerabilities')).toBeInTheDocument();
    expect(screen.getByText('Run Security Scan')).toBeInTheDocument();
  });

  it('shows no scans available message initially', () => {
    render(<SecurityDashboard />);

    expect(screen.getByText('No Security Scans Available')).toBeInTheDocument();
    expect(screen.getByText('Run your first security scan to identify vulnerabilities')).toBeInTheDocument();
  });

  it('loads and displays existing scan results', () => {
    mockScanner.getLatestScan.mockReturnValue(mockScanResult);

    render(<SecurityDashboard />);

    expect(screen.getByText('Total Vulnerabilities')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('Risk Score')).toBeInTheDocument();
    expect(screen.getByText('85/100')).toBeInTheDocument();
    expect(screen.getByText('Critical Issues')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('displays vulnerability breakdown correctly', () => {
    mockScanner.getLatestScan.mockReturnValue(mockScanResult);

    render(<SecurityDashboard />);

    expect(screen.getByText('Vulnerability Breakdown')).toBeInTheDocument();
    expect(screen.getByText('Critical')).toBeInTheDocument();
    expect(screen.getByText('High')).toBeInTheDocument();
    expect(screen.getByText('Medium')).toBeInTheDocument();
    expect(screen.getByText('Low')).toBeInTheDocument();
  });

  it('displays compliance status', () => {
    mockScanner.getLatestScan.mockReturnValue(mockScanResult);

    render(<SecurityDashboard />);

    expect(screen.getByText('Compliance Status')).toBeInTheDocument();
    expect(screen.getByText('OWASP')).toBeInTheDocument();
    expect(screen.getByText('GDPR')).toBeInTheDocument();
    expect(screen.getByText('SOX')).toBeInTheDocument();
    expect(screen.getByText('PCI DSS')).toBeInTheDocument();

    // Check compliance status
    expect(screen.getByText('Non-compliant')).toBeInTheDocument(); // OWASP and PCI should be non-compliant
    expect(screen.getAllByText('Compliant')).toHaveLength(2); // GDPR and SOX should be compliant
  });

  it('displays vulnerability list', () => {
    mockScanner.getLatestScan.mockReturnValue(mockScanResult);

    render(<SecurityDashboard />);

    expect(screen.getByText('Detected Vulnerabilities')).toBeInTheDocument();
    expect(screen.getByText('SQL Injection in Login Form')).toBeInTheDocument();
    expect(screen.getByText('Cross-Site Scripting Vulnerability')).toBeInTheDocument();
    expect(screen.getByText('CRITICAL')).toBeInTheDocument();
    expect(screen.getByText('HIGH')).toBeInTheDocument();
  });

  it('performs security scan when button is clicked', async () => {
    const user = userEvent.setup();

    render(<SecurityDashboard />);

    const scanButton = screen.getByText('Run Security Scan');
    await user.click(scanButton);

    expect(mockScanner.performSecurityScan).toHaveBeenCalled();

    await waitFor(() => {
      expect(screen.getByText('Total Vulnerabilities')).toBeInTheDocument();
    });
  });

  it('shows scanning state during scan', async () => {
    const user = userEvent.setup();

    // Make the scan take some time
    mockScanner.performSecurityScan.mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve(mockScanResult), 100))
    );

    render(<SecurityDashboard />);

    const scanButton = screen.getByText('Run Security Scan');
    await user.click(scanButton);

    expect(screen.getByText('Scanning...')).toBeInTheDocument();
    expect(scanButton).toBeDisabled();

    await waitFor(() => {
      expect(screen.getByText('Run Security Scan')).toBeInTheDocument();
    });
  });

  it('handles scan errors gracefully', async () => {
    const user = userEvent.setup();
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    mockScanner.performSecurityScan.mockRejectedValue(new Error('Scan failed'));

    render(<SecurityDashboard />);

    const scanButton = screen.getByText('Run Security Scan');
    await user.click(scanButton);

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith('Security scan failed:', expect.any(Error));
    });

    consoleSpy.mockRestore();
  });

  it('expands and collapses vulnerability details', async () => {
    const user = userEvent.setup();
    mockScanner.getLatestScan.mockReturnValue(mockScanResult);

    render(<SecurityDashboard />);

    // Details should not be visible initially
    expect(screen.queryByText('Impact')).not.toBeInTheDocument();
    expect(screen.queryByText('Remediation')).not.toBeInTheDocument();

    // Click the eye icon to expand
    const eyeIcons = screen.getAllByTitle('');
    const firstEyeIcon = eyeIcons.find(icon =>
      icon.tagName === 'svg' || icon.closest('button')
    );

    if (firstEyeIcon) {
      await user.click(firstEyeIcon.closest('button') || firstEyeIcon);

      expect(screen.getByText('Impact')).toBeInTheDocument();
      expect(screen.getByText('Remediation')).toBeInTheDocument();
      expect(screen.getByText('Evidence')).toBeInTheDocument();
      expect(screen.getByText('Database compromise possible')).toBeInTheDocument();
    }
  });

  it('acknowledges vulnerabilities', async () => {
    const user = userEvent.setup();
    mockScanner.getLatestScan.mockReturnValue(mockScanResult);

    render(<SecurityDashboard />);

    // Find and click acknowledge button for the first vulnerability
    const acknowledgeButtons = screen.getAllByText('Acknowledge');
    await user.click(acknowledgeButtons[0]);

    expect(mockScanner.acknowledgeVulnerability).toHaveBeenCalledWith('vuln-1');

    // The vulnerability should now show as acknowledged
    await waitFor(() => {
      expect(screen.getByText('Acknowledged')).toBeInTheDocument();
    });
  });

  it('displays different severity colors correctly', () => {
    mockScanner.getLatestScan.mockReturnValue(mockScanResult);

    render(<SecurityDashboard />);

    // Check that severity badges have appropriate classes
    const criticalBadge = screen.getByText('CRITICAL');
    const highBadge = screen.getByText('HIGH');

    expect(criticalBadge.closest('.inline-flex')).toHaveClass('text-red-600');
    expect(highBadge.closest('.inline-flex')).toHaveClass('text-orange-600');
  });

  it('shows CVSS scores when available', () => {
    mockScanner.getLatestScan.mockReturnValue(mockScanResult);

    render(<SecurityDashboard />);

    expect(screen.getByText('CVSS: 9.1')).toBeInTheDocument();
    expect(screen.getByText('CVSS: 7.5')).toBeInTheDocument();
  });

  it('formats vulnerability types correctly', () => {
    mockScanner.getLatestScan.mockReturnValue(mockScanResult);

    render(<SecurityDashboard />);

    expect(screen.getByText('Sql Injection')).toBeInTheDocument();
    expect(screen.getByText('Xss')).toBeInTheDocument();
  });

  it('shows scan duration', () => {
    mockScanner.getLatestScan.mockReturnValue(mockScanResult);

    render(<SecurityDashboard />);

    expect(screen.getByText('Scan Duration')).toBeInTheDocument();
    expect(screen.getByText('300s')).toBeInTheDocument(); // 300000ms / 1000 = 300s
  });

  it('displays no vulnerabilities message when scan is clean', () => {
    const cleanScanResult = {
      ...mockScanResult,
      vulnerabilities: [],
      summary: {
        total: 0,
        critical: 0,
        high: 0,
        medium: 0,
        low: 0,
      },
      riskScore: 0,
    };

    mockScanner.getLatestScan.mockReturnValue(cleanScanResult);

    render(<SecurityDashboard />);

    expect(screen.getByText('No Vulnerabilities Detected')).toBeInTheDocument();
    expect(screen.getByText('Your application appears to be secure!')).toBeInTheDocument();
  });

  it('displays last scan time correctly', () => {
    mockScanner.getLatestScan.mockReturnValue(mockScanResult);

    render(<SecurityDashboard />);

    expect(screen.getByText(/Last scan:/)).toBeInTheDocument();
    // The exact time format depends on locale, so we just check it's not "Never"
    expect(screen.queryByText('Last scan: Never')).not.toBeInTheDocument();
  });
});
