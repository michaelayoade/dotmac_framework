import { ProfileData } from '../types';

export const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
};

export const formatShortDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
};

export const validateEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

export const validatePhone = (phone: string): boolean => {
  const phoneRegex = /^[\+]?[1-9][\d]{0,15}$/;
  const cleanPhone = phone.replace(/[\s\-\(\)]/g, '');
  return phoneRegex.test(cleanPhone);
};

export const formatPhoneDisplay = (phone: string): string => {
  const cleaned = phone.replace(/\D/g, '');
  if (cleaned.length === 10) {
    return `(${cleaned.slice(0, 3)}) ${cleaned.slice(3, 6)}-${cleaned.slice(6)}`;
  }
  if (cleaned.length === 11 && cleaned[0] === '1') {
    return `+1 (${cleaned.slice(1, 4)}) ${cleaned.slice(4, 7)}-${cleaned.slice(7)}`;
  }
  return phone;
};

export const validateProfileData = (data: Partial<ProfileData>): Record<string, string> => {
  const errors: Record<string, string> = {};

  if (data.firstName && data.firstName.trim().length < 1) {
    errors.firstName = 'First name is required';
  }

  if (data.lastName && data.lastName.trim().length < 1) {
    errors.lastName = 'Last name is required';
  }

  if (data.email && !validateEmail(data.email)) {
    errors.email = 'Please enter a valid email address';
  }

  if (data.phone && !validatePhone(data.phone)) {
    errors.phone = 'Please enter a valid phone number';
  }

  if (data.dateOfBirth) {
    const birthDate = new Date(data.dateOfBirth);
    const today = new Date();
    const age = today.getFullYear() - birthDate.getFullYear();
    if (age < 13 || age > 120) {
      errors.dateOfBirth = 'Please enter a valid date of birth';
    }
  }

  if (data.address) {
    if (data.address.street && data.address.street.trim().length < 1) {
      errors['address.street'] = 'Street address is required';
    }
    if (data.address.city && data.address.city.trim().length < 1) {
      errors['address.city'] = 'City is required';
    }
    if (data.address.zipCode && !/^\d{5}(-\d{4})?$/.test(data.address.zipCode)) {
      errors['address.zipCode'] = 'Please enter a valid ZIP code';
    }
  }

  if (data.emergencyContact) {
    if (data.emergencyContact.name && data.emergencyContact.name.trim().length < 1) {
      errors['emergencyContact.name'] = 'Emergency contact name is required';
    }
    if (data.emergencyContact.phone && !validatePhone(data.emergencyContact.phone)) {
      errors['emergencyContact.phone'] = 'Please enter a valid phone number';
    }
    if (data.emergencyContact.email && !validateEmail(data.emergencyContact.email)) {
      errors['emergencyContact.email'] = 'Please enter a valid email address';
    }
  }

  return errors;
};

