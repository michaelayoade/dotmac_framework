'use client';

import React, { useState, useCallback, useEffect } from 'react';
import {
  Save,
  X,
  Eye,
  Code,
  Type,
  Plus,
  Minus,
  AlertCircle,
  CheckCircle,
  Mail,
  MessageSquare,
  Smartphone,
  Bell,
  Send,
  Tag,
  Clock,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { CommunicationTemplate } from '../../types';

interface TemplateEditorProps {
  template?: CommunicationTemplate;
  isOpen: boolean;
  onClose: () => void;
  onSave: (template: Omit<CommunicationTemplate, 'id' | 'createdAt' | 'updatedAt'>) => void;
  mode?: 'create' | 'edit';
  defaultChannel?: string;
  defaultCategory?: string;
}

const channelOptions = [
  { value: 'email', label: 'Email', icon: Mail, requiresSubject: true },
  { value: 'sms', label: 'SMS', icon: Smartphone, requiresSubject: false },
  { value: 'chat', label: 'Chat', icon: MessageSquare, requiresSubject: false },
  { value: 'push', label: 'Push Notification', icon: Bell, requiresSubject: true },
  { value: 'websocket', label: 'WebSocket', icon: MessageSquare, requiresSubject: false },
  { value: 'webhook', label: 'Webhook', icon: Send, requiresSubject: false },
  { value: 'whatsapp', label: 'WhatsApp', icon: MessageSquare, requiresSubject: false },
];

const priorityOptions = [
  { value: 'low', label: 'Low', color: 'text-gray-500' },
  { value: 'medium', label: 'Medium', color: 'text-yellow-500' },
  { value: 'high', label: 'High', color: 'text-orange-500' },
  { value: 'critical', label: 'Critical', color: 'text-red-500' },
];

const categoryOptions = [
  'Marketing',
  'Transactional',
  'Notification',
  'Alert',
  'Welcome',
  'Support',
  'Billing',
  'Security',
  'System',
  'Other',
];

export function TemplateEditor({
  template,
  isOpen,
  onClose,
  onSave,
  mode = 'create',
  defaultChannel = 'email',
  defaultCategory = 'Notification',
}: TemplateEditorProps) {
  const [formData, setFormData] = useState({
    name: '',
    channel: defaultChannel,
    subject: '',
    body: '',
    variables: [] as string[],
    priority: 'medium' as const,
    category: defaultCategory,
    tags: [] as string[],
    isActive: true,
    version: 1,
  });

  const [newVariable, setNewVariable] = useState('');
  const [newTag, setNewTag] = useState('');
  const [viewMode, setViewMode] = useState<'edit' | 'preview'>('edit');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isValidating, setIsValidating] = useState(false);

  const selectedChannel = channelOptions.find((ch) => ch.value === formData.channel);

  useEffect(() => {
    if (template) {
      setFormData({
        name: template.name,
        channel: template.channel,
        subject: template.subject || '',
        body: template.body,
        variables: [...template.variables],
        priority: template.priority,
        category: template.category,
        tags: template.tags || [],
        isActive: template.isActive,
        version: template.version,
      });
    } else {
      setFormData({
        name: '',
        channel: defaultChannel,
        subject: '',
        body: '',
        variables: [],
        priority: 'medium',
        category: defaultCategory,
        tags: [],
        isActive: true,
        version: 1,
      });
    }
  }, [template, defaultChannel, defaultCategory]);

  const validateForm = useCallback(() => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Template name is required';
    }

    if (!formData.body.trim()) {
      newErrors.body = 'Template body is required';
    }

    if (selectedChannel?.requiresSubject && !formData.subject.trim()) {
      newErrors.subject = 'Subject is required for this channel';
    }

    // Check for unused variables
    const bodyVariables = formData.body.match(/\{\{([^}]+)\}\}/g) || [];
    const usedVariables = bodyVariables.map((v) => v.replace(/[{}]/g, ''));
    const unusedVariables = formData.variables.filter((v) => !usedVariables.includes(v));

    if (unusedVariables.length > 0) {
      newErrors.variables = `Unused variables: ${unusedVariables.join(', ')}`;
    }

    // Check for undefined variables in body
    const undefinedVariables = usedVariables.filter((v) => !formData.variables.includes(v));
    if (undefinedVariables.length > 0) {
      newErrors.body = `Undefined variables in body: ${undefinedVariables.join(', ')}`;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formData, selectedChannel]);

  const handleSave = useCallback(async () => {
    setIsValidating(true);

    if (!validateForm()) {
      setIsValidating(false);
      return;
    }

    try {
      await onSave(formData);
      onClose();
    } catch (error) {
      console.error('Failed to save template:', error);
    } finally {
      setIsValidating(false);
    }
  }, [formData, validateForm, onSave, onClose]);

  const addVariable = useCallback(() => {
    if (newVariable.trim() && !formData.variables.includes(newVariable.trim())) {
      setFormData((prev) => ({
        ...prev,
        variables: [...prev.variables, newVariable.trim()],
      }));
      setNewVariable('');
    }
  }, [newVariable, formData.variables]);

  const removeVariable = useCallback((index: number) => {
    setFormData((prev) => ({
      ...prev,
      variables: prev.variables.filter((_, i) => i !== index),
    }));
  }, []);

  const addTag = useCallback(() => {
    if (newTag.trim() && !formData.tags.includes(newTag.trim())) {
      setFormData((prev) => ({
        ...prev,
        tags: [...prev.tags, newTag.trim()],
      }));
      setNewTag('');
    }
  }, [newTag, formData.tags]);

  const removeTag = useCallback((index: number) => {
    setFormData((prev) => ({
      ...prev,
      tags: prev.tags.filter((_, i) => i !== index),
    }));
  }, []);

  const insertVariable = useCallback(
    (variable: string) => {
      const textarea = document.getElementById('template-body') as HTMLTextAreaElement;
      if (textarea) {
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const newText =
          formData.body.substring(0, start) + `{{${variable}}}` + formData.body.substring(end);

        setFormData((prev) => ({ ...prev, body: newText }));

        // Reset cursor position
        setTimeout(() => {
          textarea.focus();
          textarea.setSelectionRange(start + variable.length + 4, start + variable.length + 4);
        }, 0);
      }
    },
    [formData.body]
  );

  const renderPreview = useCallback(() => {
    let preview = formData.body;

    // Replace variables with sample data
    formData.variables.forEach((variable) => {
      const sampleData: Record<string, string> = {
        name: 'John Doe',
        email: 'john@example.com',
        company: 'Acme Corp',
        amount: '$99.99',
        date: new Date().toLocaleDateString(),
        time: new Date().toLocaleTimeString(),
      };

      const replacement = sampleData[variable] || `[${variable}]`;
      preview = preview.replace(new RegExp(`\\{\\{${variable}\\}\\}`, 'g'), replacement);
    });

    return preview;
  }, [formData.body, formData.variables]);

  if (!isOpen) return null;

  return (
    <div className='fixed inset-0 z-50 overflow-hidden'>
      <div className='absolute inset-0 bg-black bg-opacity-50' onClick={onClose} />

      <motion.div
        initial={{ opacity: 0, x: '100%' }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: '100%' }}
        className='absolute right-0 top-0 h-full w-full max-w-4xl bg-white shadow-xl'
      >
        <div className='flex flex-col h-full'>
          {/* Header */}
          <div className='flex items-center justify-between p-6 border-b border-gray-200'>
            <div>
              <h2 className='text-xl font-semibold text-gray-900'>
                {mode === 'create' ? 'Create Template' : 'Edit Template'}
              </h2>
              <p className='text-sm text-gray-500 mt-1'>Design your communication template</p>
            </div>

            <div className='flex items-center space-x-2'>
              <div className='flex bg-gray-100 rounded-lg p-1'>
                <button
                  onClick={() => setViewMode('edit')}
                  className={`px-3 py-1 text-sm rounded-md transition-colors ${
                    viewMode === 'edit'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <Code className='w-4 h-4 inline mr-1' />
                  Edit
                </button>
                <button
                  onClick={() => setViewMode('preview')}
                  className={`px-3 py-1 text-sm rounded-md transition-colors ${
                    viewMode === 'preview'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <Eye className='w-4 h-4 inline mr-1' />
                  Preview
                </button>
              </div>

              <button
                onClick={onClose}
                className='p-2 hover:bg-gray-100 rounded-lg transition-colors'
              >
                <X className='w-5 h-5' />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className='flex-1 overflow-hidden'>
            <AnimatePresence mode='wait'>
              {viewMode === 'edit' ? (
                <motion.div
                  key='edit'
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className='h-full overflow-y-auto p-6'
                >
                  <div className='max-w-2xl space-y-6'>
                    {/* Basic Information */}
                    <div className='space-y-4'>
                      <h3 className='text-lg font-medium text-gray-900'>Basic Information</h3>

                      <div>
                        <label className='block text-sm font-medium text-gray-700 mb-1'>
                          Template Name *
                        </label>
                        <input
                          type='text'
                          value={formData.name}
                          onChange={(e) =>
                            setFormData((prev) => ({ ...prev, name: e.target.value }))
                          }
                          className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                            errors.name ? 'border-red-300' : 'border-gray-300'
                          }`}
                          placeholder='Enter template name'
                        />
                        {errors.name && (
                          <p className='mt-1 text-sm text-red-600 flex items-center'>
                            <AlertCircle className='w-4 h-4 mr-1' />
                            {errors.name}
                          </p>
                        )}
                      </div>

                      <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
                        <div>
                          <label className='block text-sm font-medium text-gray-700 mb-1'>
                            Channel *
                          </label>
                          <select
                            value={formData.channel}
                            onChange={(e) =>
                              setFormData((prev) => ({ ...prev, channel: e.target.value }))
                            }
                            className='w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
                          >
                            {channelOptions.map((option) => {
                              const Icon = option.icon;
                              return (
                                <option key={option.value} value={option.value}>
                                  {option.label}
                                </option>
                              );
                            })}
                          </select>
                        </div>

                        <div>
                          <label className='block text-sm font-medium text-gray-700 mb-1'>
                            Priority
                          </label>
                          <select
                            value={formData.priority}
                            onChange={(e) =>
                              setFormData((prev) => ({ ...prev, priority: e.target.value as any }))
                            }
                            className='w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
                          >
                            {priorityOptions.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>

                      <div>
                        <label className='block text-sm font-medium text-gray-700 mb-1'>
                          Category
                        </label>
                        <select
                          value={formData.category}
                          onChange={(e) =>
                            setFormData((prev) => ({ ...prev, category: e.target.value }))
                          }
                          className='w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
                        >
                          {categoryOptions.map((category) => (
                            <option key={category} value={category}>
                              {category}
                            </option>
                          ))}
                        </select>
                      </div>

                      {selectedChannel?.requiresSubject && (
                        <div>
                          <label className='block text-sm font-medium text-gray-700 mb-1'>
                            Subject *
                          </label>
                          <input
                            type='text'
                            value={formData.subject}
                            onChange={(e) =>
                              setFormData((prev) => ({ ...prev, subject: e.target.value }))
                            }
                            className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                              errors.subject ? 'border-red-300' : 'border-gray-300'
                            }`}
                            placeholder='Enter subject line'
                          />
                          {errors.subject && (
                            <p className='mt-1 text-sm text-red-600 flex items-center'>
                              <AlertCircle className='w-4 h-4 mr-1' />
                              {errors.subject}
                            </p>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Variables */}
                    <div className='space-y-4'>
                      <h3 className='text-lg font-medium text-gray-900'>Variables</h3>

                      <div className='flex space-x-2'>
                        <input
                          type='text'
                          value={newVariable}
                          onChange={(e) => setNewVariable(e.target.value)}
                          onKeyPress={(e) => e.key === 'Enter' && addVariable()}
                          className='flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
                          placeholder='Add variable name (e.g., name, email)'
                        />
                        <button
                          onClick={addVariable}
                          className='px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors'
                        >
                          <Plus className='w-4 h-4' />
                        </button>
                      </div>

                      <div className='flex flex-wrap gap-2'>
                        {formData.variables.map((variable, index) => (
                          <div
                            key={index}
                            className='flex items-center space-x-2 bg-blue-50 text-blue-700 px-3 py-1 rounded-full group'
                          >
                            <span
                              onClick={() => insertVariable(variable)}
                              className='cursor-pointer hover:underline'
                              title='Click to insert into template'
                            >
                              {variable}
                            </span>
                            <button
                              onClick={() => removeVariable(index)}
                              className='opacity-0 group-hover:opacity-100 transition-opacity'
                            >
                              <Minus className='w-3 h-3' />
                            </button>
                          </div>
                        ))}
                      </div>

                      {errors.variables && (
                        <p className='text-sm text-yellow-600 flex items-center'>
                          <AlertCircle className='w-4 h-4 mr-1' />
                          {errors.variables}
                        </p>
                      )}
                    </div>

                    {/* Template Body */}
                    <div className='space-y-4'>
                      <h3 className='text-lg font-medium text-gray-900'>Template Body</h3>

                      <div>
                        <textarea
                          id='template-body'
                          value={formData.body}
                          onChange={(e) =>
                            setFormData((prev) => ({ ...prev, body: e.target.value }))
                          }
                          className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm ${
                            errors.body ? 'border-red-300' : 'border-gray-300'
                          }`}
                          rows={12}
                          placeholder='Enter your template content here. Use {{variable}} to insert dynamic content.'
                        />
                        {errors.body && (
                          <p className='mt-1 text-sm text-red-600 flex items-center'>
                            <AlertCircle className='w-4 h-4 mr-1' />
                            {errors.body}
                          </p>
                        )}
                        <p className='mt-1 text-xs text-gray-500'>
                          Use double curly braces to insert variables: {'{{'} variable {'}}'}
                        </p>
                      </div>
                    </div>

                    {/* Tags */}
                    <div className='space-y-4'>
                      <h3 className='text-lg font-medium text-gray-900'>Tags</h3>

                      <div className='flex space-x-2'>
                        <input
                          type='text'
                          value={newTag}
                          onChange={(e) => setNewTag(e.target.value)}
                          onKeyPress={(e) => e.key === 'Enter' && addTag()}
                          className='flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
                          placeholder='Add tag'
                        />
                        <button
                          onClick={addTag}
                          className='px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors'
                        >
                          <Tag className='w-4 h-4' />
                        </button>
                      </div>

                      <div className='flex flex-wrap gap-2'>
                        {formData.tags.map((tag, index) => (
                          <div
                            key={index}
                            className='flex items-center space-x-2 bg-gray-100 text-gray-700 px-3 py-1 rounded-full group'
                          >
                            <span>{tag}</span>
                            <button
                              onClick={() => removeTag(index)}
                              className='opacity-0 group-hover:opacity-100 transition-opacity'
                            >
                              <X className='w-3 h-3' />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Status */}
                    <div className='space-y-4'>
                      <h3 className='text-lg font-medium text-gray-900'>Status</h3>

                      <div className='flex items-center space-x-2'>
                        <input
                          type='checkbox'
                          id='isActive'
                          checked={formData.isActive}
                          onChange={(e) =>
                            setFormData((prev) => ({ ...prev, isActive: e.target.checked }))
                          }
                          className='h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
                        />
                        <label htmlFor='isActive' className='text-sm text-gray-700'>
                          Active template (can be used for sending messages)
                        </label>
                      </div>
                    </div>
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  key='preview'
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  className='h-full overflow-y-auto p-6'
                >
                  <div className='max-w-2xl space-y-6'>
                    <div className='bg-gray-50 rounded-lg p-4'>
                      <h3 className='text-lg font-medium text-gray-900 mb-4'>Template Preview</h3>

                      <div className='bg-white rounded-lg border p-4 space-y-3'>
                        <div className='flex items-center justify-between text-sm text-gray-500'>
                          <div className='flex items-center space-x-2'>
                            {selectedChannel && <selectedChannel.icon className='w-4 h-4' />}
                            <span>{selectedChannel?.label}</span>
                          </div>
                          <div className='flex items-center space-x-2'>
                            <Clock className='w-4 h-4' />
                            <span>{new Date().toLocaleString()}</span>
                          </div>
                        </div>

                        {formData.subject && (
                          <div>
                            <div className='text-sm font-medium text-gray-700 mb-1'>Subject:</div>
                            <div className='font-semibold'>{formData.subject}</div>
                          </div>
                        )}

                        <div>
                          <div className='text-sm font-medium text-gray-700 mb-1'>Message:</div>
                          <div className='whitespace-pre-wrap bg-gray-50 p-3 rounded'>
                            {renderPreview()}
                          </div>
                        </div>
                      </div>

                      <div className='mt-4 text-sm text-gray-500'>
                        <p>This preview shows how your template will look with sample data.</p>
                        <p>Variables are replaced with example values for demonstration.</p>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Footer */}
          <div className='flex items-center justify-between p-6 border-t border-gray-200 bg-gray-50'>
            <div className='flex items-center text-sm text-gray-500'>
              {Object.keys(errors).length > 0 ? (
                <div className='flex items-center text-red-600'>
                  <AlertCircle className='w-4 h-4 mr-1' />
                  Please fix the errors above
                </div>
              ) : (
                <div className='flex items-center text-green-600'>
                  <CheckCircle className='w-4 h-4 mr-1' />
                  Template is ready to save
                </div>
              )}
            </div>

            <div className='flex items-center space-x-3'>
              <button
                onClick={onClose}
                className='px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors'
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={isValidating}
                className='px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2'
              >
                <Save className='w-4 h-4' />
                <span>{isValidating ? 'Saving...' : 'Save Template'}</span>
              </button>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
