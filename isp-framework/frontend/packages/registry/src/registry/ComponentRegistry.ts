import {
  type ComponentMetadata,
  type ComponentRegistration,
  type ComponentSearchFilters,
  type ComponentSearchResult,
  type ValidationResult,
  ComponentLifecycleEvent,
  type ComponentLifecycleEventData,
  ComponentMetadataSchema,
} from '../types';

export class ComponentRegistry {
  private components = new Map<string, ComponentRegistration>();
  private categories = new Map<string, string[]>();
  private portals = new Map<string, string[]>();
  private dependencies = new Map<string, string[]>();
  private eventListeners = new Map<
    ComponentLifecycleEvent,
    Array<(data: ComponentLifecycleEventData) => void>
  >();

  constructor() {
    // Initialize category and portal maps
    this.categories.set('atomic', []);
    this.categories.set('molecular', []);
    this.categories.set('organism', []);
    this.categories.set('template', []);
    this.categories.set('page', []);
    this.categories.set('layout', []);
    this.categories.set('form', []);
    this.categories.set('data-display', []);
    this.categories.set('feedback', []);
    this.categories.set('navigation', []);
    this.categories.set('utility', []);

    this.portals.set('admin', []);
    this.portals.set('customer', []);
    this.portals.set('reseller', []);
    this.portals.set('shared', []);
    this.portals.set('headless', []);
  }

  /**
   * Register a new component
   */
  register(
    id: string,
    component: React.ComponentType<any>,
    metadata: ComponentMetadata
  ): ValidationResult {
    try {
      // Validate metadata
      const validationResult = this.validateMetadata(metadata);
      if (!validationResult.isValid) {
        this.emitEvent({
          componentId: id,
          event: ComponentLifecycleEvent.ERROR,
          timestamp: new Date(),
          error: new Error(
            `Validation failed: ${validationResult.errors.map((e) => e.message).join(', ')}`
          ),
        });
        return validationResult;
      }

      // Check for existing component
      if (this.components.has(id)) {
        return this.update(id, component, metadata);
      }

      // Create registration
      const registration: ComponentRegistration = {
        id,
        component: component as any,
        metadata: {
          ...metadata,
          createdAt: new Date(),
          updatedAt: new Date(),
        },
      };

      // Store component
      this.components.set(id, registration);

      // Update indexes
      this.updateIndexes(id, metadata);

      // Emit registration event
      this.emitEvent({
        componentId: id,
        event: ComponentLifecycleEvent.REGISTERED,
        timestamp: new Date(),
        metadata,
      });

      return { isValid: true, errors: [], warnings: [] };
    } catch (error) {
      this.emitEvent({
        componentId: id,
        event: ComponentLifecycleEvent.ERROR,
        timestamp: new Date(),
        error: error as Error,
      });

      return {
        isValid: false,
        errors: [
          {
            field: 'registration',
            message: error instanceof Error ? error.message : 'Unknown error',
            code: 'REGISTRATION_FAILED',
          },
        ],
        warnings: [],
      };
    }
  }

  /**
   * Update an existing component
   */
  update(
    id: string,
    component: React.ComponentType<any>,
    metadata: ComponentMetadata
  ): ValidationResult {
    const existing = this.components.get(id);
    if (!existing) {
      return {
        isValid: false,
        errors: [
          {
            field: 'id',
            message: `Component with id '${id}' not found`,
            code: 'COMPONENT_NOT_FOUND',
          },
        ],
        warnings: [],
      };
    }

    // Validate metadata
    const validationResult = this.validateMetadata(metadata);
    if (!validationResult.isValid) {
      return validationResult;
    }

    // Update registration
    const updated: ComponentRegistration = {
      id,
      component: component as any,
      metadata: {
        ...metadata,
        createdAt: existing.metadata.createdAt,
        updatedAt: new Date(),
      },
    };

    this.components.set(id, updated);

    // Update indexes
    this.removeFromIndexes(id, existing.metadata);
    this.updateIndexes(id, metadata);

    // Emit update event
    this.emitEvent({
      componentId: id,
      event: ComponentLifecycleEvent.UPDATED,
      timestamp: new Date(),
      metadata,
    });

    return { isValid: true, errors: [], warnings: [] };
  }