export const getInitials = (firstName: string, lastName: string): string => {
  return `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase();
};

export const getFullName = (firstName: string, lastName: string): string => {
  return `${firstName} ${lastName}`.trim();
};

export const deepUpdateObject = (obj: any, path: string, value: any): any => {
  const keys = path.split('.');
  const newObj = { ...obj };
  let current = newObj;

  for (let i = 0; i < keys.length - 1; i++) {
    const key = keys[i];
    if (!current[key] || typeof current[key] !== 'object') {
      current[key] = {};
    }
    current[key] = { ...current[key] };
    current = current[key];
  }

  current[keys[keys.length - 1]] = value;
  return newObj;
};

export const getCountryOptions = () => [
  { value: 'US', label: 'United States' },
  { value: 'CA', label: 'Canada' },
  { value: 'MX', label: 'Mexico' },
  { value: 'GB', label: 'United Kingdom' },
  { value: 'DE', label: 'Germany' },
  { value: 'FR', label: 'France' },
  { value: 'AU', label: 'Australia' },
  { value: 'JP', label: 'Japan' },
];

export const getStateOptions = () => [
  { value: 'AL', label: 'Alabama' },
  { value: 'AK', label: 'Alaska' },
  { value: 'AZ', label: 'Arizona' },
  { value: 'AR', label: 'Arkansas' },
  { value: 'CA', label: 'California' },
  { value: 'CO', label: 'Colorado' },
  { value: 'CT', label: 'Connecticut' },
  { value: 'DE', label: 'Delaware' },
  { value: 'FL', label: 'Florida' },
  { value: 'GA', label: 'Georgia' },
  { value: 'HI', label: 'Hawaii' },
  { value: 'ID', label: 'Idaho' },
  { value: 'IL', label: 'Illinois' },
  { value: 'IN', label: 'Indiana' },
  { value: 'IA', label: 'Iowa' },
  { value: 'KS', label: 'Kansas' },
  { value: 'KY', label: 'Kentucky' },
  { value: 'LA', label: 'Louisiana' },
  { value: 'ME', label: 'Maine' },
  { value: 'MD', label: 'Maryland' },
  { value: 'MA', label: 'Massachusetts' },
  { value: 'MI', label: 'Michigan' },
  { value: 'MN', label: 'Minnesota' },
  { value: 'MS', label: 'Mississippi' },
  { value: 'MO', label: 'Missouri' },
  { value: 'MT', label: 'Montana' },
  { value: 'NE', label: 'Nebraska' },
  { value: 'NV', label: 'Nevada' },
  { value: 'NH', label: 'New Hampshire' },
  { value: 'NJ', label: 'New Jersey' },
  { value: 'NM', label: 'New Mexico' },
  { value: 'NY', label: 'New York' },
  { value: 'NC', label: 'North Carolina' },
  { value: 'ND', label: 'North Dakota' },
  { value: 'OH', label: 'Ohio' },
  { value: 'OK', label: 'Oklahoma' },
  { value: 'OR', label: 'Oregon' },
  { value: 'PA', label: 'Pennsylvania' },
  { value: 'RI', label: 'Rhode Island' },
  { value: 'SC', label: 'South Carolina' },
  { value: 'SD', label: 'South Dakota' },
  { value: 'TN', label: 'Tennessee' },
  { value: 'TX', label: 'Texas' },
  { value: 'UT', label: 'Utah' },
  { value: 'VT', label: 'Vermont' },
  { value: 'VA', label: 'Virginia' },
  { value: 'WA', label: 'Washington' },
  { value: 'WV', label: 'West Virginia' },
  { value: 'WI', label: 'Wisconsin' },
  { value: 'WY', label: 'Wyoming' },
];

export const getTimezoneOptions = () => [
  { value: 'America/Los_Angeles', label: 'Pacific Time (PT)' },
  { value: 'America/Denver', label: 'Mountain Time (MT)' },
  { value: 'America/Chicago', label: 'Central Time (CT)' },
  { value: 'America/New_York', label: 'Eastern Time (ET)' },
  { value: 'America/Anchorage', label: 'Alaska Time (AKT)' },
  { value: 'Pacific/Honolulu', label: 'Hawaii Time (HST)' },
];

export const getLanguageOptions = () => [
  { value: 'en-US', label: 'English (US)' },
  { value: 'en-GB', label: 'English (UK)' },
  { value: 'es-ES', label: 'Spanish (Spain)' },
  { value: 'es-MX', label: 'Spanish (Mexico)' },
  { value: 'fr-FR', label: 'French' },
  { value: 'de-DE', label: 'German' },
  { value: 'it-IT', label: 'Italian' },
  { value: 'pt-BR', label: 'Portuguese (Brazil)' },
  { value: 'ja-JP', label: 'Japanese' },
  { value: 'ko-KR', label: 'Korean' },
  { value: 'zh-CN', label: 'Chinese (Simplified)' },
];

export const getCurrencyOptions = () => [
  { value: 'USD', label: 'USD ($)', symbol: '$' },
  { value: 'EUR', label: 'EUR (€)', symbol: '€' },
  { value: 'GBP', label: 'GBP (£)', symbol: '£' },
  { value: 'CAD', label: 'CAD ($)', symbol: 'C$' },
  { value: 'JPY', label: 'JPY (¥)', symbol: '¥' },
  { value: 'AUD', label: 'AUD ($)', symbol: 'A$' },
];

export const getDateFormatOptions = () => [
  { value: 'MM/DD/YYYY', label: 'MM/DD/YYYY', example: '01/15/2024' },
  { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY', example: '15/01/2024' },
  { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD', example: '2024-01-15' },
  { value: 'DD-MM-YYYY', label: 'DD-MM-YYYY', example: '15-01-2024' },
];

export const getRelationshipOptions = () => [
  { value: 'Spouse', label: 'Spouse' },
  { value: 'Partner', label: 'Partner' },
  { value: 'Parent', label: 'Parent' },
  { value: 'Child', label: 'Child' },
  { value: 'Sibling', label: 'Sibling' },
  { value: 'Grandparent', label: 'Grandparent' },
  { value: 'Grandchild', label: 'Grandchild' },
  { value: 'Friend', label: 'Friend' },
  { value: 'Colleague', label: 'Colleague' },
  { value: 'Neighbor', label: 'Neighbor' },
  { value: 'Other', label: 'Other' },
];
