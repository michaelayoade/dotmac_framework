import React from 'react';
import {
  type ComponentSearchFilters,
  type ComponentSearchResult,
  type ComponentRegistration,
  ComponentLifecycleEvent,
  type ComponentLifecycleEventData,
} from '../types';
import { componentRegistry } from '../registry/ComponentRegistry';

/**
 * Hook to search and filter components
 */
export function useComponentSearch(filters: ComponentSearchFilters = {}) {
  const [results, setResults] = React.useState<ComponentSearchResult[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);

  React.useEffect(() => {
    setIsLoading(true);
    try {
      const searchResults = componentRegistry.search(filters);
      setResults(searchResults);
    } finally {
      setIsLoading(false);
    }
  }, [JSON.stringify(filters)]);

  return { results, isLoading };
}

/**
 * Hook to get a specific component
 */
export function useComponent(id: string) {
  const [component, setComponent] = React.useState<ComponentRegistration | undefined>();
  const [isLoading, setIsLoading] = React.useState(true);

  React.useEffect(() => {
    setIsLoading(true);
    try {
      const comp = componentRegistry.get(id);
      setComponent(comp);
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  return { component, isLoading };
}

/**
 * Hook to get components by category
 */
export function useComponentsByCategory(category: string) {
  const [components, setComponents] = React.useState<ComponentRegistration[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);

  React.useEffect(() => {
    setIsLoading(true);
    try {
      const comps = componentRegistry.getByCategory(category);
      setComponents(comps);
    } finally {
      setIsLoading(false);
    }
  }, [category]);

  return { components, isLoading };
}

/**
 * Hook to get components by portal
 */
export function useComponentsByPortal(portal: string) {
  const [components, setComponents] = React.useState<ComponentRegistration[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);

  React.useEffect(() => {
    setIsLoading(true);
    try {
      const comps = componentRegistry.getByPortal(portal);
      setComponents(comps);
    } finally {
      setIsLoading(false);
    }
  }, [portal]);

  return { components, isLoading };
}

/**
 * Hook to get registry statistics
 */
export function useRegistryStats() {
  const [stats, setStats] = React.useState(() => componentRegistry.getStats());

  React.useEffect(() => {
    const updateStats = () => {
      setStats(componentRegistry.getStats());
    };

    // Listen for component lifecycle events to update stats
    const events: ComponentLifecycleEvent[] = [
      ComponentLifecycleEvent.REGISTERED,
      ComponentLifecycleEvent.UPDATED,
      ComponentLifecycleEvent.REMOVED,
    ];

    events.forEach((event) => {
      componentRegistry.addEventListener(event, updateStats);
    });

    return () => {
      events.forEach((event) => {
        componentRegistry.removeEventListener(event, updateStats);
      });
    };
  }, []);

  return stats;
}

/**
 * Hook to listen to component lifecycle events
 */
export function useComponentLifecycle(
  event: ComponentLifecycleEvent,
  callback: (data: ComponentLifecycleEventData) => void
) {
  React.useEffect(() => {
    componentRegistry.addEventListener(event, callback);

    return () => {
      componentRegistry.removeEventListener(event, callback);
    };
  }, [event, callback]);
}

/**
 * Hook for component dependencies
 */
export function useComponentDependencies(id: string) {
  const [dependencies, setDependencies] = React.useState<string[]>([]);
  const [dependencyComponents, setDependencyComponents] = React.useState<ComponentRegistration[]>(
    []
  );

  React.useEffect(() => {
    const deps = componentRegistry.getDependencies(id);
    setDependencies(deps);

    const depComponents = deps
      .map((depId) => componentRegistry.get(depId))
      .filter((comp): comp is ComponentRegistration => comp !== undefined);
    setDependencyComponents(depComponents);
  }, [id]);

  return { dependencies, dependencyComponents };
}