  /**
   * Get a component by ID
   */
  get(id: string): ComponentRegistration | undefined {
    const component = this.components.get(id);
    if (component) {
      // Emit access event
      this.emitEvent({
        componentId: id,
        event: ComponentLifecycleEvent.ACCESSED,
        timestamp: new Date(),
      });
    }
    return component;
  }

  /**
   * Get component metadata only
   */
  getMetadata(id: string): ComponentMetadata | undefined {
    const component = this.components.get(id);
    return component?.metadata;
  }

  /**
   * Search components
   */
  search(filters: ComponentSearchFilters = {}): ComponentSearchResult[] {
    const results: ComponentSearchResult[] = [];

    for (const [id, registration] of this.components) {
      let score = 0;
      let matches = true;

      // Category filter
      if (filters.category && registration.metadata.category !== filters.category) {
        matches = false;
      }

      // Portal filter
      if (filters.portal && registration.metadata.portal !== filters.portal) {
        matches = false;
      }

      // Tags filter
      if (filters.tags && filters.tags.length > 0) {
        const hasAllTags = filters.tags.every(
          (tag) => registration.metadata.tags?.includes(tag) ?? false
        );
        if (!hasAllTags) {
          matches = false;
        } else {
          score += filters.tags.length;
        }
      }

      // Accessibility filter
      if (filters.hasAccessibility && !registration.metadata.accessibility?.ariaSupport) {
        matches = false;
      }

      // Security filter
      if (filters.hasSecurity && !registration.metadata.security?.xssProtection) {
        matches = false;
      }

      // Coverage filter
      if (
        filters.minCoverage &&
        (registration.metadata.testing?.testCoverage ?? 0) < filters.minCoverage
      ) {
        matches = false;
      }

      // Text query filter
      if (filters.query) {
        const query = filters.query.toLowerCase();
        const searchableText = [
          registration.metadata.name,
          registration.metadata.description || '',
          ...(registration.metadata.tags || []),
        ]
          .join(' ')
          .toLowerCase();

        if (searchableText.includes(query)) {
          score += 1;
        } else {
          matches = false;
        }
      }

      if (matches) {
        results.push({
          id,
          metadata: registration.metadata,
          score,
        });
      }
    }

    // Sort by score (descending) and then by name
    return results.sort((a, b) => {
      if (a.score !== b.score) {
        return b.score - a.score;
      }
      return a.metadata.name.localeCompare(b.metadata.name);
    });
  }

  /**
   * Get all components in a category
   */
  getByCategory(category: string): ComponentRegistration[] {
    const componentIds = this.categories.get(category) || [];
    return componentIds
      .map((id) => this.components.get(id))
      .filter((comp): comp is ComponentRegistration => comp !== undefined);
  }

  /**
   * Get all components for a portal
   */
  getByPortal(portal: string): ComponentRegistration[] {
    const componentIds = this.portals.get(portal) || [];
    return componentIds
      .map((id) => this.components.get(id))
      .filter((comp): comp is ComponentRegistration => comp !== undefined);
  }

  /**
   * Get component dependencies
   */
  getDependencies(id: string): string[] {
    return this.dependencies.get(id) || [];
  }

  /**
   * Get all categories
   */
  getCategories(): string[] {
    return Array.from(this.categories.keys());
  }

  /**
   * Get all portals
   */
  getPortals(): string[] {
    return Array.from(this.portals.keys());
  }

