# DotMac Developer Tools

**Advanced CLI and SDK generation platform for DotMac ISP framework**

The DotMac Developer Tools plane provides comprehensive tooling for service scaffolding, SDK generation, developer portals, and zero-trust security implementation. This plane eliminates manual service creation and provides self-service developer experience.

## 🚀 Key Features

### Service Scaffolding & Generation
- **Automated Service Generation**: Create new DotMac services with complete project structure
- **Multi-Language SDK Generation**: Generate SDKs for Python, TypeScript, Go, Java, and more
- **Template Engine**: Customizable templates for different service types and patterns
- **Code Generation**: Automatic API client generation from OpenAPI specifications

### Developer Portal
- **Self-Service API Access**: Interactive documentation and API exploration
- **API Key Management**: Automated provisioning and management of API credentials
- **Usage Analytics**: Real-time API usage metrics and quotas for external partners
- **Partner Onboarding**: Streamlined registration and approval workflows

### Zero-Trust Security
- **Service Mesh Integration**: Automatic mTLS between services
- **Identity-Based Access**: Service-to-service authentication with certificates
- **Policy Engine**: Fine-grained authorization policies for inter-service communication
- **Security Scanning**: Automated vulnerability assessment and compliance checking

## 📦 Installation

```bash
# Install the developer tools
pip install dotmac-devtools

# Initialize developer workspace
dotmac init workspace --name my-isp-project

# Generate a new service
dotmac generate service --name customer-management --type rest-api

# Generate SDK for external partners
dotmac generate sdk --language python --output-dir ./sdks
```

## 🛠️ Available Commands

### Service Generation
```bash
# Create new service from template
dotmac generate service --name billing-service --type microservice
dotmac generate service --name analytics-api --type rest-api --database postgres

# Generate API client SDKs
dotmac generate sdk --language typescript --api-spec openapi.yaml
dotmac generate sdk --language go --service billing-service

# Scaffold complete project
dotmac scaffold project --name new-isp --region us-west
```

### Developer Portal Management
```bash
# Setup developer portal
dotmac portal init --domain developer.myisp.com
dotmac portal deploy --environment production

# Manage API documentation
dotmac docs generate --service all
dotmac docs publish --version v2.1.0
```

### Security & Zero-Trust
```bash
# Initialize zero-trust model
dotmac security init-zero-trust --cluster k8s-prod
dotmac security generate-certs --service customer-api

# Policy management
dotmac security create-policy --from-service billing --to-service analytics
dotmac security audit --environment production
```

## 📋 Service Templates

### Available Service Types
- **REST API**: Full-featured REST API with OpenAPI documentation
- **GraphQL Service**: GraphQL API with schema-first development
- **Microservice**: Event-driven microservice with message handling
- **Background Worker**: Async job processing service
- **Data Pipeline**: ETL/ELT data processing service
- **Gateway Service**: API gateway and routing service

### Language Support
- **Python**: FastAPI, Django, Flask templates
- **TypeScript/Node.js**: Express, NestJS, Fastify templates
- **Go**: Gin, Echo, Fiber templates
- **Java**: Spring Boot, Quarkus templates
- **C#**: ASP.NET Core templates

## 🔧 SDK Generation

### Supported Languages
```bash
# Python SDK with async support
dotmac generate sdk --language python --async

# TypeScript SDK with React hooks
dotmac generate sdk --language typescript --framework react

# Go SDK with context support
dotmac generate sdk --language go --package-name dotmac-client

# Java SDK with Spring integration
dotmac generate sdk --language java --framework spring
```

### SDK Features
- **Type Safety**: Full type definitions and validation
- **Async Support**: Native async/await patterns where applicable
- **Error Handling**: Comprehensive error types and handling
- **Authentication**: Built-in support for API keys, JWT, OAuth2
- **Rate Limiting**: Client-side rate limiting and retry logic
- **Documentation**: Auto-generated documentation and examples

## 🌐 Developer Portal

### Features
- **Interactive API Explorer**: Test APIs directly in the browser
- **Authentication Management**: Self-service API key generation
- **Usage Monitoring**: Real-time API usage and quota tracking
- **Code Examples**: Generated code samples in multiple languages
- **Support Integration**: Direct integration with support systems

