'use client'

import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { 
  Network, 
  Database, 
  Shield, 
  Zap, 
  Cloud, 
  Settings,
  ArrowRight,
  CheckCircle,
  Server,
  Smartphone,
  Globe,
  Lock,
  BarChart3,
  Users
} from 'lucide-react'

const architectureLayers = [
  {
    id: 'frontend',
    name: 'User Interface Layer',
    description: 'Modern, responsive interfaces for all stakeholders',
    icon: Smartphone,
    color: 'text-blue-600',
    bgColor: 'bg-blue-100 dark:bg-blue-900/20',
    components: [
      { name: 'Customer Portal', description: 'Self-service customer interface' },
      { name: 'Admin Dashboard', description: 'Comprehensive management console' },
      { name: 'Technician Mobile App', description: 'Field service application' },
      { name: 'Reseller Portal', description: 'Partner management interface' }
    ],
    technologies: ['Next.js', 'React', 'TypeScript', 'Tailwind CSS', 'PWA']
  },
  {
    id: 'api',
    name: 'API Gateway Layer',
    description: 'Secure, scalable API management and routing',
    icon: Globe,
    color: 'text-green-600',
    bgColor: 'bg-green-100 dark:bg-green-900/20',
    components: [
      { name: 'REST APIs', description: 'RESTful service interfaces' },
      { name: 'GraphQL Endpoint', description: 'Flexible data querying' },
      { name: 'WebSocket Gateway', description: 'Real-time communication' },
      { name: 'Rate Limiting', description: 'API usage control and protection' }
    ],
    technologies: ['FastAPI', 'GraphQL', 'WebSockets', 'OAuth 2.0', 'JWT']
  },
  {
    id: 'services',
    name: 'Microservices Layer',
    description: 'Modular, independently deployable services',
    icon: Server,
    color: 'text-purple-600',
    bgColor: 'bg-purple-100 dark:bg-purple-900/20',
    components: [
      { name: 'Network Management', description: 'Device and topology management' },
      { name: 'Customer Management', description: 'Subscriber lifecycle management' },
      { name: 'Billing Service', description: 'Invoice and payment processing' },
      { name: 'Analytics Engine', description: 'Data processing and insights' }
    ],
    technologies: ['Python', 'Docker', 'Kubernetes', 'Redis', 'RabbitMQ']
  },
  {
    id: 'security',
    name: 'Security Layer',
    description: 'Enterprise-grade security and compliance',
    icon: Shield,
    color: 'text-red-600',
    bgColor: 'bg-red-100 dark:bg-red-900/20',
    components: [
      { name: 'Identity Management', description: 'User authentication and authorization' },
      { name: 'Encryption Service', description: 'Data encryption at rest and transit' },
      { name: 'Audit Logging', description: 'Comprehensive activity tracking' },
      { name: 'Vulnerability Scanning', description: 'Continuous security monitoring' }
    ],
    technologies: ['OAuth 2.0', 'SAML', 'AES-256', 'TLS 1.3', 'SIEM']
  },
  {
    id: 'data',
    name: 'Data Layer',
    description: 'Scalable, reliable data storage and management',
    icon: Database,
    color: 'text-orange-600',
    bgColor: 'bg-orange-100 dark:bg-orange-900/20',
    components: [
      { name: 'Primary Database', description: 'PostgreSQL for transactional data' },
      { name: 'Time Series DB', description: 'InfluxDB for metrics and monitoring' },
      { name: 'Document Store', description: 'MongoDB for flexible schema data' },
      { name: 'Data Warehouse', description: 'Analytics and reporting data store' }
    ],
    technologies: ['PostgreSQL', 'InfluxDB', 'MongoDB', 'Redis', 'Elasticsearch']
  },
  {
    id: 'infrastructure',
    name: 'Infrastructure Layer',
    description: 'Cloud-native, auto-scaling infrastructure',
    icon: Cloud,
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-100 dark:bg-indigo-900/20',
    components: [
      { name: 'Container Orchestration', description: 'Kubernetes cluster management' },
      { name: 'Load Balancing', description: 'Traffic distribution and failover' },
      { name: 'Auto Scaling', description: 'Dynamic resource allocation' },
      { name: 'Monitoring & Logging', description: 'System observability' }
    ],
    technologies: ['Kubernetes', 'Docker', 'SigNoz (OTLP)', 'ELK Stack']
  }
]

const integrations = [
  { name: 'Stripe', category: 'Payment Processing', icon: '💳' },
  { name: 'Twilio', category: 'Communications', icon: '📱' },
  { name: 'SendGrid', category: 'Email Service', icon: '📧' },
  { name: 'Slack', category: 'Team Collaboration', icon: '💬' },
  { name: 'Salesforce', category: 'CRM Integration', icon: '🏢' },
  { name: 'QuickBooks', category: 'Accounting', icon: '📊' },
  { name: 'Zapier', category: 'Workflow Automation', icon: '⚡' },
  { name: 'DataDog', category: 'Monitoring', icon: '📈' }
]

