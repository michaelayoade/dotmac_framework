'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  Network, 
  Users, 
  BarChart3, 
  Shield, 
  Zap, 
  Settings,
  ArrowRight,
  CheckCircle,
  Smartphone,
  Globe,
  TrendingUp,
  Clock,
  Wrench,
  Lock
} from 'lucide-react'

const features = [
  {
    id: 'network',
    name: 'Network Management',
    description: 'Comprehensive network monitoring, automation, and optimization tools.',
    icon: Network,
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-100 dark:bg-blue-900/20',
    features: [
      'Real-time network monitoring',
      'Automated fault detection',
      'Performance optimization',
      'Capacity planning tools',
      'Network topology mapping',
      'SLA monitoring & reporting'
    ],
    benefits: [
      '99.9% network uptime',
      '60% faster issue resolution',
      '40% reduction in maintenance costs',
      'Proactive problem detection'
    ]
  },
  {
    id: 'customer',
    name: 'Customer Experience',
    description: 'End-to-end customer management and self-service portal solutions.',
    icon: Users,
    color: 'text-green-600 dark:text-green-400',
    bgColor: 'bg-green-100 dark:bg-green-900/20',
    features: [
      'Customer self-service portal',
      'Automated billing & invoicing',
      'Support ticket management',
      'Service provisioning',
      'Usage analytics & reporting',
      'Mobile app integration'
    ],
    benefits: [
      '50% reduction in support tickets',
      '90% customer satisfaction',
      'Automated service provisioning',
      '24/7 self-service availability'
    ]
  },
  {
    id: 'analytics',
    name: 'Analytics & Insights',
    description: 'Advanced analytics, reporting, and business intelligence tools.',
    icon: BarChart3,
    color: 'text-purple-600 dark:text-purple-400',
    bgColor: 'bg-purple-100 dark:bg-purple-900/20',
    features: [
      'Real-time dashboard',
      'Custom report builder',
      'Predictive analytics',
      'Revenue optimization',
      'Customer behavior insights',
      'Performance benchmarking'
    ],
    benefits: [
      'Data-driven decisions',
      '25% increase in ARPU',
      'Predictive maintenance',
      'Market trend analysis'
    ]
  },
  {
    id: 'security',
    name: 'Security & Compliance',
    description: 'Enterprise-grade security, compliance, and risk management.',
    icon: Shield,
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-100 dark:bg-red-900/20',
    features: [
      'Multi-factor authentication',
      'Role-based access control',
      'Audit logging & compliance',
      'Data encryption',
      'Vulnerability scanning',
      'Incident response workflows'
    ],
    benefits: [
      'SOC 2 Type II certified',
      '256-bit encryption',
      'GDPR & CCPA compliant',
      'Zero security incidents'
    ]
  },
  {
    id: 'automation',
    name: 'Process Automation',
    description: 'Intelligent automation for operations, provisioning, and workflows.',
    icon: Zap,
    color: 'text-orange-600 dark:text-orange-400',
    bgColor: 'bg-orange-100 dark:bg-orange-900/20',
    features: [
      'Workflow automation',
      'Service provisioning',
      'Automated testing',
      'Configuration management',
      'Deployment pipelines',
      'AI-powered optimization'
    ],
    benefits: [
      '80% faster deployments',
      'Zero-touch provisioning',
      'Reduced human errors',
      'Scalable operations'
    ]
  },
  {
    id: 'integration',
    name: 'Platform Integration',
    description: 'Seamless integration with existing systems and third-party tools.',
    icon: Settings,
    color: 'text-indigo-600 dark:text-indigo-400',
    bgColor: 'bg-indigo-100 dark:bg-indigo-900/20',
    features: [
      'REST API & webhooks',
      'Third-party integrations',
      'Legacy system migration',
      'Custom connectors',
      'Real-time synchronization',
      'Microservices architecture'
    ],
    benefits: [
      '200+ integrations available',
      'API-first architecture',
      'Flexible deployment options',
      'Future-proof platform'
    ]
  }
]

const additionalFeatures = [
  {
    icon: Smartphone,
    name: 'Mobile-First Design',
    description: 'Native mobile apps for field technicians and customers'
  },
  {
    icon: Globe,
    name: 'Multi-Tenant Architecture',
    description: 'Support for multiple ISPs on a single platform'
  },
  {
    icon: TrendingUp,
    name: 'Scalable Infrastructure',
    description: 'Handles growth from startup to enterprise scale'
  },
  {
    icon: Clock,
    name: '24/7 Monitoring',
    description: 'Round-the-clock system monitoring and alerting'
  },
  {
    icon: Wrench,
    name: 'Professional Services',
    description: 'Expert implementation and ongoing support'
  },
  {
    icon: Lock,
    name: 'Data Privacy',
    description: 'GDPR, CCPA, and industry compliance guaranteed'
  }
]

