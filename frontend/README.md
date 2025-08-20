# DotMac Frontend

Modern TypeScript frontend for the DotMac ISP platform built with Next.js 14,
Turbo, and a component-driven architecture.

## Architecture

### Monorepo Structure

```
frontend/
├── apps/                    # Frontend applications
│   ├── admin/              # Admin portal (port 3000)
│   ├── customer/           # Customer portal (port 3001)
│   └── reseller/           # Reseller portal (port 3002)
├── packages/               # Shared packages
│   ├── headless/          # Business logic & hooks
│   ├── primitives/        # UI components
│   └── styled-components/ # Portal-specific styled components
└── turbo.json             # Turbo build configuration
```

### Applications

#### 🔧 Admin Portal (`/apps/admin`)

Full-featured ISP administration interface for:

- Network infrastructure management
- Customer account administration
- Billing and revenue operations
- Support ticket management
- System analytics and monitoring
- User and role management
- Audit logging and security

**Target Users**: ISP administrators, network engineers, support staff

#### 👤 Customer Portal (`/apps/customer`)

Self-service portal for ISP customers:

- Service status and usage monitoring
- Bill viewing and payment processing
- Support ticket creation and tracking
- Account settings management
- Service upgrade/downgrade requests

**Target Users**: ISP end customers

#### 🤝 Reseller Portal (`/apps/reseller`)

Partner interface for ISP resellers:

- Customer onboarding and management
- Commission tracking and reporting
- Sales analytics and performance metrics
- Territory management
- Marketing materials and resources

**Target Users**: ISP channel partners and resellers

### Shared Packages

#### 📚 Headless (`/packages/headless`)

Business logic and state management:

- **Authentication & Authorization**: Multi-tenant auth with RBAC
- **Real-time Synchronization**: WebSocket integration with optimistic updates
- **Offline Support**: Smart caching and offline-first architecture
- **Business Workflows**: ISP-specific workflow automation
- **Multi-tenant Management**: Tenant switching and isolation
- **API Integration**: Type-safe API client with error handling

#### 🎨 Primitives (`/packages/primitives`)

Portal-agnostic UI components:

- **Data Visualization**: Charts, graphs, and analytics widgets
- **Advanced Tables**: Filtering, sorting, pagination, virtual scrolling
- **Real-time Widgets**: Network monitoring and system metrics
- **File Management**: Upload, validation, and progress tracking
- **Notifications**: Toast and persistent notification system
- **Forms**: Validation and accessibility-compliant inputs

#### 💅 Styled Components (`/packages/styled-components`)

Portal-specific design systems:

- **Theming**: Portal-specific color schemes and branding
- **Component Variants**: Admin, customer, and reseller variants
- **Design Tokens**: Consistent spacing, typography, and colors
- **Accessibility**: WCAG-compliant implementations
- **Responsive Design**: Mobile-first responsive layouts

## Key Features

### 🏢 Multi-Tenant Architecture

- **Tenant Isolation**: Secure data separation between ISP instances
- **Dynamic Branding**: Per-tenant logos, colors, and styling
- **Permission Management**: Role-based access control per tenant
- **Real-time Switching**: Seamless tenant context switching

### 🔄 Real-time Capabilities

- **Live Updates**: WebSocket-powered real-time data synchronization
- **Network Monitoring**: Live device status and performance metrics
- **Instant Notifications**: Real-time alerts and system updates
- **Collaborative Features**: Multi-user workflow coordination

### 📱 Offline-First Design

- **Smart Caching**: Intelligent data caching with TTL management
- **Offline Operations**: Queue operations for when connectivity returns
- **Optimistic Updates**: Immediate UI feedback with rollback capability
- **Sync Management**: Automatic synchronization when online

### 🔐 Enterprise Security

- **Authentication**: JWT-based auth with refresh token rotation
- **Authorization**: Fine-grained RBAC with ISP-specific roles
- **Audit Logging**: Comprehensive activity tracking
- **Data Validation**: Input sanitization and type safety

### 🚀 Performance Optimizations

- **Code Splitting**: Route-based and component-level splitting
- **Virtual Scrolling**: Handle large datasets efficiently
- **Image Optimization**: Next.js Image component with lazy loading
- **Bundle Analysis**: Turbo-powered build optimization

