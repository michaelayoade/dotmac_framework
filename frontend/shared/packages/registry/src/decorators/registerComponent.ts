import React from 'react';
import { type ComponentMetadata } from '../types';
import { componentRegistry } from '../registry/ComponentRegistry';

/**
 * Decorator to automatically register components with the registry
 */
export function registerComponent(metadata: ComponentMetadata) {
  return function <T extends React.ComponentType<any>>(Component: T): T {
    // Generate component ID from name and portal
    const componentId = `${metadata.portal}.${metadata.name}`;

    // Register component
    const result = componentRegistry.register(componentId, Component, metadata);

    if (!result.isValid) {
      console.error(`Failed to register component ${componentId}:`, result.errors);
    }

    // Add metadata to component for debugging
    (Component as any).__componentMetadata = metadata;
    (Component as any).__componentId = componentId;

    return Component;
  };
}

/**
 * HOC to automatically register components
 */
export function withComponentRegistration<P extends object>(
  Component: React.ComponentType<P>,
  metadata: ComponentMetadata
): React.ComponentType<P> {
  const componentId = `${metadata.portal}.${metadata.name}`;

  const WrappedComponent = React.forwardRef<any, P>((props, ref) => {
    const { ...componentProps } = props as any;
    return React.createElement(Component, { ...componentProps, ref });
  });

  WrappedComponent.displayName = `WithRegistration(${Component.displayName || Component.name})`;

  // Register the component
  const result = componentRegistry.register(componentId, WrappedComponent, metadata);

  if (!result.isValid) {
    console.error(`Failed to register component ${componentId}:`, result.errors);
  }

  // Add metadata for debugging
  (WrappedComponent as any).__componentMetadata = metadata;
  (WrappedComponent as any).__componentId = componentId;

  return WrappedComponent as any;
}
