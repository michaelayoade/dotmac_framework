import React, { useState } from 'react';
import { cn } from '@dotmac/primitives/utils/cn';
import type { ReportBuilderProps, AnalyticsReport, FilterConfig } from '../../types';

const REPORT_FORMATS = [
  { value: 'pdf', label: 'PDF Document', description: 'Formatted report with charts and tables' },
  { value: 'excel', label: 'Excel Spreadsheet', description: 'Data export with multiple sheets' },
  { value: 'csv', label: 'CSV Data', description: 'Raw data in comma-separated format' },
  { value: 'json', label: 'JSON Data', description: 'Structured data export' },
  { value: 'html', label: 'HTML Report', description: 'Web-viewable report' },
] as const;

const FREQUENCIES = [
  { value: 'daily', label: 'Daily', description: 'Generated every day' },
  { value: 'weekly', label: 'Weekly', description: 'Generated every week' },
  { value: 'monthly', label: 'Monthly', description: 'Generated every month' },
  { value: 'quarterly', label: 'Quarterly', description: 'Generated every quarter' },
] as const;

export const ReportBuilder: React.FC<ReportBuilderProps> = ({
  dashboardId,
  initialReport,
  onSave,
  onCancel,
  className,
}) => {
  const [report, setReport] = useState<Partial<AnalyticsReport>>({
    type: 'ad_hoc',
    format: 'pdf',
    isActive: true,
    recipients: [],
    ...initialReport,
  });

  const [recipients, setRecipients] = useState<string>(
    report.recipients?.join(', ') || ''
  );

  const [scheduleEnabled, setScheduleEnabled] = useState(
    report.type === 'scheduled' && !!report.schedule
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!report.name?.trim()) return;

    const finalReport: AnalyticsReport = {
      id: report.id || `report-${Date.now()}`,
      name: report.name,
      description: report.description,
      type: scheduleEnabled ? 'scheduled' : 'ad_hoc',
      format: report.format || 'pdf',
      dashboardId: dashboardId || report.dashboardId,
      recipients: recipients.split(',').map(email => email.trim()).filter(Boolean),
      filters: report.filters || [],
      template: report.template,
      isActive: report.isActive ?? true,
      ...(scheduleEnabled && report.schedule && {
        schedule: report.schedule,
        nextRun: new Date() // This would be calculated based on schedule
      }),
    };

    onSave?.(finalReport);
  };

  const updateSchedule = (field: string, value: any) => {
    setReport(prev => ({
      ...prev,
      schedule: {
        frequency: 'daily',
        time: '09:00',
        timezone: 'UTC',
        ...prev.schedule,
        [field]: value,
      }
    }));
  };

  return (
    <div className={cn('bg-white rounded-lg border p-6', className)}>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">
          {initialReport?.id ? 'Edit Report' : 'Create Report'}
        </h3>
        <button
          onClick={onCancel}
          className="text-gray-500 hover:text-gray-700"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Information */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Report Name *
            </label>
            <input
              type="text"
              value={report.name || ''}
              onChange={(e) => setReport({ ...report, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
              placeholder="Enter report name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Format
            </label>
            <select
              value={report.format || 'pdf'}
              onChange={(e) => setReport({ ...report, format: e.target.value as any })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {REPORT_FORMATS.map(format => (
                <option key={format.value} value={format.value}>
                  {format.label}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              {REPORT_FORMATS.find(f => f.value === report.format)?.description}
            </p>
          </div>
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description
          </label>
          <textarea
            value={report.description || ''}
            onChange={(e) => setReport({ ...report, description: e.target.value })}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Optional report description"
          />
        </div>

        {/* Recipients */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Recipients *
          </label>
          <input
            type="text"
            value={recipients}
            onChange={(e) => setRecipients(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
            placeholder="Enter email addresses separated by commas"
          />
          <p className="text-xs text-gray-500 mt-1">
            Enter multiple email addresses separated by commas
          </p>
        </div>

        {/* Schedule Toggle */}
        <div className="flex items-center">
          <input
            type="checkbox"
            id="schedule-enabled"
            checked={scheduleEnabled}
            onChange={(e) => setScheduleEnabled(e.target.checked)}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <label htmlFor="schedule-enabled" className="ml-2 text-sm font-medium text-gray-700">
            Schedule this report to run automatically
          </label>
        </div>

        {/* Schedule Configuration */}
        {scheduleEnabled && (
          <div className="p-4 border border-gray-200 rounded-lg bg-gray-50">
            <h4 className="text-sm font-medium text-gray-900 mb-3">Schedule Configuration</h4>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Frequency
                </label>
                <select
                  value={report.schedule?.frequency || 'daily'}
                  onChange={(e) => updateSchedule('frequency', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {FREQUENCIES.map(freq => (
                    <option key={freq.value} value={freq.value}>
                      {freq.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Time
                </label>
                <input
                  type="time"
                  value={report.schedule?.time || '09:00'}
                  onChange={(e) => updateSchedule('time', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Timezone
                </label>
                <select
                  value={report.schedule?.timezone || 'UTC'}
                  onChange={(e) => updateSchedule('timezone', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="UTC">UTC</option>
                  <option value="America/New_York">Eastern Time</option>
                  <option value="America/Chicago">Central Time</option>
                  <option value="America/Denver">Mountain Time</option>
                  <option value="America/Los_Angeles">Pacific Time</option>
                  <option value="Europe/London">GMT</option>
                </select>
              </div>
            </div>

            {/* Weekly options */}
            {report.schedule?.frequency === 'weekly' && (
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Days of Week
                </label>
                <div className="flex flex-wrap gap-2">
                  {['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'].map((day, index) => (
                    <label key={day} className="flex items-center">
                      <input
                        type="checkbox"
                        checked={(report.schedule?.daysOfWeek || []).includes(index)}
                        onChange={(e) => {
                          const days = report.schedule?.daysOfWeek || [];
                          const newDays = e.target.checked
                            ? [...days, index]
                            : days.filter(d => d !== index);
                          updateSchedule('daysOfWeek', newDays);
                        }}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <span className="ml-1 text-sm text-gray-700">{day.slice(0, 3)}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {/* Monthly options */}
            {report.schedule?.frequency === 'monthly' && (
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Day of Month
                </label>
                <input
                  type="number"
                  min="1"
                  max="31"
                  value={report.schedule?.dayOfMonth || 1}
                  onChange={(e) => updateSchedule('dayOfMonth', parseInt(e.target.value))}
                  className="w-20 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Day of the month (1-31)
                </p>
              </div>
            )}
          </div>
        )}

        {/* Active Toggle */}
        <div className="flex items-center">
          <input
            type="checkbox"
            id="report-active"
            checked={report.isActive ?? true}
            onChange={(e) => setReport({ ...report, isActive: e.target.checked })}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <label htmlFor="report-active" className="ml-2 text-sm font-medium text-gray-700">
            Report is active
          </label>
        </div>

        {/* Actions */}
        <div className="flex justify-end space-x-3 pt-6 border-t border-gray-200">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            {initialReport?.id ? 'Update Report' : 'Create Report'}
          </button>
        </div>
      </form>
    </div>
  );
};
