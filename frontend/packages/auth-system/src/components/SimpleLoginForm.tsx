/**
 * Simple Login Form
 *
 * Pragmatic, functional login form following our proven patterns
 * Used until UniversalLoginForm TypeScript issues are resolved
 */

import React, { useState } from 'react';
import type { PortalVariant, LoginCredentials } from '../types';
import { getPortalFields } from '../helpers/fieldHelpers';

interface SimpleLoginFormProps {
  portalVariant: PortalVariant;
  onSubmit: (credentials: LoginCredentials) => Promise<void>;
  isLoading?: boolean;
  error?: any;
  className?: string;
}

export function SimpleLoginForm({
  portalVariant,
  onSubmit,
  isLoading = false,
  error,
  className = '',
}: SimpleLoginFormProps) {
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [showPassword, setShowPassword] = useState(false);

  const fields = getPortalFields(portalVariant);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isLoading) return;

    const credentials: LoginCredentials = {
      ...formData,
      portalType: portalVariant,
    } as LoginCredentials;

    await onSubmit(credentials);
  };

  const handleInputChange = (name: string, value: string) => {
    const field = fields.find(f => f.name === name);
    const transformedValue = field?.transform ? field.transform(value) : value;
    setFormData(prev => ({ ...prev, [name]: transformedValue }));
  };

  return (
    <div className={`auth-form ${className}`}>
      <style>{`
        .auth-form {
          max-width: 400px;
          margin: 0 auto;
          padding: 2rem;
          border: 1px solid #e5e7eb;
          border-radius: 0.5rem;
          background: white;
        }
        .form-field {
          margin-bottom: 1rem;
        }
        .form-label {
          display: block;
          margin-bottom: 0.5rem;
          font-weight: 500;
          color: #374151;
        }
        .form-input {
          width: 100%;
          padding: 0.75rem;
          border: 1px solid #d1d5db;
          border-radius: 0.375rem;
          font-size: 1rem;
        }
        .form-input:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }
        .form-button {
          width: 100%;
          padding: 0.75rem;
          background: #3b82f6;
          color: white;
          border: none;
          border-radius: 0.375rem;
          font-size: 1rem;
          font-weight: 500;
          cursor: pointer;
        }
        .form-button:hover {
          background: #2563eb;
        }
        .form-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .form-error {
          margin-top: 1rem;
          padding: 0.75rem;
          background: #fef2f2;
          border: 1px solid #fecaca;
          border-radius: 0.375rem;
          color: #dc2626;
        }
        .password-toggle {
          position: absolute;
          right: 0.75rem;
          top: 50%;
          transform: translateY(-50%);
          background: none;
          border: none;
          cursor: pointer;
          color: #6b7280;
        }
        .password-field {
          position: relative;
        }
      `}</style>

      <h2>Sign In</h2>

      <form onSubmit={handleSubmit}>
        {fields.map(field => (
          <div key={field.name} className="form-field">
            <label className="form-label" htmlFor={field.name}>
              {field.label}
            </label>

            <div className={field.type === 'password' ? 'password-field' : ''}>
              <input
                id={field.name}
                name={field.name}
                type={field.type === 'password' && !showPassword ? 'password' : 'text'}
                placeholder={field.placeholder}
                value={formData[field.name] || ''}
                onChange={(e) => handleInputChange(field.name, e.target.value)}
                required={field.required}
                maxLength={field.maxLength}
                pattern={field.pattern}
                autoComplete={field.autoComplete}
                disabled={isLoading}
                className="form-input"
              />

              {field.type === 'password' && (
                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? '👁️' : '👁️‍🗨️'}
                </button>
              )}
            </div>
          </div>
        ))}

        <button
          type="submit"
          disabled={isLoading}
          className="form-button"
        >
          {isLoading ? 'Signing In...' : 'Sign In'}
        </button>
      </form>

      {error && (
        <div className="form-error">
          {error.message || 'Login failed. Please try again.'}
        </div>
      )}
    </div>
  );
}
