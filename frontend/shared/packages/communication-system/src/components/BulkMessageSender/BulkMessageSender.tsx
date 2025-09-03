'use client';

import React, { useState, useCallback, useMemo } from 'react';
import {
  Upload,
  Send,
  X,
  FileText,
  Users,
  Calendar,
  AlertCircle,
  CheckCircle,
  Clock,
  Plus,
  Minus,
  Target,
  Filter,
  Download,
  Play,
  Pause,
  Eye,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { CommunicationTemplate, BulkCommunicationJob } from '../../types';
import { useCommunicationSystem } from '../../hooks/useCommunicationSystem';
import { TemplateManager } from '../TemplateManager';

interface BulkMessageSenderProps {
  tenantId?: string;
  userId?: string;
  onJobCreated?: (job: BulkCommunicationJob) => void;
  onJobComplete?: (job: BulkCommunicationJob) => void;
  className?: string;
  defaultChannel?: string;
  maxRecipients?: number;
}

interface RecipientData {
  email?: string;
  phone?: string;
  name?: string;
  variables?: Record<string, any>;
}

export function BulkMessageSender({
  tenantId,
  userId,
  onJobCreated,
  onJobComplete,
  className = '',
  defaultChannel = 'email',
  maxRecipients = 10000,
}: BulkMessageSenderProps) {
  const [selectedTemplate, setSelectedTemplate] = useState<CommunicationTemplate | null>(null);
  const [recipients, setRecipients] = useState<RecipientData[]>([]);
  const [csvData, setCsvData] = useState<string>('');
  const [jobName, setJobName] = useState('');
  const [scheduledAt, setScheduledAt] = useState<string>('');
  const [priority, setPriority] = useState<'low' | 'medium' | 'high' | 'critical'>('medium');
  const [currentStep, setCurrentStep] = useState<'template' | 'recipients' | 'schedule' | 'review'>(
    'template'
  );
  const [uploadMode, setUploadMode] = useState<'manual' | 'csv'>('manual');
  const [previewRecipient, setPreviewRecipient] = useState<RecipientData | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isProcessing, setIsProcessing] = useState(false);

  const communication = useCommunicationSystem({
    tenantId,
    userId,
    enableRealtime: true,
  });

  const parseCsvData = useCallback(
    (csvText: string): RecipientData[] => {
      const lines = csvText.trim().split('\n');
      if (lines.length < 2) return [];

      const headers = lines[0].split(',').map((h) => h.trim().toLowerCase());
      const data: RecipientData[] = [];

      for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',').map((v) => v.trim());
        const recipient: RecipientData = { variables: {} };

        headers.forEach((header, index) => {
          const value = values[index] || '';

          switch (header) {
            case 'email':
              recipient.email = value;
              break;
            case 'phone':
              recipient.phone = value;
              break;
            case 'name':
              recipient.name = value;
              break;
            default:
              if (recipient.variables) {
                recipient.variables[header] = value;
              }
              break;
          }
        });

        // Validate recipient has required contact info
        if (selectedTemplate?.channel === 'email' && recipient.email) {
          data.push(recipient);
        } else if (selectedTemplate?.channel === 'sms' && recipient.phone) {
          data.push(recipient);
        } else if (recipient.email || recipient.phone) {
          data.push(recipient);
        }
      }

      return data;
    },
    [selectedTemplate]
  );

  const processedRecipients = useMemo(() => {
    if (uploadMode === 'csv' && csvData) {
      return parseCsvData(csvData);
    }
    return recipients;
  }, [uploadMode, csvData, recipients, parseCsvData]);

  const validateStep = useCallback(
    (step: string): boolean => {
      const newErrors: Record<string, string> = {};

      switch (step) {
        case 'template':
          if (!selectedTemplate) {
            newErrors.template = 'Please select a template';
          }
          break;

        case 'recipients':
          if (processedRecipients.length === 0) {
            newErrors.recipients = 'Please add recipients';
          }
          if (processedRecipients.length > maxRecipients) {
            newErrors.recipients = `Maximum ${maxRecipients} recipients allowed`;
          }

          // Validate recipients have required contact info
          const invalidRecipients = processedRecipients.filter((r) => {
            if (selectedTemplate?.channel === 'email' && !r.email) return true;
            if (selectedTemplate?.channel === 'sms' && !r.phone) return true;
            return false;
          });

          if (invalidRecipients.length > 0) {
            newErrors.recipients = `${invalidRecipients.length} recipients missing required contact info`;
          }
          break;

        case 'schedule':
          if (!jobName.trim()) {
            newErrors.jobName = 'Job name is required';
          }
          if (scheduledAt && new Date(scheduledAt) <= new Date()) {
            newErrors.scheduledAt = 'Scheduled time must be in the future';
          }
          break;
      }

      setErrors(newErrors);
      return Object.keys(newErrors).length === 0;
    },
    [selectedTemplate, processedRecipients, maxRecipients, jobName, scheduledAt]
  );

  const nextStep = useCallback(() => {
    if (validateStep(currentStep)) {
      const steps = ['template', 'recipients', 'schedule', 'review'];
      const currentIndex = steps.indexOf(currentStep);
      if (currentIndex < steps.length - 1) {
        setCurrentStep(steps[currentIndex + 1] as any);
      }
    }
  }, [currentStep, validateStep]);

  const prevStep = useCallback(() => {
    const steps = ['template', 'recipients', 'schedule', 'review'];
    const currentIndex = steps.indexOf(currentStep);
    if (currentIndex > 0) {
      setCurrentStep(steps[currentIndex - 1] as any);
    }
  }, [currentStep]);

  const addRecipient = useCallback(() => {
    setRecipients((prev) => [...prev, { variables: {} }]);
  }, []);

  const updateRecipient = useCallback((index: number, updates: Partial<RecipientData>) => {
    setRecipients((prev) => prev.map((r, i) => (i === index ? { ...r, ...updates } : r)));
  }, []);

  const removeRecipient = useCallback((index: number) => {
    setRecipients((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const generatePreview = useCallback(
    (recipient: RecipientData): string => {
      if (!selectedTemplate) return '';

      let preview = selectedTemplate.body;

      // Replace template variables with recipient data
      selectedTemplate.variables.forEach((variable) => {
        const value =
          recipient.variables?.[variable] ||
          recipient[variable as keyof RecipientData] ||
          `[${variable}]`;
        preview = preview.replace(new RegExp(`\\{\\{${variable}\\}\\}`, 'g'), String(value));
      });

      return preview;
    },
    [selectedTemplate]
  );

  const handleSubmit = useCallback(async () => {
    if (!validateStep('review') || !selectedTemplate) return;

    setIsProcessing(true);

    try {
      // Prepare messages for bulk sending
      const messages = processedRecipients.map((recipient) => ({
        templateId: selectedTemplate.id,
        channel: selectedTemplate.channel,
        recipient: (selectedTemplate.channel === 'email' ? recipient.email : recipient.phone) || '',
        subject: selectedTemplate.subject,
        variables: recipient.variables,
        priority,
        ...(scheduledAt && { scheduledAt: new Date(scheduledAt) }),
        metadata: {
          recipientName: recipient.name,
          jobName,
          bulkSend: true,
        },
      }));

      const job = await communication.sendBulkMessages(messages);
      onJobCreated?.(job);

      // Reset form
      setSelectedTemplate(null);
      setRecipients([]);
      setCsvData('');
      setJobName('');
      setScheduledAt('');
      setCurrentStep('template');
    } catch (error) {
      console.error('Failed to create bulk message job:', error);
    } finally {
      setIsProcessing(false);
    }
  }, [
    validateStep,
    selectedTemplate,
    processedRecipients,
    priority,
    scheduledAt,
    jobName,
    communication,
    onJobCreated,
  ]);

  const renderStepContent = () => {
    switch (currentStep) {
      case 'template':
        return (
          <div className='space-y-6'>
            <div>
              <h3 className='text-lg font-medium text-gray-900 mb-4'>Select Template</h3>
              <TemplateManager
                tenantId={tenantId}
                userId={userId}
                onTemplateSelect={setSelectedTemplate}
                compact={true}
                filterByChannel={defaultChannel}
              />
            </div>

            {selectedTemplate && (
              <div className='bg-blue-50 border border-blue-200 rounded-lg p-4'>
                <div className='flex items-center space-x-2 mb-2'>
                  <CheckCircle className='w-5 h-5 text-blue-600' />
                  <span className='font-medium text-blue-900'>Selected Template</span>
                </div>
                <p className='text-blue-800'>{selectedTemplate.name}</p>
                <p className='text-sm text-blue-600 mt-1'>
                  Channel: {selectedTemplate.channel} | Variables:{' '}
                  {selectedTemplate.variables.join(', ')}
                </p>
              </div>
            )}

            {errors.template && (
              <div className='text-red-600 text-sm flex items-center'>
                <AlertCircle className='w-4 h-4 mr-1' />
                {errors.template}
              </div>
            )}
          </div>
        );

      case 'recipients':
        return (
          <div className='space-y-6'>
            <div>
              <h3 className='text-lg font-medium text-gray-900 mb-4'>Add Recipients</h3>

              <div className='flex space-x-4 mb-4'>
                <button
                  onClick={() => setUploadMode('manual')}
                  className={`px-4 py-2 rounded-lg transition-colors ${
                    uploadMode === 'manual'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  Manual Entry
                </button>
                <button
                  onClick={() => setUploadMode('csv')}
                  className={`px-4 py-2 rounded-lg transition-colors ${
                    uploadMode === 'csv'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  CSV Upload
                </button>
              </div>

              {uploadMode === 'manual' ? (
                <div className='space-y-4'>
                  {recipients.map((recipient, index) => (
                    <div key={index} className='border border-gray-200 rounded-lg p-4'>
                      <div className='flex items-center justify-between mb-3'>
                        <span className='text-sm font-medium text-gray-700'>
                          Recipient {index + 1}
                        </span>
                        <button
                          onClick={() => removeRecipient(index)}
                          className='text-red-600 hover:text-red-700'
                        >
                          <X className='w-4 h-4' />
                        </button>
                      </div>

                      <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
                        <div>
                          <label className='block text-sm text-gray-600 mb-1'>Name</label>
                          <input
                            type='text'
                            value={recipient.name || ''}
                            onChange={(e) => updateRecipient(index, { name: e.target.value })}
                            className='w-full px-3 py-2 border border-gray-300 rounded-md text-sm'
                          />
                        </div>

                        {selectedTemplate?.channel === 'email' && (
                          <div>
                            <label className='block text-sm text-gray-600 mb-1'>Email *</label>
                            <input
                              type='email'
                              value={recipient.email || ''}
                              onChange={(e) => updateRecipient(index, { email: e.target.value })}
                              className='w-full px-3 py-2 border border-gray-300 rounded-md text-sm'
                              required
                            />
                          </div>
                        )}

                        {selectedTemplate?.channel === 'sms' && (
                          <div>
                            <label className='block text-sm text-gray-600 mb-1'>Phone *</label>
                            <input
                              type='tel'
                              value={recipient.phone || ''}
                              onChange={(e) => updateRecipient(index, { phone: e.target.value })}
                              className='w-full px-3 py-2 border border-gray-300 rounded-md text-sm'
                              required
                            />
                          </div>
                        )}
                      </div>

                      {selectedTemplate?.variables.length > 0 && (
                        <div className='mt-4'>
                          <label className='block text-sm font-medium text-gray-700 mb-2'>
                            Template Variables
                          </label>
                          <div className='grid grid-cols-1 md:grid-cols-2 gap-3'>
                            {selectedTemplate.variables.map((variable) => (
                              <div key={variable}>
                                <label className='block text-xs text-gray-600 mb-1'>
                                  {variable}
                                </label>
                                <input
                                  type='text'
                                  value={recipient.variables?.[variable] || ''}
                                  onChange={(e) =>
                                    updateRecipient(index, {
                                      variables: {
                                        ...recipient.variables,
                                        [variable]: e.target.value,
                                      },
                                    })
                                  }
                                  className='w-full px-3 py-2 border border-gray-300 rounded-md text-sm'
                                />
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}

                  <button
                    onClick={addRecipient}
                    className='flex items-center space-x-2 px-4 py-2 border-2 border-dashed border-gray-300 rounded-lg hover:border-gray-400 transition-colors'
                  >
                    <Plus className='w-4 h-4' />
                    <span>Add Recipient</span>
                  </button>
                </div>
              ) : (
                <div className='space-y-4'>
                  <div>
                    <label className='block text-sm font-medium text-gray-700 mb-2'>CSV Data</label>
                    <div className='text-xs text-gray-500 mb-2'>
                      Format: name,email,phone,variable1,variable2...
                    </div>
                    <textarea
                      value={csvData}
                      onChange={(e) => setCsvData(e.target.value)}
                      className='w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono'
                      rows={10}
                      placeholder='name,email,phone,company,amount
John Doe,john@example.com,+1234567890,Acme Corp,100
Jane Smith,jane@example.com,+1987654321,Beta Inc,200'
                    />
                  </div>

                  {csvData && (
                    <div className='text-sm text-gray-600'>
                      Parsed {processedRecipients.length} valid recipients
                    </div>
                  )}
                </div>
              )}
            </div>

            {errors.recipients && (
              <div className='text-red-600 text-sm flex items-center'>
                <AlertCircle className='w-4 h-4 mr-1' />
                {errors.recipients}
              </div>
            )}
          </div>
        );

      case 'schedule':
        return (
          <div className='space-y-6'>
            <h3 className='text-lg font-medium text-gray-900'>Schedule & Settings</h3>

            <div className='space-y-4'>
              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>Job Name *</label>
                <input
                  type='text'
                  value={jobName}
                  onChange={(e) => setJobName(e.target.value)}
                  className='w-full px-3 py-2 border border-gray-300 rounded-lg'
                  placeholder='Enter job name'
                />
                {errors.jobName && <p className='mt-1 text-sm text-red-600'>{errors.jobName}</p>}
              </div>

              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>Priority</label>
                <select
                  value={priority}
                  onChange={(e) => setPriority(e.target.value as any)}
                  className='w-full px-3 py-2 border border-gray-300 rounded-lg'
                >
                  <option value='low'>Low</option>
                  <option value='medium'>Medium</option>
                  <option value='high'>High</option>
                  <option value='critical'>Critical</option>
                </select>
              </div>

              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>
                  Schedule (Optional)
                </label>
                <input
                  type='datetime-local'
                  value={scheduledAt}
                  onChange={(e) => setScheduledAt(e.target.value)}
                  className='w-full px-3 py-2 border border-gray-300 rounded-lg'
                  min={new Date().toISOString().slice(0, 16)}
                />
                <p className='mt-1 text-xs text-gray-500'>Leave empty to send immediately</p>
                {errors.scheduledAt && (
                  <p className='mt-1 text-sm text-red-600'>{errors.scheduledAt}</p>
                )}
              </div>
            </div>
          </div>
        );

      case 'review':
        return (
          <div className='space-y-6'>
            <h3 className='text-lg font-medium text-gray-900'>Review & Send</h3>

            <div className='space-y-4'>
              <div className='bg-gray-50 rounded-lg p-4'>
                <h4 className='font-medium text-gray-900 mb-3'>Job Summary</h4>
                <div className='grid grid-cols-1 md:grid-cols-2 gap-4 text-sm'>
                  <div>
                    <span className='text-gray-600'>Job Name:</span>
                    <span className='ml-2 font-medium'>{jobName}</span>
                  </div>
                  <div>
                    <span className='text-gray-600'>Template:</span>
                    <span className='ml-2 font-medium'>{selectedTemplate?.name}</span>
                  </div>
                  <div>
                    <span className='text-gray-600'>Recipients:</span>
                    <span className='ml-2 font-medium'>{processedRecipients.length}</span>
                  </div>
                  <div>
                    <span className='text-gray-600'>Channel:</span>
                    <span className='ml-2 font-medium capitalize'>{selectedTemplate?.channel}</span>
                  </div>
                  <div>
                    <span className='text-gray-600'>Priority:</span>
                    <span className='ml-2 font-medium capitalize'>{priority}</span>
                  </div>
                  <div>
                    <span className='text-gray-600'>Schedule:</span>
                    <span className='ml-2 font-medium'>
                      {scheduledAt ? new Date(scheduledAt).toLocaleString() : 'Immediate'}
                    </span>
                  </div>
                </div>
              </div>

              <div>
                <h4 className='font-medium text-gray-900 mb-3'>Message Preview</h4>
                <div className='flex space-x-2 mb-3'>
                  <select
                    onChange={(e) => {
                      const index = parseInt(e.target.value);
                      setPreviewRecipient(processedRecipients[index] || null);
                    }}
                    className='px-3 py-2 border border-gray-300 rounded-lg text-sm'
                  >
                    <option value=''>Select recipient to preview</option>
                    {processedRecipients.slice(0, 10).map((recipient, index) => (
                      <option key={index} value={index}>
                        {recipient.name ||
                          recipient.email ||
                          recipient.phone ||
                          `Recipient ${index + 1}`}
                      </option>
                    ))}
                  </select>
                </div>

                {previewRecipient && (
                  <div className='border border-gray-200 rounded-lg p-4 bg-white'>
                    {selectedTemplate?.subject && (
                      <div className='mb-3'>
                        <div className='text-sm font-medium text-gray-700'>Subject:</div>
                        <div className='text-gray-900'>{selectedTemplate.subject}</div>
                      </div>
                    )}
                    <div>
                      <div className='text-sm font-medium text-gray-700 mb-1'>Message:</div>
                      <div className='whitespace-pre-wrap text-gray-900'>
                        {generatePreview(previewRecipient)}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  const stepNames = {
    template: 'Template',
    recipients: 'Recipients',
    schedule: 'Schedule',
    review: 'Review',
  };

  return (
    <div className={`max-w-4xl mx-auto ${className}`}>
      {/* Progress Steps */}
      <div className='mb-8'>
        <div className='flex items-center justify-between'>
          {Object.entries(stepNames).map(([key, name], index) => {
            const isActive = key === currentStep;
            const isCompleted = Object.keys(stepNames).indexOf(currentStep) > index;

            return (
              <div key={key} className='flex items-center'>
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                    isCompleted
                      ? 'bg-green-600 text-white'
                      : isActive
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-200 text-gray-600'
                  }`}
                >
                  {isCompleted ? <CheckCircle className='w-5 h-5' /> : index + 1}
                </div>
                <span
                  className={`ml-2 text-sm font-medium ${
                    isActive ? 'text-blue-600' : 'text-gray-500'
                  }`}
                >
                  {name}
                </span>
                {index < Object.keys(stepNames).length - 1 && (
                  <div
                    className={`w-12 h-px mx-4 ${isCompleted ? 'bg-green-600' : 'bg-gray-200'}`}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Step Content */}
      <div className='bg-white rounded-lg border border-gray-200 p-6'>
        <AnimatePresence mode='wait'>
          <motion.div
            key={currentStep}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
          >
            {renderStepContent()}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Navigation */}
      <div className='flex items-center justify-between mt-6'>
        <button
          onClick={prevStep}
          disabled={currentStep === 'template'}
          className='px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors'
        >
          Previous
        </button>

        <div className='flex space-x-3'>
          {currentStep === 'review' ? (
            <button
              onClick={handleSubmit}
              disabled={isProcessing || !validateStep('review')}
              className='px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2'
            >
              {isProcessing ? (
                <>
                  <Clock className='w-4 h-4 animate-spin' />
                  <span>Creating Job...</span>
                </>
              ) : (
                <>
                  <Send className='w-4 h-4' />
                  <span>Send Messages</span>
                </>
              )}
            </button>
          ) : (
            <button
              onClick={nextStep}
              className='px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors'
            >
              Next
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
