// Main form components
export { EntityForm, CustomerForm, TenantForm, UserForm, DeviceForm, ServiceForm } from './components/EntityForm/EntityForm';
export { FormField } from './components/EntityForm/FormField';
export { FormSection } from './components/EntityForm/FormSection';
export { FormActions } from './components/EntityForm/FormActions';

// Search components
export { UniversalSearch } from './components/UniversalSearch/UniversalSearch';

// Bulk operations
export { BulkOperations } from './components/BulkOperations/BulkOperations';

// Hooks
export { usePortalTheme } from './hooks/usePortalTheme';
export { useFormValidation } from './hooks/useFormValidation';
export { useEntityForm } from './hooks/useEntityForm';

// Schemas and validation
export {
  entitySchemas,
  getEntitySchema,
  validateEntity,
  validateField,
  baseCustomerSchema,
  tenantSchema,
  userSchema,
  deviceSchema,
  serviceSchema,
  addressSchema,
  phoneSchema,
} from './schemas';

// Configuration
export { generateEntityFormConfig } from './configs/entityConfigs';
export { getPortalTheme } from './configs/portalThemes';
export { getDefaultFilters } from './configs/searchConfigs';

// Types
export type {
  PortalVariant,
  EntityType,
  FormMode,
  BaseEntity,
  Customer,
  Tenant,
  User,
  Device,
  Service,
  FilterConfig,
  SearchQuery,
  BulkOperation,
  FormFieldConfig,
  EntityFormConfig,
  PortalTheme,
  ValidationContext,
} from './types';

// Utilities
export { cn } from './utils/cn';
export { formatEntityName, getEntityDisplayName } from './utils/formatting';
export { validateFormData, sanitizeFormData } from './utils/validation';
