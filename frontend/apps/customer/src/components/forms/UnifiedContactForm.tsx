/**
 * Unified Contact Form Example
 * Shows how to use the unified form validation system
 */

import React from 'react';
import { 
  useUniversalForm, 
  contactSchema, 
  FormField,
  FormButton,
  FormSelect,
  FormTextarea
} from '@dotmac/forms';
import { generateId } from '@dotmac/utils';
import { Mail, Phone, User, MessageSquare } from 'lucide-react';

interface UnifiedContactFormProps {
  onSubmit: (data: any) => Promise<void>;
  initialData?: any;
  isLoading?: boolean;
}

export function UnifiedContactForm({ 
  onSubmit, 
  initialData,
  isLoading = false 
}: UnifiedContactFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setValue,
    watch
  } = useUniversalForm({
    schema: contactSchema,
    defaultValues: {
      firstName: '',
      lastName: '',
      email: '',
      phone: '',
      company: '',
      subject: '',
      message: '',
      ...initialData
    }
  });

  const handleFormSubmit = async (data: any) => {
    try {
      // Add tracking ID
      const submissionData = {
        ...data,
        submissionId: generateId(),
        timestamp: new Date().toISOString(),
        portal: 'customer'
      };
      
      await onSubmit(submissionData);
    } catch (error) {
      console.error('Form submission error:', error);
      throw error;
    }
  };

  const subjectOptions = [
    { label: 'General Inquiry', value: 'general' },
    { label: 'Technical Support', value: 'technical' },
    { label: 'Billing Question', value: 'billing' },
    { label: 'Service Issue', value: 'service' },
    { label: 'Feature Request', value: 'feature' }
  ];

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
      {/* Header */}
      <div className="border-b border-gray-200 pb-4">
        <h2 className="text-2xl font-bold text-gray-900">
          Contact Support
        </h2>
        <p className="text-gray-600 mt-1">
          We'll get back to you within 24 hours
        </p>
      </div>

      {/* Personal Information */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <FormField
          label="First Name"
          error={errors.firstName?.message}
          required
        >
          <div className="relative">
            <User className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
            <input
              {...register('firstName')}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter your first name"
              disabled={isLoading || isSubmitting}
            />
          </div>
        </FormField>

        <FormField
          label="Last Name"
          error={errors.lastName?.message}
          required
        >
          <div className="relative">
            <User className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
            <input
              {...register('lastName')}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter your last name"
              disabled={isLoading || isSubmitting}
            />
          </div>
        </FormField>
      </div>

      {/* Contact Information */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <FormField
          label="Email Address"
          error={errors.email?.message}
          required
        >
          <div className="relative">
            <Mail className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
            <input
              {...register('email')}
              type="email"
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="your.email@example.com"
              disabled={isLoading || isSubmitting}
            />
          </div>
        </FormField>

        <FormField
          label="Phone Number"
          error={errors.phone?.message}
          required
        >
          <div className="relative">
            <Phone className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
            <input
              {...register('phone')}
              type="tel"
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="(555) 123-4567"
              disabled={isLoading || isSubmitting}
            />
          </div>
        </FormField>
      </div>

      {/* Company (Optional) */}
      <FormField
        label="Company (Optional)"
        error={errors.company?.message}
      >
        <input
          {...register('company')}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="Your company name"
          disabled={isLoading || isSubmitting}
        />
      </FormField>

      {/* Subject */}
      <FormField
        label="Subject"
        error={errors.subject?.message}
        required
      >
        <FormSelect
          {...register('subject')}
          options={subjectOptions}
          placeholder="Select a subject"
          disabled={isLoading || isSubmitting}
        />
      </FormField>

      {/* Message */}
      <FormField
        label="Message"
        error={errors.message?.message}
        required
      >
        <div className="relative">
          <MessageSquare className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
          <FormTextarea
            {...register('message')}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Please describe your question or issue in detail..."
            rows={6}
            disabled={isLoading || isSubmitting}
          />
        </div>
      </FormField>

      {/* Submit Button */}
      <div className="flex items-center justify-end space-x-4 pt-4 border-t border-gray-200">
        <button
          type="button"
          className="px-6 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          disabled={isLoading || isSubmitting}
        >
          Cancel
        </button>
        
        <FormButton
          type="submit"
          isLoading={isSubmitting || isLoading}
          loadingText="Sending..."
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Send Message
        </FormButton>
      </div>
    </form>
  );
}