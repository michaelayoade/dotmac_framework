/**
 * @dotmac/field-ops
 *
 * Field operations and work order management system with DRY patterns
 * Provides comprehensive technician portal functionality including:
 * - Work order management with offline sync
 * - GPS tracking and geofencing
 * - Mobile workflows with validation
 * - Photo capture and evidence collection
 */

// Main Provider
export * from './components';

// Work Order Management
export * from './work-orders';

// GPS and Location Services
export * from './gps';

// Mobile Workflows
export * from './workflows';

// Core Types
export * from './types';

// Integration Components
export * from './integration';

// Version
export const VERSION = '0.1.0';
