/**
 * Universal Login Form Component
 *
 * Handles all portal authentication flows with portal-aware UI and validation
 * Supports multiple login methods: email, portal ID, account number, partner code
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Eye,
  EyeOff,
  AlertCircle,
  Loader2,
  Shield,
  Mail,
  User,
  CreditCard,
  Key,
  Smartphone,
  CheckCircle,
  Lock,
} from 'lucide-react';

import type {
  LoginCredentials,
  LoginError,
  PortalVariant,
  User as AuthUser,
  PortalConfig,
} from '../../types';
import { LOGIN_SCHEMAS, validatePortalId, validateAccountNumber } from '../../validation/schemas';
import { getPortalConfig, getPortalTheme } from '../../config/portal-configs';
import { useAuth } from '../../hooks/useAuth';

// Component Props
export interface UniversalLoginFormProps {
  portalVariant: PortalVariant;
  onLogin: (user: AuthUser) => void;
  onError?: (error: LoginError) => void;
  className?: string;
  showRememberMe?: boolean;
  showForgotPassword?: boolean;
  redirectTo?: string;
  customBranding?: {
    logo?: string;
    title?: string;
    subtitle?: string;
  };
}

// Form field configurations for different portals
const FIELD_CONFIGS = {
  email: {
    icon: Mail,
    label: 'Email Address',
    placeholder: 'Enter your email',
    type: 'email',
    autoComplete: 'email',
  },
  portalId: {
    icon: User,
    label: 'Portal ID',
    placeholder: 'Enter 8-character Portal ID',
    type: 'text',
    autoComplete: 'username',
    maxLength: 8,
    transform: (value: string) => value.toUpperCase(),
  },
  accountNumber: {
    icon: CreditCard,
    label: 'Account Number',
    placeholder: 'Enter account number',
    type: 'text',
    autoComplete: 'username',
    maxLength: 12,
  },
  partnerCode: {
    icon: Key,
    label: 'Partner Code',
    placeholder: 'Enter partner code',
    type: 'text',
    autoComplete: 'username',
    transform: (value: string) => value.toUpperCase(),
  },
  password: {
    icon: Lock,
    label: 'Password',
    placeholder: 'Enter your password',
    type: 'password',
    autoComplete: 'current-password',
  },
  mfaCode: {
    icon: Smartphone,
    label: 'Authentication Code',
    placeholder: 'Enter 6-digit code',
    type: 'text',
    maxLength: 6,
    pattern: '[0-9]*',
  },
};

export function UniversalLoginForm({
  portalVariant,
  onLogin,
  onError,
  className = '',
  showRememberMe = true,
  showForgotPassword = true,
  redirectTo,
  customBranding,
}: UniversalLoginFormProps) {
  const { login, isLoading, error: authError } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [loginStep, setLoginStep] = useState<'credentials' | 'mfa'>('credentials');
  const [mfaRequired, setMfaRequired] = useState(false);
  const [validationErrors, setValidationErrors] = useState<Record<string, string[]>>({});

  // Portal configuration
  const portalConfig: PortalConfig = getPortalConfig(portalVariant);
  const portalTheme = getPortalTheme(portalVariant);
  const schema = LOGIN_SCHEMAS[portalVariant];

  // Form setup
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    setError,
    clearErrors,
    formState: { errors, isSubmitting },
  } = useForm<LoginCredentials>({
    resolver: zodResolver(schema),
    defaultValues: {
      rememberMe: false,
      rememberDevice: false,
    },
  });

  const watchedFields = watch();

  // Branding configuration
  const branding = {
    logo: customBranding?.logo || portalConfig.branding.logo,
    title: customBranding?.title || portalConfig.branding.loginTitle || portalConfig.name,
    subtitle: customBranding?.subtitle || portalConfig.branding.loginSubtitle,
    companyName: portalConfig.branding.companyName,
  };

  // Real-time field validation for Portal ID and Account Number
  const handlePortalIdChange = useCallback(
    (value: string) => {
      if (value.length === 0) return;

      const validation = validatePortalId(value);
      setValue('portalId', validation.formatted);

      if (!validation.isValid) {
        setValidationErrors((prev) => ({
          ...prev,
          portalId: validation.errors,
        }));
      } else {
        setValidationErrors((prev) => {
          const { portalId, ...rest } = prev;
          return rest;
        });
        clearErrors('portalId');
      }
    },
    [setValue, clearErrors]
  );

  const handleAccountNumberChange = useCallback(
    (value: string) => {
      if (value.length === 0) return;

      const validation = validateAccountNumber(value);
      setValue('accountNumber', validation.formatted);

      if (!validation.isValid) {
        setValidationErrors((prev) => ({
          ...prev,
          accountNumber: validation.errors,
        }));
      } else {
        setValidationErrors((prev) => {
          const { accountNumber, ...rest } = prev;
          return rest;
        });
        clearErrors('accountNumber');
      }
    },
    [setValue, clearErrors]
  );

  // Handle form submission
  const onSubmit = async (data: LoginCredentials) => {
    try {
      setValidationErrors({});

      const response = await login({
        ...data,
        portalType: portalVariant,
      });

      if (response.mfa?.required && !data.mfaCode) {
        setMfaRequired(true);
        setLoginStep('mfa');
        return;
      }

      if (response.user) {
        onLogin(response.user);
      }
    } catch (err) {
      const loginError = err as LoginError;

      if (loginError.field) {
        setError(loginError.field as keyof LoginCredentials, {
          message: loginError.message,
        });
      }

      onError?.(loginError);
    }
  };

  // Generate form fields based on portal configuration
  const getFormFields = () => {
    const fields: Array<{
      name: keyof LoginCredentials;
      config: (typeof FIELD_CONFIGS)[keyof typeof FIELD_CONFIGS];
      required: boolean;
    }> = [];

    // Add login method fields
    if (portalConfig.loginMethods.includes('email')) {
      fields.push({ name: 'email', config: FIELD_CONFIGS.email, required: true });
    }

    if (portalConfig.loginMethods.includes('portal_id') && portalVariant === 'customer') {
      fields.push({ name: 'portalId', config: FIELD_CONFIGS.portalId, required: false });
    }

    if (portalConfig.loginMethods.includes('account_number') && portalVariant === 'customer') {
      fields.push({ name: 'accountNumber', config: FIELD_CONFIGS.accountNumber, required: false });
    }

    if (portalConfig.loginMethods.includes('partner_code') && portalVariant === 'reseller') {
      fields.push({ name: 'partnerCode', config: FIELD_CONFIGS.partnerCode, required: false });
    }

    // Password is always required
    fields.push({ name: 'password', config: FIELD_CONFIGS.password, required: true });

    // MFA field if in MFA step
    if (loginStep === 'mfa') {
      fields.push({ name: 'mfaCode', config: FIELD_CONFIGS.mfaCode, required: true });
    }

    return fields;
  };

  // Apply portal theme
  useEffect(() => {
    const root = document.documentElement;
    Object.entries(portalTheme).forEach(([key, value]) => {
      root.style.setProperty(`--auth-${key}`, value);
    });
  }, [portalTheme]);

  const formFields = getFormFields();

  return (
    <div className={`auth-form-container ${className}`}>
      <style>{`
        .auth-form-container {
          --primary: var(--auth-primary);
          --secondary: var(--auth-secondary);
          --background: var(--auth-background);
          --foreground: var(--auth-foreground);
          --muted: var(--auth-muted);
          --border: var(--auth-border);
          --input: var(--auth-input);
          --ring: var(--auth-ring);
          --destructive: var(--auth-destructive);
          --success: var(--auth-success);
        }
      `}</style>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className='w-full max-w-md mx-auto bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden'
      >
        {/* Header */}
        <div
          className='px-8 pt-8 pb-6 text-center'
          style={{ backgroundColor: 'var(--auth-muted)' }}
        >
          {branding.logo && (
            <img
              src={branding.logo}
              alt={branding.companyName}
              className='h-12 w-auto mx-auto mb-4'
            />
          )}

          <div className='flex items-center justify-center mb-2'>
            <Shield className='w-6 h-6 mr-2' style={{ color: 'var(--primary)' }} />
            <h1 className='text-2xl font-bold text-gray-900'>{branding.title}</h1>
          </div>

          {branding.subtitle && <p className='text-sm text-gray-600'>{branding.subtitle}</p>}

          {/* Step indicator for MFA */}
          {loginStep === 'mfa' && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className='mt-4 px-4 py-2 bg-blue-50 border border-blue-200 rounded-lg'
            >
              <div className='flex items-center text-sm text-blue-700'>
                <Smartphone className='w-4 h-4 mr-2' />
                Two-factor authentication required
              </div>
            </motion.div>
          )}
        </div>

        {/* Form */}
        <div className='px-8 pb-8'>
          <form onSubmit={handleSubmit(onSubmit)} className='space-y-6'>
            {/* Authentication Error */}
            <AnimatePresence>
              {authError && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className='rounded-lg border border-red-200 bg-red-50 p-4'
                >
                  <div className='flex items-start'>
                    <AlertCircle className='h-5 w-5 text-red-400 mt-0.5' />
                    <div className='ml-3'>
                      <h3 className='text-sm font-medium text-red-800'>Authentication Failed</h3>
                      <p className='text-sm text-red-700 mt-1'>{authError.message}</p>

                      {authError.lockedUntil && (
                        <p className='text-xs text-red-600 mt-2'>
                          Account locked until {new Date(authError.lockedUntil).toLocaleString()}
                        </p>
                      )}

                      {authError.retryAfter && (
                        <p className='text-xs text-red-600 mt-2'>
                          Please try again in {authError.retryAfter} seconds
                        </p>
                      )}
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Dynamic Form Fields */}
            <AnimatePresence mode='wait'>
              <motion.div
                key={loginStep}
                initial={{ opacity: 0, x: loginStep === 'mfa' ? 20 : -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: loginStep === 'mfa' ? -20 : 20 }}
                transition={{ duration: 0.3 }}
                className='space-y-4'
              >
                {formFields.map((field) => {
                  const Icon = field.config.icon;
                  const fieldError = errors[field.name]?.message;
                  const validationError = validationErrors[field.name]?.[0];
                  const hasError = fieldError || validationError;

                  return (
                    <div key={field.name} className='space-y-1'>
                      <label
                        htmlFor={field.name}
                        className='block text-sm font-medium text-gray-700'
                      >
                        {field.config.label}
                        {field.required && <span className='text-red-500 ml-1'>*</span>}
                      </label>

                      <div className='relative'>
                        <div className='absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none'>
                          <Icon className='h-5 w-5 text-gray-400' />
                        </div>

                        <input
                          {...register(field.name, {
                            onChange: (e) => {
                              if (field.name === 'portalId') {
                                handlePortalIdChange(e.target.value);
                              } else if (field.name === 'accountNumber') {
                                handleAccountNumberChange(e.target.value);
                              } else if (field.config.transform) {
                                setValue(field.name, field.config.transform(e.target.value));
                              }
                            },
                          })}
                          type={
                            field.name === 'password' && !showPassword
                              ? 'password'
                              : field.config.type
                          }
                          placeholder={field.config.placeholder}
                          autoComplete={field.config.autoComplete}
                          maxLength={field.config.maxLength}
                          pattern={field.config.pattern}
                          disabled={isSubmitting || isLoading}
                          className={`
                            block w-full pl-10 pr-12 py-3 border rounded-lg
                            text-sm placeholder-gray-400
                            focus:outline-none focus:ring-2 focus:border-transparent
                            disabled:opacity-50 disabled:cursor-not-allowed
                            ${
                              hasError
                                ? 'border-red-300 focus:ring-red-500'
                                : 'border-gray-300 focus:ring-blue-500'
                            }
                          `}
                          style={{
                            backgroundColor: hasError ? '#FEF2F2' : 'var(--auth-input)',
                            color: 'var(--foreground)',
                          }}
                        />

                        {/* Password visibility toggle */}
                        {field.name === 'password' && (
                          <button
                            type='button'
                            onClick={() => setShowPassword(!showPassword)}
                            className='absolute inset-y-0 right-0 pr-3 flex items-center'
                            tabIndex={-1}
                          >
                            {showPassword ? (
                              <EyeOff className='h-5 w-5 text-gray-400 hover:text-gray-600' />
                            ) : (
                              <Eye className='h-5 w-5 text-gray-400 hover:text-gray-600' />
                            )}
                          </button>
                        )}

                        {/* Validation success indicator */}
                        {field.name === 'portalId' &&
                          watchedFields.portalId &&
                          validatePortalId(watchedFields.portalId).isValid && (
                            <div className='absolute inset-y-0 right-0 pr-3 flex items-center'>
                              <CheckCircle className='h-5 w-5 text-green-500' />
                            </div>
                          )}
                      </div>

                      {/* Field Error */}
                      <AnimatePresence>
                        {hasError && (
                          <motion.p
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className='text-sm text-red-600 mt-1'
                          >
                            {fieldError || validationError}
                          </motion.p>
                        )}
                      </AnimatePresence>

                      {/* Portal ID help text */}
                      {field.name === 'portalId' && (
                        <p className='text-xs text-gray-500 mt-1'>
                          Your Portal ID is 8 characters (letters A-Z, numbers 2-9)
                        </p>
                      )}
                    </div>
                  );
                })}
              </motion.div>
            </AnimatePresence>

            {/* Remember Me & Options */}
            {loginStep === 'credentials' && showRememberMe && (
              <div className='flex items-center justify-between'>
                <div className='flex items-center'>
                  <input
                    {...register('rememberMe')}
                    type='checkbox'
                    className='h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500'
                  />
                  <label htmlFor='rememberMe' className='ml-2 block text-sm text-gray-700'>
                    Remember me
                  </label>
                </div>

                {portalConfig.features.rememberDevice && (
                  <div className='flex items-center'>
                    <input
                      {...register('rememberDevice')}
                      type='checkbox'
                      className='h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500'
                    />
                    <label htmlFor='rememberDevice' className='ml-2 block text-sm text-gray-700'>
                      Remember device
                    </label>
                  </div>
                )}
              </div>
            )}

            {/* Submit Button */}
            <button
              type='submit'
              disabled={isSubmitting || isLoading}
              className='w-full flex justify-center items-center py-3 px-4 border border-transparent rounded-lg text-sm font-medium text-white focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
              style={{
                backgroundColor: 'var(--primary)',
                focusRingColor: 'var(--ring)',
              }}
            >
              {isSubmitting || isLoading ? (
                <>
                  <Loader2 className='animate-spin h-4 w-4 mr-2' />
                  Signing in...
                </>
              ) : loginStep === 'mfa' ? (
                'Verify Code'
              ) : (
                'Sign In'
              )}
            </button>

            {/* Additional Actions */}
            {loginStep === 'credentials' && (
              <div className='space-y-3'>
                {showForgotPassword && (
                  <div className='text-center'>
                    <button
                      type='button'
                      className='text-sm font-medium hover:underline'
                      style={{ color: 'var(--primary)' }}
                    >
                      Forgot your password?
                    </button>
                  </div>
                )}

                {/* Portal-specific help links */}
                {portalVariant === 'customer' && (
                  <div className='text-center space-y-2'>
                    <button
                      type='button'
                      className='block w-full text-sm text-blue-600 hover:underline'
                    >
                      Forgot your Portal ID?
                    </button>
                    <button
                      type='button'
                      className='block w-full text-sm text-blue-600 hover:underline'
                    >
                      Contact Support
                    </button>
                  </div>
                )}

                {(portalVariant === 'admin' || portalVariant === 'management-admin') && (
                  <div className='text-center'>
                    <p className='text-sm text-gray-600'>
                      Need access?{' '}
                      <button
                        type='button'
                        className='font-medium hover:underline'
                        style={{ color: 'var(--primary)' }}
                      >
                        Contact your administrator
                      </button>
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Back button for MFA step */}
            {loginStep === 'mfa' && (
              <button
                type='button'
                onClick={() => {
                  setLoginStep('credentials');
                  setMfaRequired(false);
                }}
                className='w-full text-sm text-gray-600 hover:text-gray-800 py-2'
              >
                ← Back to login
              </button>
            )}
          </form>
        </div>

        {/* Footer */}
        <div className='px-8 py-4 bg-gray-50 border-t border-gray-200'>
          <p className='text-xs text-center text-gray-500'>
            © {new Date().getFullYear()} {branding.companyName}. Powered by DotMac Framework.
          </p>
        </div>
      </motion.div>
    </div>
  );
}
