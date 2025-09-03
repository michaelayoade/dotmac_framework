# @dotmac/journey-orchestration

Complete customer journey orchestration and cross-package integration for the DotMac ISP framework. This package provides centralized management of customer journeys from prospect to active service, with automated handoffs, conversion analytics, and real-time tracking.

## Features

### 🚀 Journey Orchestration

- **Complete Lifecycle Management**: Track customers from prospect → lead → qualified → customer → active service
- **Cross-Package Coordination**: Seamless integration between CRM, billing, field operations, and support
- **Automated Progression**: Smart step advancement based on conditions and triggers
- **Real-time State Management**: Live updates using RxJS observables

### 📊 Conversion Analytics

- **Funnel Analysis**: Detailed conversion funnels with drop-off analysis
- **Attribution Tracking**: Multi-touch attribution across channels and campaigns
- **Cohort Analysis**: Track customer groups over time
- **ROI Calculations**: Revenue tracking and lifetime value analysis

### 🔄 Automated Handoffs

- **Package Integration**: Automatic handoffs between @dotmac packages
- **Approval Workflows**: Manual approval gates for critical transitions
- **Failure Recovery**: Retry mechanisms and error handling
- **Bulk Operations**: Process multiple handoffs efficiently

### 📡 Event-Driven Architecture

- **Real-time Events**: Centralized event bus for package communication
- **Custom Triggers**: Create journey triggers based on business events
- **Integration Points**: Pre-built integrations for ISP workflows
- **Touchpoint Tracking**: Capture all customer interactions

## Installation

```bash
pnpm add @dotmac/journey-orchestration
```

## Dependencies

This package integrates with other DotMac packages:

- `@dotmac/crm` - Customer relationship management
- `@dotmac/business-logic` - ISP service operations
- `@dotmac/field-ops` - Field operations and work orders
- `@dotmac/support-system` - Customer support
- `@dotmac/billing-system` - Billing and payments
- `@dotmac/auth` - Authentication and authorization

## Quick Start

### Basic Journey Management

```tsx
import { useJourneyOrchestration, ISP_JOURNEY_TEMPLATES } from '@dotmac/journey-orchestration';

function JourneyManager() {
  const { journeys, activeJourney, loading, startJourney, advanceStep, updateContext } =
    useJourneyOrchestration();

  const handleStartCustomerAcquisition = async (leadId: string) => {
    const journey = await startJourney(ISP_JOURNEY_TEMPLATES.CUSTOMER_ACQUISITION.id, {
      leadId,
      priority: 'high',
      source: 'website',
    });
    console.log('Journey started:', journey.id);
  };

  const handleAdvanceStep = async (journeyId: string) => {
    await advanceStep(journeyId);
  };

  return (
    <div>
      <h2>Active Journeys: {journeys.filter((j) => j.status === 'active').length}</h2>
      {journeys.map((journey) => (
        <div key={journey.id}>
          <h3>{journey.name}</h3>
          <p>
            Stage: {journey.stage} | Progress: {journey.progress}%
          </p>
          <button onClick={() => handleAdvanceStep(journey.id)}>Advance Step</button>
        </div>
      ))}
    </div>
  );
}
```

### Conversion Analytics

```tsx
import { useConversionAnalytics } from '@dotmac/journey-orchestration';

function AnalyticsDashboard() {
  const { metrics, funnels, loading, getFunnelData, getAttributionData, exportAnalytics } =
    useConversionAnalytics();

  const handleExport = async () => {
    const csvData = await exportAnalytics('csv');
    // Download CSV file
    const blob = new Blob([csvData], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'journey-analytics.csv';
    a.click();
  };

  if (loading) return <div>Loading analytics...</div>;

  return (
    <div>
      <h2>Journey Analytics</h2>

      {/* Key Metrics */}
      {metrics && (
        <div>
          <p>Total Journeys: {metrics.totalJourneys}</p>
          <p>Active Journeys: {metrics.activeJourneys}</p>
          <p>Completed: {metrics.completedJourneys}</p>
          <p>Average Duration: {metrics.averageJourneyDuration} days</p>
        </div>
      )}

      {/* Conversion Funnels */}
      {funnels.map((funnel) => (
        <div key={funnel.name}>
          <h3>{funnel.name}</h3>
          <p>Overall Conversion: {funnel.overallConversionRate.toFixed(1)}%</p>
          {funnel.stages.map((stage) => (
            <div key={stage.stage}>
              <span>
                {stage.stage}: {stage.count} ({stage.conversionRate.toFixed(1)}%)
              </span>
            </div>
          ))}
        </div>
      ))}

      <button onClick={handleExport}>Export Analytics</button>
    </div>
  );
}
```

### Handoff Management

