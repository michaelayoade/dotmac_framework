export interface ValidationRule {
  validate: (value: unknown) => boolean;
  message: string;
}

export interface FieldValidationConfig {
  required?: boolean;
  rules?: ValidationRule[];
  dependsOn?: string[];
}

export interface FormValidationConfig {
  [fieldName: string]: FieldValidationConfig;
}

export interface ValidationError {
  field: string;
  message: string;
}

export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
  fieldErrors: Record<string, string>;
}

// Built-in validation rules
export const validationRules = {
  email: {
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      const emailRegex = /^[^\s@]+@[^\s@]+.[^\s@]+$/;
      return emailRegex.test(value);
    },
    message: 'Please enter a valid email address',
  },

  minLength: (length: number) => ({
    validate: (value: unknown) => typeof value === 'string' && value.length >= length,
    message: `Must be at least ${length} characters long`,
  }),

  maxLength: (length: number) => ({
    validate: (value: unknown) => typeof value === 'string' && value.length <= length,
    message: `Must be no more than ${length} characters long`,
  }),

  strongPassword: {
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      // At least 8 characters, 1 uppercase, 1 lowercase, 1 number, 1 special char
      const strongPasswordRegex =
        /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;
      return strongPasswordRegex.test(value);
    },
    message:
      'Password must contain at least 8 characters with uppercase, lowercase, number, and special character',
  },

  phoneNumber: {
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      const phoneRegex = /^\+?[\d\s\-()]{10,}$/;
      return phoneRegex.test(value);
    },
    message: 'Please enter a valid phone number',
  },

  url: {
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      try {
        new URL(value);
        return true;
      } catch {
        return false;
      }
    },
    message: 'Please enter a valid URL',
  },

  numeric: {
    validate: (value: unknown) =>
      typeof value === 'string' && !Number.isNaN(Number(value)) && !Number.isNaN(parseFloat(value)),
    message: 'Must be a valid number',
  },

  positiveNumber: {
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      const num = parseFloat(value);
      return !Number.isNaN(num) && num > 0;
    },
    message: 'Must be a positive number',
  },

  integer: {
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      const num = parseInt(value, 10);
      return !Number.isNaN(num) && num.toString() === value;
    },
    message: 'Must be a whole number',
  },

  alphanumeric: {
    validate: (value: unknown) => typeof value === 'string' && /^[a-zA-Z0-9]+$/.test(value),
    message: 'Must contain only letters and numbers',
  },

  noWhitespace: {
    validate: (value: unknown) => typeof value === 'string' && !/\s/.test(value),
    message: 'Must not contain spaces',
  },

  matchField: (fieldName: string, getFieldValue: (name: string) => any) => ({
    validate: (value: unknown) => value === getFieldValue(fieldName),
    message: `Must match ${fieldName}`,
  }),
};

export class FormValidator {
  private config: FormValidationConfig;

  private formData: Record<string, unknown> = {};

  constructor(config: FormValidationConfig) {
    this.config = config;
  }

  setFormData(data: Record<string, unknown>) {
    this.formData = data;
  }

  validateField(fieldName: string, value: unknown): ValidationError[] {
    const fieldConfig = this.config[fieldName];
    if (!fieldConfig) {
      return [];
    }

    const errors: ValidationError[] = [];

    // Check required
    if (fieldConfig.required && this.isEmpty(value)) {
      errors.push({
        field: fieldName,
        message: 'This field is required',
      });
      return errors; // Don't run other validations if required and empty
    }

    // Skip other validations if field is empty but not required
    if (!fieldConfig.required && this.isEmpty(value)) {
      return errors;
    }

    // Run custom validation rules
    if (fieldConfig.rules) {
      for (const rule of fieldConfig.rules) {
        if (!rule.validate(value)) {
          errors.push({
            field: fieldName,
            message: rule.message,
          });
        }
      }
    }

    return errors;
  }

