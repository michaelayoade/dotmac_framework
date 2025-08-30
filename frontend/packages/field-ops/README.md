# @dotmac/field-ops

Field operations and work order management system for ISP technician portals. This package provides comprehensive functionality for managing work orders, GPS tracking, and mobile workflows using DRY patterns from the existing codebase.

## Features

- **Work Order Management**: Complete CRUD operations with offline sync capabilities
- **GPS Tracking**: Real-time location tracking with geofencing for work sites
- **Mobile Workflows**: Step-by-step guided workflows with validation and evidence collection
- **Offline Support**: Works offline with automatic sync when connection is restored
- **Evidence Collection**: Photo capture, signatures, and documentation
- **Geofencing**: Automatic arrival/departure detection for work sites

## Installation

```bash
pnpm add @dotmac/field-ops
```

## Quick Start

### 1. Wrap your technician portal with the provider

```tsx
import { TechnicianPortalIntegration } from '@dotmac/field-ops';

function TechnicianApp() {
  return (
    <TechnicianPortalIntegration
      technicianId="tech_123"
      config={{
        enableGPS: true,
        enableOfflineMode: true,
        autoStartWorkflows: true
      }}
    >
      <YourTechnicianPortal />
    </TechnicianPortalIntegration>
  );
}
```

### 2. Use work order management

```tsx
import { useWorkOrders } from '@dotmac/field-ops';

function WorkOrdersList() {
  const {
    workOrders,
    loading,
    startWorkOrder,
    completeWorkOrder,
    updateStatus
  } = useWorkOrders({ autoSync: true });

  return (
    <div>
      {workOrders.map(wo => (
        <div key={wo.id}>
          <h3>{wo.title}</h3>
          <p>{wo.customer.name}</p>
          <button onClick={() => startWorkOrder(wo.id)}>
            Start Work
          </button>
        </div>
      ))}
    </div>
  );
}
```

### 3. Add GPS tracking

```tsx
import { useGPSTracking } from '@dotmac/field-ops';

function LocationTracker() {
  const {
    currentLocation,
    isTracking,
    startTracking,
    stopTracking,
    permissionStatus
  } = useGPSTracking({ autoStart: true });

  return (
    <div>
      {permissionStatus?.granted ? (
        <p>Location: {currentLocation?.latitude}, {currentLocation?.longitude}</p>
      ) : (
        <button onClick={() => requestPermissions()}>
          Enable Location
        </button>
      )}
    </div>
  );
}
```

### 4. Implement workflows

```tsx
import { useWorkflow, WorkflowStep } from '@dotmac/field-ops';

function WorkflowManager({ workOrderId }: { workOrderId: string }) {
  const {
    workflow,
    currentStep,
    startStep,
    completeStep,
    progress
  } = useWorkflow({
    workOrderId,
    templateId: 'installation_template',
    autoSave: true
  });

  if (!workflow) return <div>Loading workflow...</div>;

  return (
    <div>
      <div>Progress: {progress}%</div>
      {workflow.steps.map(step => (
        <WorkflowStep
          key={step.id}
          step={step}
          isActive={step.id === currentStep?.id}
          canStart={canGoToStep(step.id)}
          onStart={() => startStep(step.id)}
          onComplete={(data, evidence) => completeStep(step.id, data, evidence)}
          onSkip={() => skipStep(step.id)}
          onPause={() => pauseStep(step.id)}
        />
      ))}
    </div>
  );
}
```

## API Reference

### Hooks

#### `useWorkOrders(options)`

Manages work orders with offline sync capabilities.

**Options:**

- `autoSync: boolean` - Enable automatic sync with server
- `syncInterval: number` - Sync interval in milliseconds
- `technicianId?: string` - Filter work orders by technician

**Returns:**

- Work orders array and CRUD operations
- Sync status and error handling
- Filtering and search capabilities

#### `useGPSTracking(options)`

Provides GPS tracking and geofencing functionality.

**Options:**

- `settings: LocationTrackingSettings` - GPS configuration
- `autoStart: boolean` - Start tracking automatically
- `workOrderId?: string` - Associate tracking with work order

**Returns:**

- Current location and tracking status
- Geofence management
- Permission handling

#### `useWorkflow(options)`

Manages step-by-step workflows for work orders.

**Options:**

- `workOrderId: string` - Work order to attach workflow
- `templateId?: string` - Workflow template to use
- `autoSave: boolean` - Enable automatic saving

**Returns:**

- Workflow state and step management
- Progress tracking
- Validation and evidence collection

### Components

#### `<TechnicianPortalIntegration>`

Main integration component that provides field operations context.

#### `<WorkflowStep>`

Individual workflow step component with form validation and evidence collection.

#### `<FieldOpsProvider>`

Low-level provider for field operations configuration.

### Types

The package exports comprehensive TypeScript types for all data structures:

- `WorkOrder` - Complete work order definition
- `GPSLocation` - Location data with metadata
- `WorkflowInstance` - Workflow state and progress
- `GeoFence` - Geofencing configuration
- And many more...

## Architecture

This package follows DRY patterns from the existing codebase:

- **Database Layer**: Uses Dexie for offline storage with sync queues
- **API Client**: Integrates with `@dotmac/headless` for API calls
- **Authentication**: Uses existing auth patterns from `@dotmac/auth`
- **Error Handling**: Follows standard error boundary patterns
- **State Management**: Uses React hooks with proper cleanup

## Offline Support

The package provides robust offline functionality:

- **Work Order Sync**: Queues changes when offline, syncs when online
- **Photo Storage**: Stores photos locally until they can be uploaded
- **GPS History**: Maintains location history for later upload
- **Conflict Resolution**: Handles sync conflicts intelligently

## Performance Considerations

- **Lazy Loading**: Components and workflows load on demand
- **Memory Management**: Automatic cleanup of old location data
- **Batch Operations**: Efficient database operations
- **Background Sync**: Non-blocking sync operations

## Security

- **Data Sanitization**: All user inputs are sanitized
- **Secure Storage**: Sensitive data is encrypted in local storage
- **Permission Validation**: GPS and camera permissions handled securely
- **API Security**: Integrates with existing authentication systems

## Contributing

Follow the existing patterns in the codebase:

1. Use DRY patterns from `@dotmac/headless`
2. Follow TypeScript strict mode
3. Add comprehensive error handling
4. Include proper cleanup in useEffect hooks
5. Maintain backward compatibility

## License

MIT
