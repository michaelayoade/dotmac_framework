/**
 * Reports Management - Focused component for financial reports
 * Handles report generation, downloading, and status tracking
 */

'use client';

import { FileTextIcon, RefreshCwIcon, CheckCircleIcon, XCircleIcon, ClockIcon } from 'lucide-react';
import type { Report } from '../../../types/billing';

interface ReportsManagementProps {
  reports: Report[];
  onReportAction?: (action: string, reportId: string) => void;
  onGenerateReport?: () => void;
}

export function ReportsManagement({ 
  reports, 
  onReportAction,
  onGenerateReport 
}: ReportsManagementProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ready':
        return 'bg-green-100 text-green-800';
      case 'generating':
        return 'bg-yellow-100 text-yellow-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ready':
        return CheckCircleIcon;
      case 'generating':
        return RefreshCwIcon;
      case 'failed':
        return XCircleIcon;
      default:
        return ClockIcon;
    }
  };

  return (
    <div className='bg-white rounded-lg shadow-sm border border-gray-200'>
      <div className='p-6 border-b border-gray-200'>
        <div className='flex items-center justify-between'>
          <div>
            <h3 className='text-lg font-semibold text-gray-900'>Financial Reports</h3>
            <p className='text-sm text-gray-500'>
              Generate and download comprehensive financial reports
            </p>
          </div>
          {onGenerateReport && (
            <button 
              onClick={onGenerateReport}
              className='px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium'
            >
              Generate Report
            </button>
          )}
        </div>
      </div>

      <div className='p-6 space-y-4'>
        {reports.map((report) => (
          <ReportCard 
            key={report.id} 
            report={report} 
            onAction={onReportAction}
          />
        ))}
      </div>
    </div>
  );
}

interface ReportCardProps {
  report: Report;
  onAction?: (action: string, reportId: string) => void;
}

function ReportCard({ report, onAction }: ReportCardProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ready':
        return 'bg-green-100 text-green-800';
      case 'generating':
        return 'bg-yellow-100 text-yellow-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ready':
        return CheckCircleIcon;
      case 'generating':
        return RefreshCwIcon;
      case 'failed':
        return XCircleIcon;
      default:
        return ClockIcon;
    }
  };

  const StatusIcon = getStatusIcon(report.status);

  return (
    <div className='bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow'>
      <div className='flex items-center justify-between'>
        <div className='flex items-center space-x-4'>
          <div className='flex-shrink-0'>
            <div className='w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center'>
              <FileTextIcon className='w-6 h-6 text-blue-600' />
            </div>
          </div>
          <div>
            <h3 className='text-lg font-semibold text-gray-900'>{report.name}</h3>
            <p className='text-sm text-gray-500'>{report.description}</p>
            <div className='mt-2 flex items-center space-x-4 text-xs text-gray-500'>
              <span>Type: {report.type}</span>
              <span>•</span>
              <span>Frequency: {report.frequency}</span>
              <span>•</span>
              <span>Format: {report.format}</span>
              {report.size && (
                <>
                  <span>•</span>
                  <span>Size: {report.size}</span>
                </>
              )}
            </div>
          </div>
        </div>
        <div className='flex items-center space-x-3'>
          <span
            className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(report.status)}`}
          >
            <StatusIcon
              className={`w-3 h-3 mr-1 ${report.status === 'generating' ? 'animate-spin' : ''}`}
            />
            {report.status}
          </span>
          {report.status === 'ready' && onAction && (
            <button 
              onClick={() => onAction('download', report.id)}
              className='px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium'
            >
              Download
            </button>
          )}
        </div>
      </div>

      <div className='mt-4 text-sm text-gray-500'>
        Last generated: {new Date(report.lastGenerated).toLocaleString()}
      </div>
    </div>
  );
}