  validateForm(formData: Record<string, unknown>): ValidationResult {
    this.setFormData(formData);
    const allErrors: ValidationError[] = [];
    const fieldErrors: Record<string, string> = {};

    // Validate each configured field
    for (const fieldName in this.config) {
      const fieldValue = formData[fieldName];
      const errors = this.validateField(fieldName, fieldValue);

      if (errors.length > 0) {
        allErrors.push(...errors);
        fieldErrors[fieldName] = errors[0]?.message || 'Validation error'; // Show first error for each field
      }
    }

    return {
      isValid: allErrors.length === 0,
      errors: allErrors,
      fieldErrors,
    };
  }

  validateFormAsync(formData: Record<string, unknown>): Promise<ValidationResult> {
    // For future async validation support (e.g., server-side checks)
    return Promise.resolve(this.validateForm(formData));
  }

  private isEmpty(value: unknown): boolean {
    if (value === null || value === undefined) {
      return true;
    }
    if (typeof value === 'string') {
      return value.trim() === '';
    }
    if (Array.isArray(value)) {
      return value.length === 0;
    }
    if (typeof value === 'object') {
      return Object.keys(value).length === 0;
    }
    return false;
  }

  // Utility method to get validation config for a specific field
  getFieldConfig(fieldName: string): FieldValidationConfig | undefined {
    return this.config[fieldName];
  }

  // Check if a field is required
  isFieldRequired(fieldName: string): boolean {
    return this.config[fieldName]?.required ?? false;
  }
}

// Debounced validation for real-time validation
export function createDebouncedValidator(validator: FormValidator, delay: number = 300) {
  let timeoutId: NodeJS.Timeout;

  return (fieldName: string, value: unknown, callback: (errors: ValidationError[]) => void) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => {
      const errors = validator.validateField(fieldName, value);
      callback(errors);
    }, delay);
  };
}

// Pre-configured validators for common forms
export const commonValidators = {
  loginForm: new FormValidator({
    email: {
      required: true,
      rules: [validationRules.email],
    },
    password: {
      required: true,
      rules: [validationRules.minLength(1)], // Basic requirement for login
    },
  }),

  registrationForm: new FormValidator({
    firstName: {
      required: true,
      rules: [validationRules.minLength(2), validationRules.maxLength(50)],
    },
    lastName: {
      required: true,
      rules: [validationRules.minLength(2), validationRules.maxLength(50)],
    },
    email: {
      required: true,
      rules: [validationRules.email],
    },
    password: {
      required: true,
      rules: [validationRules.strongPassword],
    },
    confirmPassword: {
      required: true,
      rules: [
        {
          validate: (_value: unknown) => {
            // This would need access to the form data context
            return true; // Implement in component
          },
          message: 'Passwords must match',
        },
      ],
    },
  }),

  profileForm: new FormValidator({
    firstName: {
      required: true,
      rules: [validationRules.minLength(2), validationRules.maxLength(50)],
    },
    lastName: {
      required: true,
      rules: [validationRules.minLength(2), validationRules.maxLength(50)],
    },
    email: {
      required: true,
      rules: [validationRules.email],
    },
    phone: {
      required: false,
      rules: [validationRules.phoneNumber],
    },
    website: {
      required: false,
      rules: [validationRules.url],
    },
  }),

  passwordChangeForm: new FormValidator({
    currentPassword: {
      required: true,
      rules: [validationRules.minLength(1)],
    },
    newPassword: {
      required: true,
      rules: [validationRules.strongPassword],
    },
    confirmNewPassword: {
      required: true,
      rules: [
        {
          validate: (_value: unknown) => true, // Implement in component
          message: 'Passwords must match',
        },
      ],
    },
  }),
};

// Utility function to create validation messages
export function formatValidationMessage(
  fieldName: string,
  message: string,
  customFieldNames?: Record<string, string>
): string {
  const displayName =
    customFieldNames?.[fieldName] ||
    fieldName.charAt(0).toUpperCase() + fieldName.slice(1).replace(/([A-Z])/g, ' $1');

  return message.replace(/this field/i, displayName.toLowerCase());
}

