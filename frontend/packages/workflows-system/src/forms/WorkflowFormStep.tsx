'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import type { WorkflowStep, FormStepConfig } from '../types';

interface WorkflowFormStepProps {
  step: WorkflowStep & { type: 'form' };
  onDataChange: (data: unknown) => void;
  onComplete: (data: unknown) => void;
  onError: (error: string) => void;
  className?: string;
  disabled?: boolean;
}

export function WorkflowFormStep({
  step,
  onDataChange,
  onComplete,
  onError,
  className,
  disabled = false
}: WorkflowFormStepProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [customFields, setCustomFields] = useState<Record<string, unknown>>({});

  // Parse form configuration from step input
  const formConfig = React.useMemo((): FormStepConfig => {
    if (step.input && typeof step.input === 'object' && 'schema' in step.input) {
      return step.input as FormStepConfig;
    }

    // Default configuration
    return {
      schema: {
        type: 'object',
        properties: {
          notes: {
            type: 'string',
            title: 'Notes',
            description: 'Additional notes or comments'
          }
        },
        required: []
      },
      layout: 'single-column'
    };
  }, [step.input]);

  // Create Zod schema from JSON schema
  const zodSchema = React.useMemo(() => {
    return createZodSchemaFromJsonSchema(formConfig.schema);
  }, [formConfig.schema]);

  // Initialize form
  const form = useForm({
    resolver: zodResolver(zodSchema),
    defaultValues: step.output || {},
    mode: 'onChange'
  });

  const { register, handleSubmit, watch, formState: { errors, isValid, isDirty } } = form;

  // Watch form changes and notify parent
  const watchedValues = watch();

  useEffect(() => {
    if (isDirty) {
      onDataChange({ ...watchedValues, ...customFields });
    }
  }, [watchedValues, customFields, isDirty, onDataChange]);

  // Handle form submission
  const onSubmit = async (data: unknown) => {
    if (disabled || isSubmitting) return;

    setIsSubmitting(true);
    try {
      const finalData = { ...data, ...customFields };
      await onComplete(finalData);
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Form submission failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Render field based on JSON schema property
  const renderField = (key: string, property: any, isRequired: boolean) => {
    const error = errors[key as keyof typeof errors];

    switch (property.type) {
      case 'string':
        if (property.enum) {
          return (
            <select
              {...register(key)}
              className={clsx('form-select', { 'error': error })}
              disabled={disabled}
            >
              <option value="">Select {property.title || key}...</option>
              {property.enum.map((option: string) => (
                <option key={option} value={option}>
                  {property.enumNames?.[property.enum.indexOf(option)] || option}
                </option>
              ))}
            </select>
          );
        }

        if (property.format === 'textarea' || (property.maxLength && property.maxLength > 100)) {
          return (
            <textarea
              {...register(key)}
              rows={property.rows || 3}
              placeholder={property.placeholder}
              className={clsx('form-textarea', { 'error': error })}
              disabled={disabled}
            />
          );
        }

        return (
          <input
            {...register(key)}
            type={getInputType(property)}
            placeholder={property.placeholder}
            className={clsx('form-input', { 'error': error })}
            disabled={disabled}
          />
        );

      case 'number':
      case 'integer':
        return (
          <input
            {...register(key, { valueAsNumber: true })}
            type="number"
            min={property.minimum}
            max={property.maximum}
            step={property.type === 'integer' ? 1 : 'any'}
            placeholder={property.placeholder}
            className={clsx('form-input', { 'error': error })}
            disabled={disabled}
          />
        );

      case 'boolean':
        return (
          <div className="form-checkbox-wrapper">
            <input
              {...register(key)}
              type="checkbox"
              className={clsx('form-checkbox', { 'error': error })}
              disabled={disabled}
            />
            <span className="checkbox-label">
              {property.title || key}
            </span>
          </div>
        );

      case 'array':
        if (property.items?.enum) {
          return (
            <div className="form-checkbox-group">
              {property.items.enum.map((option: string, index: number) => (
                <label key={option} className="checkbox-item">
                  <input
                    {...register(key)}
                    type="checkbox"
                    value={option}
                    className="form-checkbox"
                    disabled={disabled}
                  />
                  <span>{property.items.enumNames?.[index] || option}</span>
                </label>
              ))}
            </div>
          );
        }
        break;

      default:
        return (
          <input
            {...register(key)}
            type="text"
            placeholder={property.placeholder}
            className={clsx('form-input', { 'error': error })}
            disabled={disabled}
          />
        );
    }
  };

  // Get appropriate input type based on property format
  const getInputType = (property: any): string => {
    switch (property.format) {
      case 'email': return 'email';
      case 'uri': return 'url';
      case 'date': return 'date';
      case 'time': return 'time';
      case 'datetime-local': return 'datetime-local';
      case 'password': return 'password';
      case 'tel': return 'tel';
      default: return 'text';
    }
  };

  // Render form sections if configured
  const renderSections = () => {
    if (!formConfig.sections) {
      // Render all fields in a single section
      return (
        <div className="form-section">
          {Object.entries(formConfig.schema.properties || {}).map(([key, property]) => {
            const isRequired = Array.isArray(formConfig.schema.required) &&
              formConfig.schema.required.includes(key);

            return renderFieldWrapper(key, property as any, isRequired);
          })}
        </div>
      );
    }

    return formConfig.sections.map((section) => (
      <div key={section.title} className="form-section">
        <div className="section-header">
          <h4 className="section-title">{section.title}</h4>
          {section.description && (
            <p className="section-description">{section.description}</p>
          )}
        </div>

        <div className={clsx('section-fields', {
          'collapsible': section.collapsible
        })}>
          {section.fields.map((fieldKey) => {
            const property = formConfig.schema.properties?.[fieldKey];
            if (!property) return null;

            const isRequired = Array.isArray(formConfig.schema.required) &&
              formConfig.schema.required.includes(fieldKey);

            return renderFieldWrapper(fieldKey, property as any, isRequired);
          })}
        </div>
      </div>
    ));
  };

  const renderFieldWrapper = (key: string, property: any, isRequired: boolean) => {
    const error = errors[key as keyof typeof errors];

    return (
      <motion.div
        key={key}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="form-field"
      >
        <label className="field-label">
          {property.title || key}
          {isRequired && <span className="required-indicator">*</span>}
        </label>

        {property.description && (
          <p className="field-description">{property.description}</p>
        )}

        {renderField(key, property, isRequired)}

        <AnimatePresence>
          {error && (
            <motion.p
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="field-error"
            >
              {error.message}
            </motion.p>
          )}
        </AnimatePresence>
      </motion.div>
    );
  };

  return (
    <div className={clsx('workflow-form-step', className)}>
      <div className="form-header">
        <h3 className="form-title">{step.name}</h3>
        {step.description && (
          <p className="form-description">{step.description}</p>
        )}
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className={clsx('workflow-form', formConfig.layout)}>
        {renderSections()}

        {/* Custom Fields Section */}
        <div className="form-actions">
          <div className="action-buttons">
            <motion.button
              type="submit"
              disabled={disabled || isSubmitting || !isValid}
              className={clsx('submit-button', {
                'loading': isSubmitting,
                'disabled': disabled || !isValid
              })}
              whileHover={{ scale: disabled ? 1 : 1.02 }}
              whileTap={{ scale: disabled ? 1 : 0.98 }}
            >
              {isSubmitting ? (
                <>
                  <span className="loading-spinner" />
                  Submitting...
                </>
              ) : (
                'Complete Step'
              )}
            </motion.button>

            {step.canSkip && (
              <button
                type="button"
                onClick={() => onComplete({ skipped: true })}
                disabled={disabled || isSubmitting}
                className="skip-button"
              >
                Skip
              </button>
            )}
          </div>

          <div className="form-status">
            {isDirty && !isSubmitting && (
              <span className="status-message">Unsaved changes</span>
            )}
            {!isValid && Object.keys(errors).length > 0 && (
              <span className="error-message">
                Please fix {Object.keys(errors).length} error(s) above
              </span>
            )}
          </div>
        </div>
      </form>
    </div>
  );
}

// Helper function to create Zod schema from JSON schema (simplified)
function createZodSchemaFromJsonSchema(jsonSchema: any): z.ZodSchema {
  const fields: Record<string, z.ZodTypeAny> = {};

  if (jsonSchema.properties) {
    Object.entries(jsonSchema.properties).forEach(([key, property]: [string, any]) => {
      let field: z.ZodTypeAny;

      switch (property.type) {
        case 'string':
          field = z.string();
          if (property.minLength) field = (field as z.ZodString).min(property.minLength);
          if (property.maxLength) field = (field as z.ZodString).max(property.maxLength);
          if (property.pattern) field = (field as z.ZodString).regex(new RegExp(property.pattern));
          if (property.format === 'email') field = (field as z.ZodString).email();
          if (property.format === 'uri') field = (field as z.ZodString).url();
          break;

        case 'number':
          field = z.number();
          if (property.minimum) field = (field as z.ZodNumber).min(property.minimum);
          if (property.maximum) field = (field as z.ZodNumber).max(property.maximum);
          break;

        case 'integer':
          field = z.number().int();
          if (property.minimum) field = (field as z.ZodNumber).min(property.minimum);
          if (property.maximum) field = (field as z.ZodNumber).max(property.maximum);
          break;

        case 'boolean':
          field = z.boolean();
          break;

        case 'array':
          field = z.array(z.string()); // Simplified - would need more complex logic for nested types
          if (property.minItems) field = (field as z.ZodArray<any>).min(property.minItems);
          if (property.maxItems) field = (field as z.ZodArray<any>).max(property.maxItems);
          break;

        default:
          field = z.string();
      }

      // Handle optional fields
      if (!jsonSchema.required?.includes(key)) {
        field = field.optional();
      }

      fields[key] = field;
    });
  }

  return z.object(fields);
}

export default WorkflowFormStep;
