import { z } from 'zod';

// Component metadata schema
export const ComponentMetadataSchema = z.object({
  name: z.string().min(1),
  version: z.string().regex(/^\d+\.\d+\.\d+$/, 'Version must follow semver format'),
  description: z.string().optional(),
  category: z.enum([
    'atomic',
    'molecular',
    'organism',
    'template',
    'page',
    'layout',
    'form',
    'data-display',
    'feedback',
    'navigation',
    'utility',
  ]),
  portal: z.enum(['admin', 'customer', 'reseller', 'shared', 'headless']),
  dependencies: z.array(z.string()).default([]),
  props: z
    .record(
      z.object({
        type: z.string(),
        required: z.boolean().default(false),
        description: z.string().optional(),
        defaultValue: z.any().optional(),
      })
    )
    .optional(),
  accessibility: z
    .object({
      ariaSupport: z.boolean().default(true),
      keyboardSupport: z.boolean().default(false),
      focusManagement: z.boolean().default(false),
      screenReaderSupport: z.boolean().default(true),
      wcagLevel: z.enum(['A', 'AA', 'AAA']).default('AA'),
    })
    .optional(),
  security: z
    .object({
      xssProtection: z.boolean().default(true),
      csrfProtection: z.boolean().default(false),
      inputSanitization: z.boolean().default(false),
      outputEncoding: z.boolean().default(false),
    })
    .optional(),
  performance: z
    .object({
      lazyLoading: z.boolean().default(false),
      memoization: z.boolean().default(false),
      bundleSize: z.number().optional(),
      renderingCost: z.enum(['low', 'medium', 'high']).default('low'),
    })
    .optional(),
  testing: z
    .object({
      unitTests: z.boolean().default(false),
      integrationTests: z.boolean().default(false),
      accessibilityTests: z.boolean().default(false),
      visualTests: z.boolean().default(false),
      testCoverage: z.number().min(0).max(100).optional(),
    })
    .optional(),
  tags: z.array(z.string()).default([]),
  createdAt: z.date().default(() => new Date()),
  updatedAt: z.date().default(() => new Date()),
});

export type ComponentMetadata = z.infer<typeof ComponentMetadataSchema>;

// Component registration schema
export const ComponentRegistrationSchema = z.object({
  id: z.string().min(1),
  component: z.function(),
  metadata: ComponentMetadataSchema,
});

export type ComponentRegistration = z.infer<typeof ComponentRegistrationSchema>;

// Registry state schema
export const RegistryStateSchema = z.object({
  components: z.map(z.string(), ComponentRegistrationSchema),
  categories: z.map(z.string(), z.array(z.string())),
  portals: z.map(z.string(), z.array(z.string())),
  dependencies: z.map(z.string(), z.array(z.string())),
});

export type RegistryState = z.infer<typeof RegistryStateSchema>;

// Search and filter types
export interface ComponentSearchFilters {
  category?: string;
  portal?: string;
  tags?: string[];
  hasAccessibility?: boolean;
  hasSecurity?: boolean;
  minCoverage?: number;
  query?: string;
}

export interface ComponentSearchResult {
  id: string;
  metadata: ComponentMetadata;
  score: number;
}

// Validation result types
export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
}

export interface ValidationError {
  field: string;
  message: string;
  code: string;
}

export interface ValidationWarning {
  field: string;
  message: string;
  severity: 'low' | 'medium' | 'high';
}

// Component lifecycle events
export enum ComponentLifecycleEvent {
  REGISTERED = 'registered',
  UPDATED = 'updated',
  DEPRECATED = 'deprecated',
  REMOVED = 'removed',
  ACCESSED = 'accessed',
  ERROR = 'error',
}

export interface ComponentLifecycleEventData {
  componentId: string;
  event: ComponentLifecycleEvent;
  timestamp: Date;
  metadata?: Partial<ComponentMetadata>;
  error?: Error;
}