/**
 * ISP-Specific Validation Rules
 */
export const ispValidationRules = {
  ipAddress: {
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      const ipv4Regex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
      const ipv6Regex = /^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$/;
      return ipv4Regex.test(value) || ipv6Regex.test(value);
    },
    message: 'Please enter a valid IP address',
  },

  macAddress: {
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      const macRegex = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/;
      return macRegex.test(value);
    },
    message: 'Please enter a valid MAC address (e.g., 00:1A:2B:3C:4D:5E)',
  },

  vlan: {
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      const vlan = parseInt(value, 10);
      return !isNaN(vlan) && vlan >= 1 && vlan <= 4094;
    },
    message: 'VLAN ID must be between 1 and 4094',
  },

  bandwidth: {
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      const bandwidthRegex = /^\d+(\.\d+)?\s?(Kbps|Mbps|Gbps)$/i;
      return bandwidthRegex.test(value);
    },
    message: 'Please enter a valid bandwidth (e.g., 100 Mbps)',
  },

  serviceId: {
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      const serviceIdRegex = /^SVC-[A-Z0-9]{6,12}$/;
      return serviceIdRegex.test(value);
    },
    message: 'Service ID must follow format SVC-XXXXXX',
  },

  customerId: {
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      const customerIdRegex = /^CUST-[A-Z0-9]{6,12}$/;
      return customerIdRegex.test(value);
    },
    message: 'Customer ID must follow format CUST-XXXXXX',
  },

  invoiceNumber: {
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      const invoiceRegex = /^INV-\d{6,12}$/;
      return invoiceRegex.test(value);
    },
    message: 'Invoice number must follow format INV-000000',
  },

  currency: {
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      const currencyRegex = /^\d+(\.\d{2})?$/;
      return currencyRegex.test(value);
    },
    message: 'Please enter a valid currency amount (e.g., 99.99)',
  },

  networkPort: {
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      const port = parseInt(value, 10);
      return !isNaN(port) && port >= 1 && port <= 65535;
    },
    message: 'Port number must be between 1 and 65535',
  },

  subnetMask: {
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      // CIDR notation (e.g., /24) or full subnet mask (e.g., 255.255.255.0)
      const cidrRegex = /^\/([1-9]|[12][0-9]|3[0-2])$/;
      const fullMaskRegex = /^(255\.(255\.|254\.|252\.|248\.|240\.|224\.|192\.|128\.|0\.)){3}(255|254|252|248|240|224|192|128|0)$/;
      return cidrRegex.test(value) || fullMaskRegex.test(value);
    },
    message: 'Please enter a valid subnet mask or CIDR notation',
  },

  serialNumber: {
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      // Generic serial number validation - alphanumeric, hyphens, underscores
      const serialRegex = /^[A-Z0-9\-_]{6,20}$/i;
      return serialRegex.test(value);
    },
    message: 'Serial number must be 6-20 alphanumeric characters',
  },

  deviceModel: {
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      const modelRegex = /^[A-Z0-9\-_\s]{2,50}$/i;
      return modelRegex.test(value);
    },
    message: 'Device model must be 2-50 characters',
  },

  ticketNumber: {
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      const ticketRegex = /^(TKT|INC|REQ)-[0-9]{6,12}$/;
      return ticketRegex.test(value);
    },
    message: 'Ticket number must follow format TKT-000000, INC-000000, or REQ-000000',
  },

  coordinates: {
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      const coordRegex = /^-?\d{1,3}\.\d{4,6},-?\d{1,3}\.\d{4,6}$/;
      return coordRegex.test(value);
    },
    message: 'Coordinates must be in format "latitude,longitude" (e.g., 40.7128,-74.0060)',
  },

  contractNumber: {
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      const contractRegex = /^CON-[A-Z0-9]{8,16}$/;
      return contractRegex.test(value);
    },
    message: 'Contract number must follow format CON-XXXXXXXX',
  },

  // ISP-specific business validations
  recurringAmount: (minAmount: number = 0.01) => ({
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      const amount = parseFloat(value);
      return !isNaN(amount) && amount >= minAmount;
    },
    message: `Recurring amount must be at least $${minAmount.toFixed(2)}`,
  }),

  billingCycle: {
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      const validCycles = ['monthly', 'quarterly', 'semi-annually', 'annually'];
      return validCycles.includes(value.toLowerCase());
    },
    message: 'Please select a valid billing cycle',
  },

  serviceLevel: {
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      const validLevels = ['basic', 'standard', 'premium', 'enterprise'];
      return validLevels.includes(value.toLowerCase());
    },
    message: 'Please select a valid service level',
  },

  uptime: {
    validate: (value: unknown) => {
      if (typeof value !== 'string') return false;
      const uptimeRegex = /^(9[0-9](\.\d{1,3})?|100)%$/;
      return uptimeRegex.test(value);
    },
    message: 'Uptime must be between 90% and 100%',
  },
};

