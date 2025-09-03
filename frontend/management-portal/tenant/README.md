# DotMac Tenant Portal

A comprehensive self-service portal for DotMac ISP Platform tenants to manage their instances, settings, billing, and support.

## Features

### 🏠 Dashboard

- **Instance Overview**: Real-time health metrics, uptime, and performance data
- **Usage Metrics**: Customer count, service statistics, and resource utilization
- **Quick Actions**: Access to common management tasks
- **Billing Summary**: Current costs and next billing date
- **System Alerts**: Health status and active alerts

### ⚙️ Instance Settings

- **General Configuration**: Instance name, timezone, language, currency
- **Branding**: Custom colors, logos, company name, CSS styling
- **Features**: Enable/disable platform features and modules
- **Notifications**: Email and system notification preferences
- **Security Settings**: Session timeout, password policies (view-only)

### 💳 Billing & Subscriptions

- **Subscription Overview**: Current plan, billing cycle, account status
- **Usage Tracking**: Real-time usage charges and overage monitoring
- **Invoice History**: Download and view past invoices
- **Payment Methods**: Manage credit cards and billing information
- **Cost Analysis**: Detailed breakdowns of infrastructure and feature costs

### 👥 User Management (Coming Soon)

- **Team Members**: Add and manage tenant users
- **Role Management**: Assign permissions and access levels
- **Invitation System**: Send invitations to new team members

### 📊 Analytics (Coming Soon)

- **Usage Analytics**: Detailed insights into customer and service metrics
- **Performance Reports**: Response times, uptime analysis
- **Growth Metrics**: Customer acquisition and churn analysis

### 🎧 Support (Coming Soon)

- **Ticket System**: Create and track support requests
- **Knowledge Base**: Self-service documentation
- **Live Chat**: Direct communication with support team

## Technology Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS with custom tenant theming
- **Authentication**: Custom tenant auth provider with session management
- **Icons**: Lucide React
- **Charts**: Recharts (for analytics)
- **Package Manager**: pnpm
- **Monorepo**: Turborepo workspace integration

## Project Structure

```
src/
├── app/
│   ├── (authenticated)/          # Protected routes
│   │   ├── dashboard/           # Main dashboard
│   │   ├── settings/            # Instance configuration
│   │   ├── billing/             # Billing and subscriptions
│   │   ├── users/               # User management (coming soon)
│   │   ├── analytics/           # Analytics (coming soon)
│   │   └── support/             # Support portal (coming soon)
│   ├── login/                   # Authentication page
│   ├── layout.tsx               # Root layout with providers
│   └── globals.css              # Global styles
├── components/
│   ├── auth/                    # Authentication components
│   └── layout/                  # Layout components
└── lib/                         # Utilities and helpers
```

## Authentication

The portal uses a custom tenant authentication system that integrates with the DotMac Management Platform:

- **Session Management**: Secure session handling with automatic refresh
- **Tenant Context**: Multi-tenant aware authentication with tenant isolation
- **Role-Based Access**: Permission checking based on tenant admin roles
- **Branding Integration**: Dynamic theming based on tenant branding settings

## API Integration

Designed to integrate with the Management Platform API:

- **Tenant Management**: `/api/v1/tenant-admin/*` endpoints
- **Real-time Data**: Instance health, usage metrics, and billing information
- **Configuration Updates**: Settings changes with restart management
- **Billing Portal**: Subscription and payment method management

## Getting Started

1. **Install Dependencies**:

   ```bash
   pnpm install
   ```

2. **Environment Setup**:

   ```bash
   cp .env.example .env.local
   # Configure your environment variables
   ```

3. **Development Server**:

   ```bash
   pnpm dev
   ```

   The portal will be available at `http://localhost:3003`

4. **Demo Login**:
   - Email: `admin@demo-tenant.com`
   - Password: `demo123`

## Configuration

### Environment Variables

```env
NEXT_PUBLIC_MANAGEMENT_API_URL=http://localhost:8000
NEXT_PUBLIC_PORTAL_TYPE=tenant
```

### Tenant Theming

The portal automatically applies tenant branding:

- **Colors**: Primary color from tenant settings
- **Logo**: Custom tenant logo in navigation
- **Company Name**: Tenant display name throughout the UI
- **Custom Domain**: Supports tenant custom domains

## Development

### Component Structure

- **Authentication**: Handled by `TenantAuthProvider` with React Context
- **Layout**: Responsive sidebar navigation with `TenantLayout`
- **Theming**: Tailwind CSS with CSS custom properties for tenant colors
- **State Management**: React hooks with session storage for persistence

### Design System

- **Colors**: Tenant-aware color system with semantic variants
- **Typography**: Inter font family with consistent sizing
- **Components**: Reusable components following DotMac design patterns
- **Spacing**: Consistent spacing scale using Tailwind utilities

### Testing (Coming Soon)

- **Unit Tests**: Jest with React Testing Library
- **Integration Tests**: API integration testing
- **E2E Tests**: Playwright for full user workflows

## Deployment

### Production Build

```bash
pnpm build
pnpm start
```

### Docker Support

The portal can be containerized alongside other DotMac applications:

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3003
CMD ["npm", "start"]
```

## Security

- **Authentication**: Secure session management with HttpOnly cookies (production)
- **Authorization**: Role-based access control with tenant isolation
- **CSRF Protection**: Built-in Next.js CSRF protection
- **Content Security Policy**: Strict CSP headers for security
- **Input Validation**: Client and server-side input sanitization

## Performance

- **Code Splitting**: Automatic code splitting with Next.js App Router
- **Image Optimization**: Next.js Image component for optimized loading
- **Caching**: Appropriate caching strategies for static and dynamic content
- **Bundle Analysis**: Webpack bundle analyzer for optimization

## Accessibility

- **WCAG 2.1**: Level AA compliance
- **Keyboard Navigation**: Full keyboard accessibility
- **Screen Readers**: Semantic HTML and ARIA labels
- **Color Contrast**: High contrast ratios for readability
- **Focus Management**: Logical focus order and visible focus indicators

## Contributing

1. **Code Style**: Prettier and ESLint configuration
2. **Commit Messages**: Conventional commit format
3. **Branch Naming**: `feature/`, `bugfix/`, `hotfix/` prefixes
4. **Testing**: All new features require tests
5. **Documentation**: Update README and component documentation

## License

Proprietary - DotMac ISP Platform