```tsx
import { useHandoffSystem } from '@dotmac/journey-orchestration';

function HandoffManager() {
  const {
    activeHandoffs,
    pendingApprovals,
    loading,
    createHandoff,
    approveHandoff,
    rejectHandoff,
  } = useHandoffSystem();

  const handleCreateHandoff = async () => {
    await createHandoff({
      journeyId: 'journey_123',
      fromPackage: 'crm',
      toPackage: 'field-ops',
      stepId: 'installation_schedule',
      handoffType: 'automatic',
      data: {
        customerId: 'cust_456',
        serviceType: 'fiber',
        priority: 'standard',
      },
      requiredData: ['customerId', 'serviceType'],
    });
  };

  return (
    <div>
      <h2>Handoff Management</h2>

      {/* Active Handoffs */}
      <h3>Active Handoffs ({activeHandoffs.length})</h3>
      {activeHandoffs.map((handoff) => (
        <div key={handoff.id}>
          <p>
            {handoff.fromPackage} → {handoff.toPackage}
          </p>
          <p>Status: {handoff.status}</p>
        </div>
      ))}

      {/* Pending Approvals */}
      <h3>Pending Approvals ({pendingApprovals.length})</h3>
      {pendingApprovals.map((handoff) => (
        <div key={handoff.id}>
          <p>
            {handoff.fromPackage} → {handoff.toPackage}
          </p>
          <button onClick={() => approveHandoff(handoff.id, 'Approved by admin')}>Approve</button>
          <button onClick={() => rejectHandoff(handoff.id, 'Insufficient data')}>Reject</button>
        </div>
      ))}
    </div>
  );
}
```

## Built-in Journey Templates

### Customer Acquisition Journey

Complete lead-to-customer conversion with service activation:

```tsx
import { ISP_JOURNEY_TEMPLATES } from '@dotmac/journey-orchestration';

// Start customer acquisition journey
const journey = await startJourney(ISP_JOURNEY_TEMPLATES.CUSTOMER_ACQUISITION.id, {
  leadId: 'lead_123',
  leadScore: 85,
  interestedServices: ['fiber', 'voip'],
});
```

**Steps:**

1. Lead Qualification
2. Customer Conversion
3. Service Selection
4. Service Activation
5. Installation Scheduling

### Support Resolution Journey

Automated support ticket resolution workflow:

```tsx
// Triggered automatically when support ticket is created
const supportJourney = await startJourney(ISP_JOURNEY_TEMPLATES.SUPPORT_RESOLUTION.id, {
  ticketId: 'tick_456',
  customerId: 'cust_789',
  priority: 'high',
  issue: 'Internet connectivity',
});
```

**Steps:**

1. Ticket Triage
2. Agent Assignment
3. Issue Diagnosis
4. Resolution Action
5. Customer Verification

### Customer Onboarding Journey

New customer setup and service activation:

```tsx
// Triggered when service is activated
const onboardingJourney = await startJourney(ISP_JOURNEY_TEMPLATES.CUSTOMER_ONBOARDING.id, {
  customerId: 'cust_101',
  serviceType: 'fiber',
  installationDate: '2024-01-15',
});
```

**Steps:**

1. Welcome Communication
2. Billing Setup
3. Equipment Provisioning
4. Service Testing
5. Onboarding Complete

## Advanced Features

### Custom Journey Templates

```tsx
import { JourneyUtils } from '@dotmac/journey-orchestration';

const customTemplate = JourneyUtils.createTemplate({
  id: 'custom_upsell',
  name: 'Service Upsell Journey',
  description: 'Upsell existing customers to higher service tiers',
  category: 'retention',
  steps: [
    {
      id: 'analyze_usage',
      name: 'Analyze Usage Patterns',
      stage: 'active_service',
      order: 1,
      type: 'automated',
      estimatedDuration: 30,
    },
    {
      id: 'generate_recommendation',
      name: 'Generate Upsell Recommendation',
      stage: 'active_service',
      order: 2,
      type: 'automated',
      estimatedDuration: 15,
    },
    {
      id: 'contact_customer',
      name: 'Contact Customer',
      stage: 'active_service',
      order: 3,
      type: 'manual',
      estimatedDuration: 45,
    },
  ],
  triggers: [
    {
      id: 'usage_threshold_trigger',
      name: 'High Usage Detected',
      type: 'conditional',
      conditions: [{ field: 'monthlyUsage', operator: 'greater_than', value: 80 }],
    },
  ],
});

// Validate template
const validation = JourneyUtils.validateTemplate(customTemplate);
if (!validation.isValid) {
  console.error('Template validation errors:', validation.errors);
}
```

### Event Bus Integration

