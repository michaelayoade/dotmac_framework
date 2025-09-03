# @dotmac/maps

Universal GIS and mapping system for ISP portals. Provides unified mapping functionality, GIS business logic engines, and multi-provider support for all portal applications.

## Features

### 🗺️ **Universal Map Providers**

- **Leaflet** - Production-ready open-source mapping
- **Google Maps** - Enterprise mapping with APIs (coming soon)
- **Mapbox** - Custom styled mapping (coming soon)
- **Mock Provider** - Development and testing

### 🧠 **GIS Business Logic Engines**

- **Service Coverage Engine** - Coverage analysis, gap identification, optimization
- **Territory Engine** - Market analysis, competitor overlap, expansion planning
- **Route Optimization Engine** - Field operations, maintenance scheduling, travel optimization

### 🎯 **Portal-Aware**

- Different configurations for each portal type
- Permission-based feature access
- Portal-specific styling and themes

## Quick Start

```typescript
import { UniversalMappingSystem } from '@dotmac/maps';

// Initialize the mapping system
const mappingSystem = UniversalMappingSystem.getInstance();

// Create a map for a specific portal
const container = document.getElementById('map');
const mapProvider = await mappingSystem.createMapForPortal(
  'admin', // Portal type
  container,
  {
    center: { lat: 37.7749, lng: -122.4194 },
    zoom: 12,
  }
);

// Add markers
mapProvider.addMarker({
  id: 'customer-1',
  position: { lat: 37.7849, lng: -122.4094 },
  type: 'customer',
  status: 'active',
  title: 'Customer Location',
});

// Create business logic engines
const engines = mappingSystem.createEngines({
  portalType: 'admin',
  userId: 'user-123',
  permissions: ['coverage_read', 'territory_read'],
});

// Analyze service coverage
const coverage = await engines.serviceCoverage.calculateCoverage(serviceArea, [
  'fiber',
  'wireless',
]);
```

## Map Provider Usage

### Creating Providers

```typescript
import { MapProviderFactory, LeafletProvider } from '@dotmac/maps';

// Get factory instance
const factory = MapProviderFactory.getInstance({
  defaultProvider: 'leaflet',
  fallbackProvider: 'mock',
  enableFallback: true,
});

// Create specific provider
const provider = await factory.createProvider(
  { type: 'leaflet' },
  { center: { lat: 40.7128, lng: -74.006 }, zoom: 10 }
);

await provider.initialize(container);
```

### Adding Map Features

```typescript
// Add service areas
provider.addServiceArea({
  id: 'area-1',
  name: 'Downtown Fiber',
  type: 'fiber',
  polygon: {
    coordinates: [
      { lat: 40.7128, lng: -74.006 },
      { lat: 40.7148, lng: -74.004 },
      { lat: 40.7108, lng: -74.002 },
      { lat: 40.7088, lng: -74.008 },
    ],
  },
  serviceLevel: 'full',
  maxSpeed: 1000,
  coverage: 95,
});

// Add network nodes
provider.addNetworkNode({
  id: 'node-1',
  name: 'Core Router NYC-1',
  type: 'core',
  position: { lat: 40.7128, lng: -74.006 },
  status: 'online',
  capacity: '100Gbps',
  utilization: 67,
});

// Add routes
provider.addRoute({
  id: 'route-1',
  name: 'Technician Route A',
  waypoints: [
    { lat: 40.7128, lng: -74.006 },
    { lat: 40.7148, lng: -74.004 },
    { lat: 40.7168, lng: -74.002 },
  ],
  type: 'installation',
  status: 'in_progress',
  priority: 'high',
});
```

## GIS Business Logic

### Service Coverage Analysis

```typescript
import { ServiceCoverageEngine } from '@dotmac/maps';

const coverageEngine = new ServiceCoverageEngine(portalContext);

// Analyze coverage in an area
const result = await coverageEngine.calculateCoverage(polygon, ['fiber', 'wireless'], {
  maxBuildoutCost: 500000,
  minExpectedCustomers: 100,
});

console.log(`Coverage: ${result.coveragePercentage}%`);
console.log(`Gaps found: ${result.gaps.length}`);
console.log(`Recommendations: ${result.recommendations.length}`);
```

