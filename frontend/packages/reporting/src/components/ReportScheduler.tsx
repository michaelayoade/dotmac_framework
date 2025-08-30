/**
 * Report Scheduler Component
 * Leverages existing UI components and patterns
 */

import React, { useState, useCallback } from 'react';
import { Calendar, Clock, Users, Mail, FileDown } from 'lucide-react';
import { Button, Card, Input } from '@dotmac/primitives';
import type { ReportSchedule, ExportFormat, PortalVariant } from '../types';

interface ReportSchedulerProps {
  reportId: string;
  currentSchedule?: ReportSchedule;
  portal: PortalVariant;
  onScheduleUpdate: (schedule: ReportSchedule) => void;
  onClose: () => void;
  isOpen: boolean;
}

export const ReportScheduler: React.FC<ReportSchedulerProps> = ({
  reportId,
  currentSchedule,
  portal,
  onScheduleUpdate,
  onClose,
  isOpen
}) => {
  const [schedule, setSchedule] = useState<ReportSchedule>(
    currentSchedule || {
      enabled: false,
      frequency: 'weekly',
      time: '09:00',
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      recipients: [],
      format: ['pdf']
    }
  );

  const [recipientInput, setRecipientInput] = useState('');

  const handleFrequencyChange = useCallback((frequency: ReportSchedule['frequency']) => {
    setSchedule(prev => ({ ...prev, frequency }));
  }, []);

  const handleTimeChange = useCallback((time: string) => {
    setSchedule(prev => ({ ...prev, time }));
  }, []);

  const handleAddRecipient = useCallback(() => {
    if (recipientInput.trim() && !schedule.recipients.includes(recipientInput.trim())) {
      setSchedule(prev => ({
        ...prev,
        recipients: [...prev.recipients, recipientInput.trim()]
      }));
      setRecipientInput('');
    }
  }, [recipientInput, schedule.recipients]);

  const handleRemoveRecipient = useCallback((email: string) => {
    setSchedule(prev => ({
      ...prev,
      recipients: prev.recipients.filter(r => r !== email)
    }));
  }, []);

  const handleFormatToggle = useCallback((format: ExportFormat) => {
    setSchedule(prev => ({
      ...prev,
      format: prev.format.includes(format)
        ? prev.format.filter(f => f !== format)
        : [...prev.format, format]
    }));
  }, []);

  const handleSave = useCallback(() => {
    const nextRun = calculateNextRun(schedule);
    const updatedSchedule = { ...schedule };
    if (nextRun) {
      updatedSchedule.nextRun = nextRun;
    }
    onScheduleUpdate(updatedSchedule);
    onClose();
  }, [schedule, onScheduleUpdate, onClose]);

  const frequencyOptions = [
    { value: 'once', label: 'Once', icon: Calendar },
    { value: 'daily', label: 'Daily', icon: Clock },
    { value: 'weekly', label: 'Weekly', icon: Calendar },
    { value: 'monthly', label: 'Monthly', icon: Calendar },
    { value: 'quarterly', label: 'Quarterly', icon: Calendar },
    { value: 'yearly', label: 'Yearly', icon: Calendar }
  ] as const;

  const formatOptions: { value: ExportFormat; label: string }[] = [
    { value: 'pdf', label: 'PDF' },
    { value: 'csv', label: 'CSV' },
    { value: 'xlsx', label: 'Excel' },
    { value: 'json', label: 'JSON' }
  ];

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-auto bg-gray-500 bg-opacity-75 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-auto">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Schedule Report</h3>
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
          >
            ×
          </button>
        </div>
        <div className="p-6 space-y-6">
        {/* Enable/Disable Toggle */}
        <div className="flex items-center space-x-3">
          <input
            type="checkbox"
            id="enabled"
            checked={schedule.enabled}
            onChange={(e) => setSchedule(prev => ({ ...prev, enabled: e.target.checked }))}
            className="rounded border-gray-300"
          />
          <label htmlFor="enabled" className="text-sm font-medium text-gray-700">
            Enable scheduled reporting
          </label>
        </div>

        {schedule.enabled && (
          <>
            {/* Frequency Selection */}
            <div className="space-y-3">
              <label className="text-sm font-medium text-gray-700">Frequency</label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {frequencyOptions.map(({ value, label, icon: Icon }) => (
                  <Button
                    key={value}
                    variant={schedule.frequency === value ? "default" : "outline"}
                    size="sm"
                    onClick={() => handleFrequencyChange(value)}
                    className="justify-start"
                  >
                    <Icon className="h-4 w-4 mr-2" />
                    {label}
                  </Button>
                ))}
              </div>
            </div>

            {/* Time Selection */}
            <div className="space-y-3">
              <label className="text-sm font-medium text-gray-700">Time</label>
              <div className="flex items-center space-x-3">
                <Clock className="h-4 w-4 text-gray-400" />
                <Input
                  type="time"
                  value={schedule.time}
                  onChange={(e) => handleTimeChange(e.target.value)}
                  className="w-32"
                />
                <span className="text-sm text-gray-500">
                  {schedule.timezone}
                </span>
              </div>
            </div>

            {/* Day Selection for Weekly/Monthly */}
            {schedule.frequency === 'weekly' && (
              <div className="space-y-3">
                <label className="text-sm font-medium text-gray-700">Day of Week</label>
                <div className="grid grid-cols-7 gap-1">
                  {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day, index) => (
                    <Button
                      key={day}
                      variant={schedule.dayOfWeek === index ? "default" : "outline"}
                      size="sm"
                      onClick={() => setSchedule(prev => ({ ...prev, dayOfWeek: index }))}
                      className="p-2 text-xs"
                    >
                      {day}
                    </Button>
                  ))}
                </div>
              </div>
            )}

            {schedule.frequency === 'monthly' && (
              <div className="space-y-3">
                <label className="text-sm font-medium text-gray-700">Day of Month</label>
                <Input
                  type="number"
                  min="1"
                  max="31"
                  value={schedule.dayOfMonth || 1}
                  onChange={(e) => setSchedule(prev => ({
                    ...prev,
                    dayOfMonth: parseInt(e.target.value)
                  }))}
                  className="w-20"
                />
              </div>
            )}

            {/* Export Formats */}
            <div className="space-y-3">
              <label className="text-sm font-medium text-gray-700">Export Formats</label>
              <div className="grid grid-cols-2 gap-2">
                {formatOptions.map(({ value, label }) => (
                  <Button
                    key={value}
                    variant={schedule.format.includes(value) ? "default" : "outline"}
                    size="sm"
                    onClick={() => handleFormatToggle(value)}
                    className="justify-start"
                  >
                    <FileDown className="h-4 w-4 mr-2" />
                    {label}
                  </Button>
                ))}
              </div>
            </div>

            {/* Recipients */}
            <div className="space-y-3">
              <label className="text-sm font-medium text-gray-700">Recipients</label>
              <div className="flex items-center space-x-2">
                <Mail className="h-4 w-4 text-gray-400" />
                <Input
                  type="email"
                  placeholder="Enter email address"
                  value={recipientInput}
                  onChange={(e) => setRecipientInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleAddRecipient()}
                  className="flex-1"
                />
                <Button
                  type="button"
                  onClick={handleAddRecipient}
                  disabled={!recipientInput.trim()}
                  size="sm"
                >
                  Add
                </Button>
              </div>

              {schedule.recipients.length > 0 && (
                <div className="space-y-1">
                  {schedule.recipients.map((email, index) => (
                    <div key={index} className="flex items-center justify-between bg-gray-50 px-3 py-2 rounded-md">
                      <span className="text-sm text-gray-700">{email}</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveRecipient(email)}
                        className="text-red-500 hover:text-red-700"
                      >
                        ×
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Next Run Preview */}
            {schedule.enabled && (
              <Card className="p-4 bg-blue-50 border-blue-200">
                <div className="flex items-center space-x-2">
                  <Calendar className="h-4 w-4 text-blue-600" />
                  <span className="text-sm font-medium text-blue-800">Next Run:</span>
                  <span className="text-sm text-blue-700">
                    {calculateNextRun(schedule)?.toLocaleString() || 'Not scheduled'}
                  </span>
                </div>
              </Card>
            )}
          </>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end space-x-3 pt-4 border-t">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave}>
            Save Schedule
          </Button>
        </div>
        </div>
      </div>
    </div>
  );
};

// Helper function to calculate next run time
function calculateNextRun(schedule: ReportSchedule): Date | null {
  if (!schedule.enabled) return null;

  const now = new Date();
  const timeParts = schedule.time.split(':');
  const hours = parseInt(timeParts[0] || '0') || 0;
  const minutes = parseInt(timeParts[1] || '0') || 0;
  const nextRun = new Date();

  nextRun.setHours(hours, minutes, 0, 0);

  switch (schedule.frequency) {
    case 'once':
      return nextRun > now ? nextRun : null;

    case 'daily':
      if (nextRun <= now) {
        nextRun.setDate(nextRun.getDate() + 1);
      }
      return nextRun;

    case 'weekly':
      const targetDay = schedule.dayOfWeek || 1; // Default to Monday
      const currentDay = nextRun.getDay();
      let daysUntilNext = targetDay - currentDay;

      if (daysUntilNext <= 0 || (daysUntilNext === 0 && nextRun <= now)) {
        daysUntilNext += 7;
      }

      nextRun.setDate(nextRun.getDate() + daysUntilNext);
      return nextRun;

    case 'monthly':
      const targetDate = schedule.dayOfMonth || 1;
      nextRun.setDate(targetDate);

      if (nextRun <= now) {
        nextRun.setMonth(nextRun.getMonth() + 1);
      }
      return nextRun;

    case 'quarterly':
      const currentMonth = nextRun.getMonth();
      const quarterMonth = Math.floor(currentMonth / 3) * 3;
      nextRun.setMonth(quarterMonth + 3, 1);
      return nextRun;

    case 'yearly':
      if (nextRun <= now) {
        nextRun.setFullYear(nextRun.getFullYear() + 1);
      }
      return nextRun;

    default:
      return null;
  }
}
