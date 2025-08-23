// Types
export * from './types';

// Registry
export { ComponentRegistry, componentRegistry } from './registry/ComponentRegistry';

// Decorators
export * from './decorators/registerComponent';

// Hooks
export * from './hooks/useRegistry';

// Default export for convenience
export { componentRegistry as default } from './registry/ComponentRegistry';