  /**
   * Remove a component
   */
  remove(id: string): boolean {
    const component = this.components.get(id);
    if (!component) {
      return false;
    }

    // Remove from main storage
    this.components.delete(id);

    // Remove from indexes
    this.removeFromIndexes(id, component.metadata);

    // Emit removal event
    this.emitEvent({
      componentId: id,
      event: ComponentLifecycleEvent.REMOVED,
      timestamp: new Date(),
      metadata: component.metadata,
    });

    return true;
  }

  /**
   * Get registry statistics
   */
  getStats() {
    const totalComponents = this.components.size;
    const categoryStats = new Map<string, number>();
    const portalStats = new Map<string, number>();

    for (const [, registration] of this.components) {
      const category = registration.metadata.category;
      const portal = registration.metadata.portal;

      categoryStats.set(category, (categoryStats.get(category) || 0) + 1);
      portalStats.set(portal, (portalStats.get(portal) || 0) + 1);
    }

    return {
      totalComponents,
      categories: Object.fromEntries(categoryStats),
      portals: Object.fromEntries(portalStats),
    };
  }

  /**
   * Add event listener
   */
  addEventListener(
    event: ComponentLifecycleEvent,
    listener: (data: ComponentLifecycleEventData) => void
  ): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, []);
    }
    this.eventListeners.get(event)!.push(listener);
  }

  /**
   * Remove event listener
   */
  removeEventListener(
    event: ComponentLifecycleEvent,
    listener: (data: ComponentLifecycleEventData) => void
  ): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      const index = listeners.indexOf(listener);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  private validateMetadata(metadata: ComponentMetadata): ValidationResult {
    try {
      ComponentMetadataSchema.parse(metadata);
      return { isValid: true, errors: [], warnings: [] };
    } catch (error: any) {
      const errors = error.errors?.map((err: any) => ({
        field: err.path?.join('.') || 'unknown',
        message: err.message,
        code: err.code || 'VALIDATION_ERROR',
      })) || [
        {
          field: 'metadata',
          message: 'Invalid metadata format',
          code: 'VALIDATION_ERROR',
        },
      ];

      return { isValid: false, errors, warnings: [] };
    }
  }

  private updateIndexes(id: string, metadata: ComponentMetadata): void {
    // Update category index
    const categoryComponents = this.categories.get(metadata.category) || [];
    if (!categoryComponents.includes(id)) {
      categoryComponents.push(id);
      this.categories.set(metadata.category, categoryComponents);
    }

    // Update portal index
    const portalComponents = this.portals.get(metadata.portal) || [];
    if (!portalComponents.includes(id)) {
      portalComponents.push(id);
      this.portals.set(metadata.portal, portalComponents);
    }

    // Update dependencies index
    if (metadata.dependencies && metadata.dependencies.length > 0) {
      this.dependencies.set(id, metadata.dependencies);
    }
  }

  private removeFromIndexes(id: string, metadata: ComponentMetadata): void {
    // Remove from category index
    const categoryComponents = this.categories.get(metadata.category) || [];
    const categoryIndex = categoryComponents.indexOf(id);
    if (categoryIndex > -1) {
      categoryComponents.splice(categoryIndex, 1);
      this.categories.set(metadata.category, categoryComponents);
    }

    // Remove from portal index
    const portalComponents = this.portals.get(metadata.portal) || [];
    const portalIndex = portalComponents.indexOf(id);
    if (portalIndex > -1) {
      portalComponents.splice(portalIndex, 1);
      this.portals.set(metadata.portal, portalComponents);
    }

    // Remove from dependencies index
    this.dependencies.delete(id);
  }

  private emitEvent(data: ComponentLifecycleEventData): void {
    const listeners = this.eventListeners.get(data.event);
    if (listeners) {
      listeners.forEach((listener) => {
        try {
          listener(data);
        } catch (error) {
          console.error('Error in component lifecycle event listener:', error);
        }
      });
    }
  }
}

// Global registry instance
export const componentRegistry = new ComponentRegistry();