export function Features() {
  const [activeFeature, setActiveFeature] = useState('network')

  const currentFeature = features.find(f => f.id === activeFeature) || features[0]

  return (
    <div className="py-24 sm:py-32 bg-background">
      <div className="container-custom">
        {/* Section Header */}
        <div className="mx-auto max-w-2xl text-center mb-16">
          <Badge variant="secondary" className="mb-4">
            Platform Features
          </Badge>
          <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            Everything your ISP needs,{' '}
            <span className="text-gradient">in one platform</span>
          </h2>
          <p className="mt-6 text-lg leading-8 text-muted-foreground">
            From network automation to customer experience, our comprehensive platform 
            handles every aspect of ISP operations with enterprise-grade reliability.
          </p>
        </div>

        {/* Feature Navigation */}
        <div className="mb-16">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            {features.map((feature) => (
              <button
                key={feature.id}
                onClick={() => setActiveFeature(feature.id)}
                className={`group relative p-4 rounded-xl border transition-all duration-200 ${
                  activeFeature === feature.id
                    ? 'border-primary bg-primary/5 shadow-md'
                    : 'border-border bg-background hover:border-primary/50 hover:bg-muted/50'
                }`}
              >
                <div className={`w-12 h-12 rounded-lg flex items-center justify-center mb-3 mx-auto ${
                  activeFeature === feature.id ? feature.bgColor : 'bg-muted'
                }`}>
                  <feature.icon className={`w-6 h-6 ${
                    activeFeature === feature.id ? feature.color : 'text-muted-foreground'
                  }`} />
                </div>
                <h3 className="text-sm font-semibold text-center text-foreground">
                  {feature.name}
                </h3>
                {activeFeature === feature.id && (
                  <div className="absolute inset-0 rounded-xl border-2 border-primary opacity-50" />
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Feature Details */}
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          {/* Feature Content */}
          <div className="feature-card">
            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mb-6 ${currentFeature.bgColor}`}>
              <currentFeature.icon className={`w-8 h-8 ${currentFeature.color}`} />
            </div>
            
            <h3 className="text-2xl font-bold text-foreground mb-4">
              {currentFeature.name}
            </h3>
            
            <p className="text-lg text-muted-foreground mb-8">
              {currentFeature.description}
            </p>

            <div className="grid sm:grid-cols-2 gap-8">
              {/* Features List */}
              <div>
                <h4 className="text-lg font-semibold text-foreground mb-4">
                  Key Features
                </h4>
                <ul className="space-y-3">
                  {currentFeature.features.map((feature, index) => (
                    <li key={index} className="flex items-start gap-3">
                      <CheckCircle className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                      <span className="text-muted-foreground">{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Benefits List */}
              <div>
                <h4 className="text-lg font-semibold text-foreground mb-4">
                  Key Benefits
                </h4>
                <ul className="space-y-3">
                  {currentFeature.benefits.map((benefit, index) => (
                    <li key={index} className="flex items-start gap-3">
                      <ArrowRight className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                      <span className="text-muted-foreground">{benefit}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="mt-8">
              <Button>
                Learn More About {currentFeature.name}
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Feature Visual */}
          <div className="relative feature-card">
            <div className="relative rounded-2xl overflow-hidden bg-gradient-to-br from-muted/50 to-muted border border-border shadow-feature">
              {/* Mock Dashboard/Interface */}
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${currentFeature.bgColor}`}>
                      <currentFeature.icon className={`w-5 h-5 ${currentFeature.color}`} />
                    </div>
                    <div>
                      <h5 className="font-semibold text-foreground">{currentFeature.name}</h5>
                      <p className="text-sm text-muted-foreground">Live Dashboard</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                    <span className="text-sm text-muted-foreground">Online</span>
                  </div>
                </div>

                {/* Mock Metrics Grid */}
                <div className="grid grid-cols-2 gap-4 mb-6">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <div key={i} className="p-3 bg-background rounded-lg border border-border">
                      <div className="text-2xl font-bold text-foreground mb-1">
                        {['2.4K', '99.9%', '847ms', '12'][i]}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {['Active Users', 'Uptime', 'Response Time', 'Incidents'][i]}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Mock Chart */}
                <div className="h-32 bg-background rounded-lg border border-border p-3 flex items-end justify-between">
                  {Array.from({ length: 12 }).map((_, i) => (
                    <div
                      key={i}
                      className={`w-4 rounded-t transition-all duration-1000 ${currentFeature.bgColor}`}
                      style={{ 
                        height: `${Math.sin(i * 0.5) * 50 + 60}%`,
                        animationDelay: `${i * 100}ms`
                      }}
                    />
                  ))}
                </div>
              </div>
              
              {/* Gradient Overlay */}
              <div className="absolute inset-0 bg-gradient-to-t from-background/20 to-transparent pointer-events-none" />
            </div>
          </div>
        </div>

        {/* Additional Features Grid */}
        <div className="mt-24">
          <div className="text-center mb-12">
            <h3 className="text-2xl font-bold text-foreground mb-4">
              And much more...
            </h3>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Discover additional capabilities that make our platform the most comprehensive 
              ISP management solution available.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {additionalFeatures.map((feature, index) => (
              <div 
                key={feature.name}
                className={`group p-6 rounded-xl border border-border bg-background hover:bg-muted/50 transition-all duration-200 card-hover feature-card stagger-${(index % 6) + 1}`}
              >
                <div className="w-12 h-12 rounded-lg bg-muted flex items-center justify-center mb-4 group-hover:bg-primary/10 transition-colors">
                  <feature.icon className="w-6 h-6 text-muted-foreground group-hover:text-primary transition-colors" />
                </div>
                <h4 className="text-lg font-semibold text-foreground mb-2">
                  {feature.name}
                </h4>
                <p className="text-muted-foreground text-sm">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* CTA Section */}
        <div className="mt-20 text-center">
          <div className="max-w-2xl mx-auto">
            <h3 className="text-2xl font-bold text-foreground mb-4">
              Ready to transform your ISP operations?
            </h3>
            <p className="text-muted-foreground mb-8">
              See how our platform can streamline your operations, improve customer satisfaction, 
              and drive business growth.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button size="lg">
                Start Free Trial
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
              <Button variant="outline" size="lg">
                Schedule Demo
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}