### Setup Example
```bash
# Initialize developer portal
dotmac portal init \\
  --domain api.myisp.com \\
  --company "My ISP Company" \\
  --support-email api-support@myisp.com

# Configure authentication
dotmac portal auth configure \\
  --provider oauth2 \\
  --client-id my-oauth-client \\
  --scopes "api:read,api:write"

# Deploy to production
dotmac portal deploy --environment production --ssl-cert /path/to/cert
```

## 🔒 Zero-Trust Security Model

### Service Mesh Configuration
```bash
# Initialize service mesh with mTLS
dotmac security init-mesh \\
  --provider istio \\
  --enable-mtls \\
  --ca-provider vault

# Generate service certificates
dotmac security cert generate \\
  --service customer-api \\
  --namespace production \\
  --validity 90d

# Apply security policies
dotmac security policy apply \\
  --policy-file security-policies.yaml \\
  --environment production
```

### Policy Definition
```yaml
# security-policies.yaml
apiVersion: security.dotmac.com/v1
kind: ServiceSecurityPolicy
metadata:
  name: billing-service-policy
spec:
  service: billing-service
  ingress:
    - from:
        service: api-gateway
      action: allow
      conditions:
        - authenticated: true
        - scopes: ["billing:read", "billing:write"]
  egress:
    - to:
        service: customer-database
      action: allow
      conditions:
        - encrypted: true
```

## 📊 Usage Examples

### Complete Service Generation Workflow
```bash
# 1. Create new service
dotmac generate service \\
  --name payment-processor \\
  --type microservice \\
  --database postgres \\
  --cache redis \\
  --queue rabbitmq

# 2. Generate API documentation
cd payment-processor
dotmac docs generate --format openapi

# 3. Create SDK for partners
dotmac generate sdk \\
  --language python \\
  --output-dir ./sdk-python \\
  --package-name payment-client

# 4. Deploy to development
dotmac deploy --environment development

# 5. Setup security policies
dotmac security policy create \\
  --service payment-processor \\
  --allow-from api-gateway \\
  --require-auth jwt
```

### Developer Portal Setup
```bash
# Setup complete developer portal
dotmac portal setup \\
  --domain developer.myisp.com \\
  --apis "customer-api,billing-api,network-api" \\
  --auth-provider auth0 \\
  --payment-provider stripe

# Configure partner registration
dotmac portal configure \\
  --approval-workflow manual \\
  --tier-limits "starter:1000,pro:10000,enterprise:unlimited" \\
  --support-integration zendesk
```

## 🧪 Testing Generated Code

The developer tools include comprehensive testing capabilities:

```bash
# Test generated service
dotmac test service --name my-service --coverage 80

# Validate generated SDK
dotmac test sdk --language python --api-spec openapi.yaml

# Security audit
dotmac security audit --service all --report detailed
```

## 📚 Template Customization

Create custom templates for your organization:

```bash
# Create custom template
dotmac template create \\
  --name my-org-api \\
  --base-template rest-api \\
  --customize

# Use custom template
dotmac generate service \\
  --name new-service \\
  --template my-org-api
```

## 🔧 Configuration

Global configuration in `~/.dotmac/config.yaml`:

```yaml
# Default settings
defaults:
  author: "My ISP Team"
  license: "MIT"
  python_version: "3.11"
  docker_registry: "myregistry.com"

# Template settings
templates:
  custom_path: "~/.dotmac/templates"
  default_language: "python"

# Security settings
security:
  enforce_mtls: true
  cert_authority: "vault"
  policy_enforcement: "strict"

# Portal settings
portal:
  default_domain: "developer.myisp.com"
  auth_provider: "auth0"
  analytics_provider: "mixpanel"
```

## 🚀 Getting Started

1. **Install the tools**: `pip install dotmac-devtools`
2. **Initialize workspace**: `dotmac init workspace`
3. **Generate your first service**: `dotmac generate service --name hello-world`
4. **Setup developer portal**: `dotmac portal init`
5. **Enable zero-trust**: `dotmac security init-zero-trust`

## 📖 Documentation

- [Service Generation Guide](docs/service-generation.md)
- [SDK Development](docs/sdk-development.md)
- [Developer Portal Setup](docs/developer-portal.md)
- [Zero-Trust Implementation](docs/zero-trust.md)
- [Template Development](docs/template-development.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**DotMac Developer Tools** - Accelerating ISP service development with automated tooling and zero-trust security.