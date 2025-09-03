/**
 * Field Configuration Helpers
 *
 * Simple, type-safe helpers for form field configuration
 * Following our proven pattern from the forms package
 */

import type { PortalVariant } from '../types';

export interface FieldConfig {
  name: string;
  type: string;
  placeholder: string;
  label: string;
  icon?: any;
  autoComplete?: string;
  maxLength?: number;
  pattern?: string;
  transform?: (value: string) => string;
  required?: boolean;
}

/**
 * Get form fields for a portal variant
 * Simple helper that returns consistent field configurations
 */
export function getPortalFields(portalVariant: PortalVariant): FieldConfig[] {
  const baseFields: FieldConfig[] = [
    {
      name: 'password',
      type: 'password',
      placeholder: 'Enter your password',
      label: 'Password',
      autoComplete: 'current-password',
      required: true,
    },
  ];

  // Add portal-specific login fields
  switch (portalVariant) {
    case 'customer':
      return [
        {
          name: 'portalId',
          type: 'text',
          placeholder: 'Enter Portal ID',
          label: 'Portal ID',
          autoComplete: 'username',
          maxLength: 20,
          transform: (value: string) => value.toUpperCase().trim(),
          required: true,
        },
        ...baseFields,
      ];

    case 'reseller':
      return [
        {
          name: 'partnerCode',
          type: 'text',
          placeholder: 'Enter Partner Code',
          label: 'Partner Code',
          autoComplete: 'username',
          maxLength: 15,
          transform: (value: string) => value.toUpperCase().trim(),
          required: true,
        },
        ...baseFields,
      ];

    default:
      return [
        {
          name: 'email',
          type: 'email',
          placeholder: 'Enter your email',
          label: 'Email',
          autoComplete: 'email',
          required: true,
        },
        ...baseFields,
      ];
  }
}

/**
 * Get field property safely
 */
export function getFieldProp<T extends keyof FieldConfig>(
  field: FieldConfig,
  prop: T,
  fallback?: FieldConfig[T]
): FieldConfig[T] {
  return field[prop] ?? fallback;
}

/**
 * Transform field value if transformer exists
 */
export function transformFieldValue(field: FieldConfig, value: string): string {
  return field.transform ? field.transform(value) : value;
}