/**
 * ISP-Specific Form Validators
 */
export const ispValidators = {
  customerRegistrationForm: new FormValidator({
    firstName: {
      required: true,
      rules: [validationRules.minLength(2), validationRules.maxLength(50)],
    },
    lastName: {
      required: true,
      rules: [validationRules.minLength(2), validationRules.maxLength(50)],
    },
    email: {
      required: true,
      rules: [validationRules.email],
    },
    phone: {
      required: true,
      rules: [validationRules.phoneNumber],
    },
    address: {
      required: true,
      rules: [validationRules.minLength(5), validationRules.maxLength(200)],
    },
    serviceType: {
      required: true,
      rules: [validationRules.minLength(1)],
    },
    billingCycle: {
      required: true,
      rules: [ispValidationRules.billingCycle],
    },
  }),

  networkDeviceForm: new FormValidator({
    deviceName: {
      required: true,
      rules: [validationRules.minLength(2), validationRules.maxLength(50)],
    },
    ipAddress: {
      required: true,
      rules: [ispValidationRules.ipAddress],
    },
    macAddress: {
      required: false,
      rules: [ispValidationRules.macAddress],
    },
    vlanId: {
      required: false,
      rules: [ispValidationRules.vlan],
    },
    deviceModel: {
      required: true,
      rules: [ispValidationRules.deviceModel],
    },
    serialNumber: {
      required: false,
      rules: [ispValidationRules.serialNumber],
    },
  }),

  serviceProvisioningForm: new FormValidator({
    customerId: {
      required: true,
      rules: [ispValidationRules.customerId],
    },
    serviceType: {
      required: true,
      rules: [validationRules.minLength(1)],
    },
    bandwidth: {
      required: true,
      rules: [ispValidationRules.bandwidth],
    },
    ipAddress: {
      required: false,
      rules: [ispValidationRules.ipAddress],
    },
    vlanId: {
      required: false,
      rules: [ispValidationRules.vlan],
    },
    installationDate: {
      required: true,
      rules: [validationRules.minLength(1)],
    },
    contractNumber: {
      required: false,
      rules: [ispValidationRules.contractNumber],
    },
  }),

  billingForm: new FormValidator({
    customerId: {
      required: true,
      rules: [ispValidationRules.customerId],
    },
    amount: {
      required: true,
      rules: [ispValidationRules.currency, ispValidationRules.recurringAmount()],
    },
    billingCycle: {
      required: true,
      rules: [ispValidationRules.billingCycle],
    },
    dueDate: {
      required: true,
      rules: [validationRules.minLength(1)],
    },
    description: {
      required: true,
      rules: [validationRules.minLength(5), validationRules.maxLength(500)],
    },
  }),

  supportTicketForm: new FormValidator({
    customerId: {
      required: true,
      rules: [ispValidationRules.customerId],
    },
    title: {
      required: true,
      rules: [validationRules.minLength(5), validationRules.maxLength(100)],
    },
    description: {
      required: true,
      rules: [validationRules.minLength(10), validationRules.maxLength(2000)],
    },
    priority: {
      required: true,
      rules: [validationRules.minLength(1)],
    },
    category: {
      required: true,
      rules: [validationRules.minLength(1)],
    },
    contactEmail: {
      required: true,
      rules: [validationRules.email],
    },
    contactPhone: {
      required: false,
      rules: [validationRules.phoneNumber],
    },
  }),

  paymentForm: new FormValidator({
    amount: {
      required: true,
      rules: [ispValidationRules.currency, ispValidationRules.recurringAmount()],
    },
    paymentMethod: {
      required: true,
      rules: [validationRules.minLength(1)],
    },
    invoiceId: {
      required: false,
      rules: [ispValidationRules.invoiceNumber],
    },
    reference: {
      required: false,
      rules: [validationRules.maxLength(100)],
    },
    notes: {
      required: false,
      rules: [validationRules.maxLength(500)],
    },
  }),
};