const deploymentOptions = [
  {
    name: 'Cloud Hosted',
    description: 'Fully managed SaaS deployment',
    features: ['Zero maintenance', 'Automatic updates', 'Global CDN', '99.9% SLA'],
    popular: true
  },
  {
    name: 'Private Cloud',
    description: 'Dedicated cloud environment',
    features: ['Enhanced security', 'Custom compliance', 'Reserved resources', 'Priority support']
  },
  {
    name: 'On-Premises',
    description: 'Self-hosted deployment',
    features: ['Complete control', 'Custom configuration', 'Local data residency', 'Offline capability']
  },
  {
    name: 'Hybrid',
    description: 'Mix of cloud and on-premises',
    features: ['Flexible deployment', 'Data sovereignty', 'Cost optimization', 'Gradual migration']
  }
]

export function Architecture() {
  const [activeLayer, setActiveLayer] = useState('frontend')
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false)

  const currentLayer = architectureLayers.find(layer => layer.id === activeLayer) || architectureLayers[0]

  return (
    <div className="py-24 sm:py-32 bg-background">
      <div className="container-custom">
        {/* Section Header */}
        <div className="text-center mb-16">
          <Badge variant="secondary" className="mb-4">
            Platform Architecture
          </Badge>
          <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl mb-6">
            Built for <span className="text-gradient">enterprise scale</span>
          </h2>
          <p className="text-lg text-muted-foreground max-w-3xl mx-auto">
            Our platform is architected with modern, cloud-native principles to ensure 
            scalability, security, and reliability at every layer. From user interfaces 
            to data storage, every component is designed for enterprise-grade performance.
          </p>
        </div>

        {/* Architecture Diagram */}
        <div className="mb-16">
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 gap-4">
              {architectureLayers.map((layer, index) => (
                <div
                  key={layer.id}
                  className={`group relative p-6 rounded-xl border transition-all duration-300 cursor-pointer ${
                    activeLayer === layer.id
                      ? 'border-primary bg-primary/5 shadow-lg'
                      : 'border-border bg-background hover:border-primary/50 hover:bg-muted/50'
                  }`}
                  onClick={() => setActiveLayer(layer.id)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                        activeLayer === layer.id ? layer.bgColor : 'bg-muted'
                      }`}>
                        <layer.icon className={`w-6 h-6 ${
                          activeLayer === layer.id ? layer.color : 'text-muted-foreground'
                        }`} />
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-foreground">
                          {layer.name}
                        </h3>
                        <p className="text-sm text-muted-foreground">
                          {layer.description}
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-3">
                      <div className="hidden sm:flex items-center space-x-2">
                        {layer.technologies.slice(0, 3).map((tech, i) => (
                          <Badge key={i} variant="outline" className="text-xs">
                            {tech}
                          </Badge>
                        ))}
                        {layer.technologies.length > 3 && (
                          <Badge variant="outline" className="text-xs">
                            +{layer.technologies.length - 3}
                          </Badge>
                        )}
                      </div>
                      <ArrowRight className={`w-5 h-5 transition-transform ${
                        activeLayer === layer.id ? 'rotate-90 text-primary' : 'text-muted-foreground'
                      }`} />
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {activeLayer === layer.id && (
                    <div className="mt-6 pt-6 border-t border-border animate-in slide-in-from-top-2 duration-300">
                      <div className="grid md:grid-cols-2 gap-6">
                        {/* Components */}
                        <div>
                          <h4 className="text-sm font-semibold text-foreground mb-3">
                            Key Components
                          </h4>
                          <div className="space-y-3">
                            {layer.components.map((component, i) => (
                              <div key={i} className="flex items-start space-x-3">
                                <CheckCircle className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                                <div>
                                  <div className="text-sm font-medium text-foreground">
                                    {component.name}
                                  </div>
                                  <div className="text-xs text-muted-foreground">
                                    {component.description}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Technologies */}
                        <div>
                          <h4 className="text-sm font-semibold text-foreground mb-3">
                            Technologies
                          </h4>
                          <div className="flex flex-wrap gap-2">
                            {layer.technologies.map((tech, i) => (
                              <Badge key={i} variant="secondary" className="text-xs">
                                {tech}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Integrations */}
        <div className="mb-16">
          <div className="text-center mb-8">
            <h3 className="text-2xl font-bold text-foreground mb-4">
              200+ Ready Integrations
            </h3>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Connect with your existing tools and services seamlessly. 
              Our platform integrates with industry-leading solutions out of the box.
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {integrations.map((integration, index) => (
              <div 
                key={integration.name}
                className="group p-4 bg-muted/30 rounded-lg border border-border hover:border-primary/50 hover:bg-background transition-all duration-200"
              >
                <div className="flex items-center space-x-3">
                  <div className="text-2xl">{integration.icon}</div>
                  <div>
                    <div className="font-medium text-foreground text-sm">
                      {integration.name}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {integration.category}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="text-center mt-8">
            <Button variant="outline">
              View All Integrations
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Deployment Options */}
        <div className="mb-16">
          <div className="text-center mb-8">
            <h3 className="text-2xl font-bold text-foreground mb-4">
              Flexible Deployment Options
            </h3>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Deploy the platform in the way that best fits your business requirements, 
              compliance needs, and operational preferences.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {deploymentOptions.map((option, index) => (
              <div 
                key={option.name}
                className={`relative p-6 rounded-xl border bg-background hover:bg-muted/30 transition-all duration-200 ${
                  option.popular 
                    ? 'border-primary ring-2 ring-primary/20' 
                    : 'border-border'
                }`}
              >
                {option.popular && (
                  <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                    <Badge className="bg-primary text-primary-foreground">
                      Most Popular
                    </Badge>
                  </div>
                )}
                
                <h4 className="text-lg font-semibold text-foreground mb-2">
                  {option.name}
                </h4>
                <p className="text-sm text-muted-foreground mb-4">
                  {option.description}
                </p>
                
                <ul className="space-y-2">
                  {option.features.map((feature, i) => (
                    <li key={i} className="flex items-start space-x-2">
                      <CheckCircle className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                      <span className="text-sm text-muted-foreground">{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Technical Specifications */}
        <div className="bg-muted/30 rounded-2xl p-8 border border-border">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-bold text-foreground">
              Technical Specifications
            </h3>
            <Button 
              variant="outline" 
              onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
            >
              {showTechnicalDetails ? 'Hide Details' : 'Show Details'}
              <Settings className="ml-2 h-4 w-4" />
            </Button>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-primary mb-2">99.9%</div>
              <div className="text-sm text-muted-foreground">Uptime SLA</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-primary mb-2">&lt; 100ms</div>
              <div className="text-sm text-muted-foreground">API Response Time</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-primary mb-2">10M+</div>
              <div className="text-sm text-muted-foreground">Requests/Hour</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-primary mb-2">Auto</div>
              <div className="text-sm text-muted-foreground">Scaling</div>
            </div>
          </div>

          {showTechnicalDetails && (
            <div className="mt-8 pt-8 border-t border-border animate-in slide-in-from-top-2 duration-300">
              <div className="grid md:grid-cols-2 gap-8">
                <div>
                  <h4 className="font-semibold text-foreground mb-3">Performance Specs</h4>
                  <ul className="space-y-2 text-sm">
                    <li className="flex justify-between">
                      <span className="text-muted-foreground">Concurrent Users:</span>
                      <span className="font-medium">100,000+</span>
                    </li>
                    <li className="flex justify-between">
                      <span className="text-muted-foreground">Database Connections:</span>
                      <span className="font-medium">10,000+</span>
                    </li>
                    <li className="flex justify-between">
                      <span className="text-muted-foreground">Data Processing:</span>
                      <span className="font-medium">1TB/day</span>
                    </li>
                    <li className="flex justify-between">
                      <span className="text-muted-foreground">Backup Frequency:</span>
                      <span className="font-medium">Real-time</span>
                    </li>
                  </ul>
                </div>
                
                <div>
                  <h4 className="font-semibold text-foreground mb-3">Security & Compliance</h4>
                  <ul className="space-y-2 text-sm">
                    <li className="flex justify-between">
                      <span className="text-muted-foreground">Encryption:</span>
                      <span className="font-medium">AES-256</span>
                    </li>
                    <li className="flex justify-between">
                      <span className="text-muted-foreground">Authentication:</span>
                      <span className="font-medium">OAuth 2.0 / SAML</span>
                    </li>
                    <li className="flex justify-between">
                      <span className="text-muted-foreground">Compliance:</span>
                      <span className="font-medium">SOC 2, GDPR, HIPAA</span>
                    </li>
                    <li className="flex justify-between">
                      <span className="text-muted-foreground">Audit Logs:</span>
                      <span className="font-medium">Complete Activity</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* CTA */}
        <div className="mt-16 text-center">
          <h3 className="text-2xl font-bold text-foreground mb-4">
            Ready to see the architecture in action?
          </h3>
          <p className="text-muted-foreground mb-8 max-w-2xl mx-auto">
            Schedule a technical deep-dive with our solutions architects to explore 
            how our platform can be tailored to your specific requirements.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg">
              Schedule Technical Demo
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
            <Button variant="outline" size="lg">
              Download Architecture Guide
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