### Territory Management

```typescript
import { TerritoryEngine } from '@dotmac/maps';

const territoryEngine = new TerritoryEngine(portalContext);

// Analyze market penetration
const penetration = await territoryEngine.calculateMarketPenetration(territory);

// Find competitor overlaps
const competition = await territoryEngine.findCompetitorOverlap([territory1, territory2]);

// Suggest expansion areas
const expansion = await territoryEngine.suggestTerritoryExpansion(territory, {
  maxDistance: 10, // km
  minPopulation: 5000,
  budgetConstraint: 1000000,
});
```

### Route Optimization

```typescript
import { RouteOptimizationEngine } from '@dotmac/maps';

const routeEngine = new RouteOptimizationEngine(portalContext);

// Optimize technician routes
const optimization = await routeEngine.optimizeRoutes({
  technicians: [
    {
      id: 'tech-1',
      name: 'John Doe',
      location: { lat: 40.7128, lng: -74.006 },
      skills: ['fiber', 'installation'],
      maxWorkOrders: 8,
    },
  ],
  workOrders: [
    {
      id: 'wo-1',
      location: { lat: 40.7148, lng: -74.004 },
      type: 'installation',
      priority: 'high',
      estimatedDuration: 120,
    },
  ],
  constraints: {
    maxWorkingHours: 8,
    skillMatching: true,
  },
  objectives: [
    { type: 'minimize_travel', weight: 0.6 },
    { type: 'maximize_completion', weight: 0.4 },
  ],
});

console.log(`Optimized routes: ${optimization.routes.length}`);
console.log(`Efficiency improvement: ${optimization.optimizationStats.improvementPercentage}%`);
```

## Portal-Specific Features

### Management Admin Portal

```typescript
// Full feature access
const mapProvider = await mappingSystem.createMapForPortal('management-admin', container);

// All engines available
const engines = mappingSystem.createEngines({
  portalType: 'management-admin',
  userId: 'admin-user',
  permissions: ['admin'], // Full access
});
```

### Customer Portal

```typescript
// Limited, customer-focused features
const mapProvider = await mappingSystem.createMapForPortal('customer', container, {
  zoom: 14, // Higher detail for local view
  maxZoom: 16, // Limit zoom for performance
});

// Limited engine access
const engines = mappingSystem.createEngines({
  portalType: 'customer',
  userId: 'customer-123',
  permissions: ['service_coverage_read'], // Limited permissions
});
```

### Technician Portal

```typescript
// Field-optimized configuration
const mapProvider = await mappingSystem.createMapForPortal('technician', container, {
  maxZoom: 20, // High detail for field work
  enableGPS: true, // GPS tracking
});

// Route optimization focus
const routeResult = await engines.routeOptimization.optimizeRoutes(routeRequest);
```

## Event Handling

```typescript
// Listen for map events
provider.on('click', (event) => {
  console.log('Map clicked at:', event.coordinates);
});

provider.on('markerClick', (event) => {
  console.log('Marker clicked:', event.marker.title);
});

provider.on('areaClick', (event) => {
  console.log('Service area clicked:', event.area.name);
});
```

## Performance Features

- **Caching** - Automatic caching of providers and data
- **Clustering** - Marker clustering for performance
- **Lazy Loading** - Load map features on demand
- **Memory Management** - Automatic cleanup of resources

## Development

```bash
# Install dependencies
npm install

# Build the package
npm run build

# Development mode
npm run dev
```

## Architecture

```
@dotmac/maps/
├── src/
│   ├── types/           # TypeScript interfaces
│   ├── providers/       # Map provider implementations
│   │   ├── MapProvider.ts        # Abstract base class
│   │   ├── LeafletProvider.ts    # Leaflet implementation
│   │   ├── MockProvider.ts       # Development provider
│   │   └── MapProviderFactory.ts # Provider factory
│   ├── engines/         # GIS business logic
│   │   ├── ServiceCoverageEngine.ts
│   │   ├── TerritoryEngine.ts
│   │   └── RouteOptimizationEngine.ts
│   └── index.ts         # Main exports
└── package.json
```

## License

MIT License - see LICENSE file for details.