/**
 * Validation utilities for ISP operations
 */
export const ispValidationUtils = {
  validateServiceConfiguration: (config: Record<string, any>): ValidationResult => {
    const errors: ValidationError[] = [];

    // Check required fields based on service type
    if (config.serviceType === 'dedicated') {
      if (!config.staticIp) {
        errors.push({ field: 'staticIp', message: 'Static IP is required for dedicated services' });
      }
      if (!config.bandwidth || parseInt(config.bandwidth) < 10) {
        errors.push({ field: 'bandwidth', message: 'Dedicated services require minimum 10 Mbps' });
      }
    }

    if (config.serviceType === 'residential' && config.bandwidth) {
      const bandwidth = parseInt(config.bandwidth);
      if (bandwidth > 1000) {
        errors.push({ field: 'bandwidth', message: 'Residential services limited to 1 Gbps' });
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      fieldErrors: errors.reduce((acc, error) => {
        acc[error.field] = error.message;
        return acc;
      }, {} as Record<string, string>)
    };
  },

  validateNetworkConfiguration: (config: Record<string, any>): ValidationResult => {
    const errors: ValidationError[] = [];

    // Validate IP ranges don't conflict
    if (config.ipRanges && Array.isArray(config.ipRanges)) {
      const ranges = config.ipRanges.filter(Boolean);
      if (ranges.length !== new Set(ranges).size) {
        errors.push({ field: 'ipRanges', message: 'Duplicate IP ranges detected' });
      }
    }

    // Validate VLAN assignments
    if (config.vlans && Array.isArray(config.vlans)) {
      const vlans = config.vlans.map((v: any) => parseInt(v)).filter((v: number) => !isNaN(v));
      if (vlans.some((v: number) => v < 1 || v > 4094)) {
        errors.push({ field: 'vlans', message: 'VLAN IDs must be between 1 and 4094' });
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      fieldErrors: errors.reduce((acc, error) => {
        acc[error.field] = error.message;
        return acc;
      }, {} as Record<string, string>)
    };
  },

  validateBillingRules: (rules: Record<string, any>): ValidationResult => {
    const errors: ValidationError[] = [];

    // Validate billing amounts
    if (rules.recurringCharges) {
      Object.entries(rules.recurringCharges).forEach(([key, value]) => {
        const amount = parseFloat(value as string);
        if (isNaN(amount) || amount <= 0) {
          errors.push({ field: `recurringCharges.${key}`, message: 'Recurring charges must be positive amounts' });
        }
      });
    }

    // Validate tax rates
    if (rules.taxRate !== undefined) {
      const taxRate = parseFloat(rules.taxRate);
      if (isNaN(taxRate) || taxRate < 0 || taxRate > 100) {
        errors.push({ field: 'taxRate', message: 'Tax rate must be between 0% and 100%' });
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      fieldErrors: errors.reduce((acc, error) => {
        acc[error.field] = error.message;
        return acc;
      }, {} as Record<string, string>)
    };
  },
};