## Development

### Prerequisites

- Node.js 18.0.0+
- pnpm 8.0.0+
- DotMac Platform API running

### Quick Start

```bash
# Install dependencies
pnpm install

# Start all applications in development
pnpm dev

# Start specific applications
pnpm --filter @dotmac/admin-app dev    # Admin portal
pnpm --filter @dotmac/customer-app dev # Customer portal
pnpm --filter @dotmac/reseller-app dev # Reseller portal

# Build all applications
pnpm build

# Run linting and type checking
pnpm lint
pnpm type-check
```

### Application URLs

- **Admin Portal**: http://localhost:3000
- **Customer Portal**: http://localhost:3001
- **Reseller Portal**: http://localhost:3002

### Environment Variables

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WEBSOCKET_URL=ws://localhost:3001

# Feature Flags
NEXT_PUBLIC_ENABLE_OFFLINE_MODE=true
NEXT_PUBLIC_ENABLE_REAL_TIME=true
NEXT_PUBLIC_ENABLE_ANALYTICS=true
```

## Technology Stack

### Core Framework

- **Next.js 14**: React framework with App Router
- **TypeScript**: Type-safe development
- **Turbo**: Monorepo build system and task runner

### State Management

- **Zustand**: Lightweight state management
- **TanStack Query**: Server state management and caching
- **Socket.IO**: Real-time WebSocket communication

### UI & Styling

- **Tailwind CSS**: Utility-first CSS framework
- **Radix UI**: Accessible component primitives
- **Lucide React**: Consistent icon library
- **Class Variance Authority**: Type-safe component variants

### Data & Visualization

- **Recharts**: Composable charting library
- **Zod**: Runtime type validation
- **Date-fns**: Date manipulation utilities

### Development Tools

- **ESLint**: Code linting and formatting
- **Prettier**: Code formatting
- **Changesets**: Version management and publishing

## ISP-Specific Features

### Network Management

- **Device Monitoring**: Real-time status of routers, switches, and access
  points
- **Performance Metrics**: Bandwidth utilization, latency, and error rates
- **Topology Visualization**: Interactive network topology maps
- **Incident Management**: Automated incident detection and response workflows

### Customer Management

- **Service Provisioning**: Automated customer onboarding workflows
- **Usage Analytics**: Detailed bandwidth and usage reporting
- **Billing Integration**: Real-time billing calculations and invoice generation
- **Support Integration**: Integrated ticketing and chat support

### Business Intelligence

- **Revenue Analytics**: MRR tracking, churn analysis, and growth metrics
- **Operational Metrics**: SLA compliance, MTTR, and service quality metrics
- **Reseller Performance**: Partner sales tracking and commission management
- **Predictive Analytics**: Usage forecasting and capacity planning

## Deployment

### Production Build

```bash
# Build all applications for production
pnpm build

# Build specific application
pnpm --filter @dotmac/admin-app build
```

### Docker Deployment

```bash
# Build Docker images
docker build -f apps/admin/Dockerfile -t dotmac-admin .
docker build -f apps/customer/Dockerfile -t dotmac-customer .
docker build -f apps/reseller/Dockerfile -t dotmac-reseller .

# Run with Docker Compose
docker-compose -f docker-compose.frontend.yml up
```

### Environment-Specific Configurations

- **Development**: Hot reloading, source maps, debug logging
- **Staging**: Production build with debug features
- **Production**: Optimized build, error reporting, analytics

## Contributing

### Code Standards

- **TypeScript**: Strict mode enabled with comprehensive typing
- **Components**: Functional components with hooks
- **Testing**: Jest + React Testing Library (planned)
- **Documentation**: Comprehensive JSDoc comments

### Component Development

1. Create components in appropriate package (`primitives` vs
   `styled-components`)
2. Follow portal-specific design patterns
3. Implement proper TypeScript interfaces
4. Add accessibility attributes (ARIA)
5. Include responsive design considerations

### Business Logic Development

1. Implement hooks in `headless` package
2. Follow established patterns for state management
3. Include offline support where applicable
4. Add proper error handling and loading states
5. Document ISP-specific use cases