```tsx
import { JourneyEventBus } from '@dotmac/journey-orchestration';

const eventBus = JourneyEventBus.getInstance('tenant_123');

// Listen for conversion events
const unsubscribe = eventBus.onEventType('crm:lead_converted', (event) => {
  console.log('Lead converted:', event.data);

  // Automatically start onboarding journey
  startJourney('customer_onboarding', {
    customerId: event.customerId,
    leadId: event.leadId,
    conversionSource: event.source,
  });
});

// Emit custom events
await eventBus.emitJourneyEvent({
  type: 'service:usage_spike',
  source: 'monitoring-system',
  customerId: 'cust_123',
  data: {
    usagePercentage: 95,
    planLimit: 1000,
    currentUsage: 950,
  },
});
```

### Real-time Journey Tracking

```tsx
function JourneyTracker({ journeyId }: { journeyId: string }) {
  const { subscribeToJourney } = useJourneyOrchestration();
  const [journey, setJourney] = useState<CustomerJourney | null>(null);

  useEffect(() => {
    const unsubscribe = subscribeToJourney(journeyId, (updatedJourney) => {
      setJourney(updatedJourney);

      // Show notification for important updates
      if (updatedJourney.status === 'completed') {
        showNotification('Journey completed successfully!');
      }
    });

    return unsubscribe;
  }, [journeyId, subscribeToJourney]);

  return (
    <div>
      {journey && (
        <>
          <h3>{journey.name}</h3>
          <ProgressBar progress={journey.progress} />
          <p>Current Step: {journey.currentStep}</p>
          <p>Last Activity: {new Date(journey.lastActivity).toLocaleString()}</p>
        </>
      )}
    </div>
  );
}
```

## Integration Examples

### CRM Integration

```tsx
// Automatic journey triggers based on CRM events
eventBus.onEventType('crm:lead_qualified', async (event) => {
  await startJourney('customer_acquisition', {
    leadId: event.leadId,
    qualificationScore: event.data.score,
    interestedServices: event.data.services,
  });
});

eventBus.onEventType('crm:customer_created', async (event) => {
  await startJourney('customer_onboarding', {
    customerId: event.customerId,
    customerType: event.data.type,
    serviceRequests: event.data.services,
  });
});
```

### Business Logic Integration

```tsx
// Service activation triggers
eventBus.onEventType('service:activated', async (event) => {
  // Complete acquisition journey step
  if (event.journeyId) {
    await advanceStep(event.journeyId, 'service_activation_complete');
  }

  // Start installation scheduling
  await createHandoff({
    journeyId: event.journeyId || '',
    fromPackage: 'business-logic',
    toPackage: 'field-ops',
    stepId: 'schedule_installation',
    handoffType: 'automatic',
    data: {
      customerId: event.customerId,
      serviceId: event.data.serviceId,
      installationType: event.data.installationType,
    },
  });
});
```

### Support System Integration

```tsx
// Support ticket creation triggers
eventBus.onEventType('support:ticket_created', async (event) => {
  await startJourney('support_resolution', {
    ticketId: event.data.ticketId,
    customerId: event.customerId,
    priority: event.data.priority,
    category: event.data.category,
    assignedAgent: event.data.assignedTo,
  });
});
```

## Configuration

```tsx
import type { JourneyOrchestrationConfig } from '@dotmac/journey-orchestration';

const config: JourneyOrchestrationConfig = {
  apiBaseUrl: '/api/journey-orchestration',
  websocketUrl: 'ws://localhost:3001/journey-events',
  enableRealtime: true,
  enableAnalytics: true,
  enableHandoffs: true,

  // Performance settings
  maxConcurrentJourneys: 500,
  handoffTimeout: 300000, // 5 minutes
  retryAttempts: 3,

  // Package integrations
  packageIntegrations: {
    crm: { enabled: true },
    'business-logic': { enabled: true },
    'field-ops': { enabled: true },
    'support-system': { enabled: true },
    'billing-system': { enabled: true },
  },

  // Analytics settings
  analyticsRetentionDays: 365,
  enableTouchpointTracking: true,
  enableConversionTracking: true,
};
```

## API Reference

### Core Classes

#### JourneyOrchestrator

Main orchestration engine for managing customer journeys.

#### JourneyEventBus

Centralized event system for cross-package communication.

#### ConversionAnalytics

Analytics engine for funnel analysis and conversion tracking.

#### HandoffSystem

Automated handoff management between packages.

### React Hooks

#### useJourneyOrchestration()

Complete journey management with real-time updates.

#### useConversionAnalytics()

Analytics and reporting capabilities.

#### useHandoffSystem()

Handoff management and approval workflows.

## License

MIT - See LICENSE file for details.

## Contributing

Please refer to the main DotMac Framework contributing guidelines.
