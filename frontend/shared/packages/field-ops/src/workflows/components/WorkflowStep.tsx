import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CheckCircle2,
  Circle,
  AlertCircle,
  Clock,
  MapPin,
  Camera,
  PenTool,
  FileText,
  ChevronRight,
  Play,
  Pause,
  SkipForward,
} from 'lucide-react';
import type { WorkflowStep as WorkflowStepType, StepEvidence } from '../types';

interface WorkflowStepProps {
  step: WorkflowStepType;
  isActive: boolean;
  canStart: boolean;
  onStart: () => void;
  onComplete: (data: Record<string, any>, evidence: StepEvidence[]) => void;
  onSkip: () => void;
  onPause: () => void;
  className?: string;
}

export function WorkflowStep({
  step,
  isActive,
  canStart,
  onStart,
  onComplete,
  onSkip,
  onPause,
  className = '',
}: WorkflowStepProps) {
  const [isExpanded, setIsExpanded] = useState(isActive);
  const [formData, setFormData] = useState<Record<string, any>>(step.data || {});
  const [evidence, setEvidence] = useState<StepEvidence[]>(step.evidence || []);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const getStatusIcon = () => {
    switch (step.status) {
      case 'completed':
        return <CheckCircle2 className='w-5 h-5 text-green-600' />;
      case 'in_progress':
        return <Clock className='w-5 h-5 text-blue-600 animate-pulse' />;
      case 'failed':
        return <AlertCircle className='w-5 h-5 text-red-600' />;
      case 'skipped':
        return <SkipForward className='w-5 h-5 text-gray-400' />;
      default:
        return <Circle className='w-5 h-5 text-gray-300' />;
    }
  };

  const getStatusColor = () => {
    switch (step.status) {
      case 'completed':
        return 'border-green-200 bg-green-50';
      case 'in_progress':
        return 'border-blue-200 bg-blue-50';
      case 'failed':
        return 'border-red-200 bg-red-50';
      case 'skipped':
        return 'border-gray-200 bg-gray-50';
      default:
        return canStart ? 'border-primary-200 bg-primary-50' : 'border-gray-200 bg-gray-50';
    }
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    step.formFields?.forEach((field) => {
      const value = formData[field.id];

      // Check required fields
      if (field.required && (!value || value.toString().trim() === '')) {
        newErrors[field.id] = `${field.label} is required`;
        return;
      }

      // Check validation rules
      field.validation?.forEach((rule) => {
        if (!value && !field.required) return;

        switch (rule.type) {
          case 'min_length':
            if (value && value.toString().length < rule.value) {
              newErrors[field.id] = rule.message;
            }
            break;
          case 'max_length':
            if (value && value.toString().length > rule.value) {
              newErrors[field.id] = rule.message;
            }
            break;
          case 'pattern':
            if (value && !new RegExp(rule.value).test(value.toString())) {
              newErrors[field.id] = rule.message;
            }
            break;
          case 'custom':
            if (rule.validator && value && !rule.validator(value)) {
              newErrors[field.id] = rule.message;
            }
            break;
        }
      });
    });

    // Check evidence requirements
    if (step.evidenceRequired?.photos && step.evidenceRequired.photos.minimum > 0) {
      const photoEvidence = evidence.filter((e) => e.type === 'photo');
      if (photoEvidence.length < step.evidenceRequired.photos.minimum) {
        newErrors.photos = `At least ${step.evidenceRequired.photos.minimum} photo(s) required`;
      }
    }

    if (step.evidenceRequired?.signature) {
      const signatureEvidence = evidence.find((e) => e.type === 'signature');
      if (!signatureEvidence) {
        newErrors.signature = 'Signature is required';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleStart = () => {
    if (!canStart) return;
    setIsExpanded(true);
    onStart();
  };

  const handleComplete = () => {
    if (!validateForm()) return;

    onComplete(formData, evidence);
    setIsExpanded(false);
  };

  const handleSkip = () => {
    onSkip();
    setIsExpanded(false);
  };

  const handlePause = () => {
    onPause();
    setIsExpanded(false);
  };

  const handleFieldChange = (fieldId: string, value: any) => {
    setFormData((prev) => ({
      ...prev,
      [fieldId]: value,
    }));

    // Clear error when field is updated
    if (errors[fieldId]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[fieldId];
        return newErrors;
      });
    }
  };

  const addEvidence = (newEvidence: StepEvidence) => {
    setEvidence((prev) => [...prev, newEvidence]);
  };

  const removeEvidence = (evidenceId: string) => {
    setEvidence((prev) => prev.filter((e) => e.id !== evidenceId));
  };

  const renderFormField = (field: any) => {
    const value = formData[field.id] || field.defaultValue || '';
    const error = errors[field.id];

    const baseInputClass = `w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 ${
      error ? 'border-red-300' : 'border-gray-300'
    }`;

    switch (field.type) {
      case 'text':
        return (
          <div key={field.id} className='space-y-1'>
            <label className='block text-sm font-medium text-gray-700'>
              {field.label} {field.required && <span className='text-red-500'>*</span>}
            </label>
            <input
              type='text'
              value={value}
              onChange={(e) => handleFieldChange(field.id, e.target.value)}
              placeholder={field.placeholder}
              className={baseInputClass}
            />
            {error && <p className='text-sm text-red-600'>{error}</p>}
          </div>
        );

      case 'textarea':
        return (
          <div key={field.id} className='space-y-1'>
            <label className='block text-sm font-medium text-gray-700'>
              {field.label} {field.required && <span className='text-red-500'>*</span>}
            </label>
            <textarea
              value={value}
              onChange={(e) => handleFieldChange(field.id, e.target.value)}
              placeholder={field.placeholder}
              rows={3}
              className={baseInputClass}
            />
            {error && <p className='text-sm text-red-600'>{error}</p>}
          </div>
        );

      case 'select':
        return (
          <div key={field.id} className='space-y-1'>
            <label className='block text-sm font-medium text-gray-700'>
              {field.label} {field.required && <span className='text-red-500'>*</span>}
            </label>
            <select
              value={value}
              onChange={(e) => handleFieldChange(field.id, e.target.value)}
              className={baseInputClass}
            >
              <option value=''>Select {field.label}</option>
              {field.options?.map((option: any) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            {error && <p className='text-sm text-red-600'>{error}</p>}
          </div>
        );

      case 'checkbox':
        return (
          <div key={field.id} className='space-y-1'>
            <label className='flex items-center space-x-2'>
              <input
                type='checkbox'
                checked={value}
                onChange={(e) => handleFieldChange(field.id, e.target.checked)}
                className='rounded border-gray-300 text-primary-600 focus:ring-primary-500'
              />
              <span className='text-sm font-medium text-gray-700'>
                {field.label} {field.required && <span className='text-red-500'>*</span>}
              </span>
            </label>
            {error && <p className='text-sm text-red-600'>{error}</p>}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <motion.div layout className={`border rounded-lg ${getStatusColor()} ${className}`}>
      {/* Step Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className='w-full p-4 flex items-center justify-between text-left hover:bg-black hover:bg-opacity-5 transition-colors'
      >
        <div className='flex items-center space-x-3'>
          {getStatusIcon()}
          <div>
            <h3 className='font-medium text-gray-900'>{step.title}</h3>
            <p className='text-sm text-gray-600'>{step.description}</p>
          </div>
        </div>

        <div className='flex items-center space-x-2'>
          {step.estimatedDuration && (
            <div className='flex items-center text-xs text-gray-500'>
              <Clock className='w-3 h-3 mr-1' />
              {step.estimatedDuration}m
            </div>
          )}
          {step.locationRequired && <MapPin className='w-4 h-4 text-gray-400' />}
          <ChevronRight
            className={`w-4 h-4 text-gray-400 transform transition-transform ${
              isExpanded ? 'rotate-90' : ''
            }`}
          />
        </div>
      </button>

      {/* Step Content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
            className='px-4 pb-4'
          >
            {/* Form Fields */}
            {step.formFields && step.formFields.length > 0 && (
              <div className='space-y-4 mb-4'>
                <h4 className='font-medium text-gray-900'>Information Required</h4>
                {step.formFields.map(renderFormField)}
              </div>
            )}

            {/* Evidence Requirements */}
            {(step.evidenceRequired?.photos || step.evidenceRequired?.signature) && (
              <div className='space-y-3 mb-4'>
                <h4 className='font-medium text-gray-900'>Evidence Required</h4>

                {step.evidenceRequired.photos && (
                  <div className='flex items-center space-x-2 text-sm text-gray-600'>
                    <Camera className='w-4 h-4' />
                    <span>
                      {step.evidenceRequired.photos.minimum} photo(s) required
                      {step.evidenceRequired.photos.categories.length > 0 &&
                        ` (${step.evidenceRequired.photos.categories.join(', ')})`}
                    </span>
                  </div>
                )}

                {step.evidenceRequired.signature && (
                  <div className='flex items-center space-x-2 text-sm text-gray-600'>
                    <PenTool className='w-4 h-4' />
                    <span>Customer signature required</span>
                  </div>
                )}

                {step.evidenceRequired.notes && (
                  <div className='flex items-center space-x-2 text-sm text-gray-600'>
                    <FileText className='w-4 h-4' />
                    <span>Detailed notes required</span>
                  </div>
                )}

                {errors.photos && <p className='text-sm text-red-600'>{errors.photos}</p>}
                {errors.signature && <p className='text-sm text-red-600'>{errors.signature}</p>}
              </div>
            )}

            {/* Current Evidence */}
            {evidence.length > 0 && (
              <div className='space-y-2 mb-4'>
                <h4 className='font-medium text-gray-900'>Collected Evidence</h4>
                <div className='grid grid-cols-2 gap-2'>
                  {evidence.map((item) => (
                    <div
                      key={item.id}
                      className='p-2 bg-white rounded border flex items-center space-x-2'
                    >
                      {item.type === 'photo' && <Camera className='w-4 h-4 text-gray-400' />}
                      {item.type === 'signature' && <PenTool className='w-4 h-4 text-gray-400' />}
                      {item.type === 'note' && <FileText className='w-4 h-4 text-gray-400' />}
                      <span className='text-sm text-gray-600 truncate'>
                        {item.metadata.description || `${item.type} evidence`}
                      </span>
                      <button
                        onClick={() => removeEvidence(item.id)}
                        className='text-red-500 hover:text-red-700'
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className='flex flex-wrap gap-2'>
              {step.status === 'pending' && canStart && (
                <button
                  onClick={handleStart}
                  className='flex items-center space-x-1 px-3 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors'
                >
                  <Play className='w-4 h-4' />
                  <span>Start Step</span>
                </button>
              )}

              {step.status === 'in_progress' && (
                <>
                  <button
                    onClick={handleComplete}
                    className='flex items-center space-x-1 px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors'
                  >
                    <CheckCircle2 className='w-4 h-4' />
                    <span>Complete</span>
                  </button>

                  <button
                    onClick={handlePause}
                    className='flex items-center space-x-1 px-3 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors'
                  >
                    <Pause className='w-4 h-4' />
                    <span>Pause</span>
                  </button>

                  {!step.required && (
                    <button
                      onClick={handleSkip}
                      className='flex items-center space-x-1 px-3 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors'
                    >
                      <SkipForward className='w-4 h-4' />
                      <span>Skip</span>
                    </button>
                  )}
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
