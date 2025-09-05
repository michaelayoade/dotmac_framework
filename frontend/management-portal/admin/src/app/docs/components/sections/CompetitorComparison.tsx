'use client'

import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { 
  CheckCircle, 
  X, 
  Minus,
  ArrowRight,
  Crown,
  Star,
  Zap,
  Shield,
  Users,
  Clock
} from 'lucide-react'

const features = [
  {
    category: 'Core Platform',
    items: [
      { name: 'Network Monitoring & Management', description: 'Real-time network monitoring and automated management' },
      { name: 'Customer Self-Service Portal', description: 'Comprehensive customer portal with billing and support' },
      { name: 'Automated Provisioning', description: 'Zero-touch service provisioning and activation' },
      { name: 'Multi-Tenant Architecture', description: 'Support for multiple ISPs on single platform' },
      { name: 'API-First Design', description: 'Comprehensive REST APIs for all functionality' },
    ]
  },
  {
    category: 'Advanced Features',
    items: [
      { name: 'AI-Powered Analytics', description: 'Machine learning for predictive insights and optimization' },
      { name: 'Real-Time Dashboard', description: 'Live operational dashboard with custom metrics' },
      { name: 'Mobile Applications', description: 'Native mobile apps for customers and technicians' },
      { name: 'White-Label Solutions', description: 'Fully customizable branding and theming' },
      { name: 'Advanced Reporting', description: 'Custom report builder with 50+ templates' },
    ]
  },
  {
    category: 'Integration & Scalability',
    items: [
      { name: '200+ Pre-Built Integrations', description: 'Ready integrations with popular business tools' },
      { name: 'Webhook Support', description: 'Real-time event notifications and automation' },
      { name: 'Auto-Scaling Infrastructure', description: 'Automatic scaling based on demand' },
      { name: 'Global CDN & Edge Caching', description: 'Worldwide content delivery for optimal performance' },
      { name: 'High Availability (99.9% SLA)', description: 'Enterprise-grade uptime guarantee' },
    ]
  },
  {
    category: 'Security & Compliance',
    items: [
      { name: 'SOC 2 Type II Certified', description: 'Audited security controls and compliance' },
      { name: 'GDPR & CCPA Compliant', description: 'Full data privacy regulation compliance' },
      { name: 'Enterprise SSO', description: 'SAML, OAuth 2.0, and Active Directory integration' },
      { name: 'Role-Based Access Control', description: 'Granular permissions and access management' },
      { name: 'End-to-End Encryption', description: 'AES-256 encryption for data at rest and in transit' },
    ]
  },
  {
    category: 'Support & Services',
    items: [
      { name: '24/7 Technical Support', description: 'Round-the-clock expert technical assistance' },
      { name: 'Dedicated Success Manager', description: 'Personal success manager for enterprise clients' },
      { name: 'Professional Implementation', description: 'Expert-led platform setup and configuration' },
      { name: 'Training & Certification', description: 'Comprehensive training programs for your team' },
      { name: 'Custom Development', description: 'Bespoke feature development for unique requirements' },
    ]
  }
]

const competitors = [
  {
    name: 'ISP Framework',
    tagline: 'Complete ISP Platform',
    pricing: '$299/month',
    highlight: true,
    badges: ['Most Popular', 'Best Value'],
    strengths: ['All-in-one solution', 'Modern technology', 'Best support']
  },
  {
    name: 'Legacy Provider A',
    tagline: 'Traditional ISP Software',
    pricing: '$899/month',
    highlight: false,
    badges: [],
    strengths: ['Established player', 'Large customer base']
  },
  {
    name: 'Competitor B',
    tagline: 'Network Management Focus',
    pricing: '$649/month',
    highlight: false,
    badges: [],
    strengths: ['Network tools', 'Industry experience']
  },
  {
    name: 'Solution C',
    tagline: 'Basic ISP Tools',
    pricing: '$399/month',
    highlight: false,
    badges: [],
    strengths: ['Simple setup', 'Basic features']
  }
]

// Feature availability matrix
const featureMatrix = {
  'Network Monitoring & Management': [true, true, true, false],
  'Customer Self-Service Portal': [true, 'limited', true, 'limited'],
  'Automated Provisioning': [true, false, 'limited', false],
  'Multi-Tenant Architecture': [true, false, false, false],
  'API-First Design': [true, 'limited', 'limited', false],
  'AI-Powered Analytics': [true, false, false, false],
  'Real-Time Dashboard': [true, 'basic', true, 'basic'],
  'Mobile Applications': [true, false, false, false],
  'White-Label Solutions': [true, 'addon', 'addon', false],
  'Advanced Reporting': [true, 'limited', 'basic', 'basic'],
  '200+ Pre-Built Integrations': [true, 'limited', 'limited', false],
  'Webhook Support': [true, false, 'limited', false],
  'Auto-Scaling Infrastructure': [true, false, false, false],
  'Global CDN & Edge Caching': [true, false, false, false],
  'High Availability (99.9% SLA)': [true, 'basic', 'basic', false],
  'SOC 2 Type II Certified': [true, true, false, false],
  'GDPR & CCPA Compliant': [true, 'basic', 'basic', false],
  'Enterprise SSO': [true, 'addon', 'addon', false],
  'Role-Based Access Control': [true, 'basic', 'basic', 'basic'],
  'End-to-End Encryption': [true, true, 'basic', false],
  '24/7 Technical Support': [true, 'business-hours', 'business-hours', 'email'],
  'Dedicated Success Manager': [true, 'enterprise', false, false],
  'Professional Implementation': [true, 'addon', 'addon', false],
  'Training & Certification': [true, 'basic', false, false],
  'Custom Development': [true, 'addon', false, false],
}

const renderFeatureStatus = (status: boolean | string) => {
  if (status === true) {
    return <CheckCircle className="w-5 h-5 text-green-600" />
  } else if (status === false) {
    return <X className="w-5 h-5 text-red-500" />
  } else if (status === 'limited' || status === 'basic') {
    return <Minus className="w-5 h-5 text-yellow-500" />
  } else if (status === 'addon') {
    return <span className="text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded">Add-on</span>
  } else if (status === 'enterprise') {
    return <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">Enterprise</span>
  } else if (status === 'business-hours') {
    return <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">9-5</span>
  } else if (status === 'email') {
    return <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">Email</span>
  }
  return <span className="text-xs text-muted-foreground">{status}</span>
}

export function CompetitorComparison() {
  const [selectedCategory, setSelectedCategory] = useState('Core Platform')

  const currentFeatures = features.find(f => f.category === selectedCategory)?.items || []

  return (
    <div className="py-24 sm:py-32 bg-background">
      <div className="container-custom">
        {/* Section Header */}
        <div className="text-center mb-16">
          <Badge variant="secondary" className="mb-4">
            Competitive Analysis
          </Badge>
          <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl mb-6">
            Why ISPs choose us over <span className="text-gradient">the competition</span>
          </h2>
          <p className="text-lg text-muted-foreground max-w-3xl mx-auto">
            See how our platform stacks up against traditional ISP management solutions. 
            We offer more features, better technology, and superior value.
          </p>
        </div>

        {/* Quick Stats Comparison */}
        <div className="grid md:grid-cols-4 gap-6 mb-16 max-w-4xl mx-auto">
          {[
            { 
              icon: Zap, 
              metric: '15 minutes',
              label: 'Setup Time',
              comparison: 'vs 2-3 months with others'
            },
            { 
              icon: Users, 
              metric: '500+',
              label: 'Happy Customers',
              comparison: 'Growing 50% annually'
            },
            { 
              icon: Shield, 
              metric: '99.9%',
              label: 'Uptime SLA',
              comparison: 'Industry-leading reliability'
            },
            { 
              icon: Clock, 
              metric: '< 15min',
              label: 'Support Response',
              comparison: '24/7 expert assistance'
            }
          ].map((stat, index) => (
            <div key={index} className="text-center p-6 bg-muted/30 rounded-xl border border-border">
              <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center mb-4 mx-auto">
                <stat.icon className="w-6 h-6 text-primary" />
              </div>
              <div className="text-2xl font-bold text-foreground mb-1">
                {stat.metric}
              </div>
              <div className="font-semibold text-foreground mb-2">
                {stat.label}
              </div>
              <div className="text-xs text-muted-foreground">
                {stat.comparison}
              </div>
            </div>
          ))}
        </div>

        {/* Competitor Header Cards */}
        <div className="grid md:grid-cols-4 gap-4 mb-8">
          {competitors.map((competitor, index) => (
            <div 
              key={competitor.name}
              className={`relative p-6 rounded-xl border text-center ${
                competitor.highlight 
                  ? 'bg-primary/5 border-primary shadow-lg ring-2 ring-primary/20' 
                  : 'bg-muted/30 border-border'
              }`}
            >
              {competitor.highlight && (
                <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                  <Badge className="bg-primary text-primary-foreground">
                    <Crown className="w-3 h-3 mr-1" />
                    Recommended
                  </Badge>
                </div>
              )}
              
              {competitor.badges.map((badge, i) => (
                <Badge key={i} variant="secondary" className="mb-2 mr-1">
                  {badge}
                </Badge>
              ))}
              
              <h3 className={`text-lg font-bold mb-2 ${
                competitor.highlight ? 'text-primary' : 'text-foreground'
              }`}>
                {competitor.name}
              </h3>
              
              <p className="text-sm text-muted-foreground mb-3">
                {competitor.tagline}
              </p>
              
              <div className={`text-2xl font-bold mb-4 ${
                competitor.highlight ? 'text-primary' : 'text-foreground'
              }`}>
                {competitor.pricing}
              </div>
              
              <div className="space-y-1">
                {competitor.strengths.map((strength, i) => (
                  <div key={i} className="text-xs text-muted-foreground">
                    • {strength}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Category Tabs */}
        <div className="flex flex-wrap justify-center gap-2 mb-8">
          {features.map((category) => (
            <button
              key={category.category}
              onClick={() => setSelectedCategory(category.category)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                selectedCategory === category.category
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }`}
            >
              {category.category}
            </button>
          ))}
        </div>

        {/* Feature Comparison Table */}
        <div className="overflow-x-auto">
          <table className="w-full border-collapse bg-background rounded-xl border border-border shadow-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left p-4 font-semibold text-foreground min-w-[300px]">
                  {selectedCategory} Features
                </th>
                {competitors.map((competitor) => (
                  <th key={competitor.name} className="text-center p-4 font-semibold text-foreground min-w-[120px]">
                    {competitor.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {currentFeatures.map((feature, index) => (
                <tr key={feature.name} className="border-b border-border last:border-b-0 hover:bg-muted/30 transition-colors">
                  <td className="p-4">
                    <div className="font-medium text-foreground mb-1">
                      {feature.name}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {feature.description}
                    </div>
                  </td>
                  {competitors.map((_, compIndex) => (
                    <td key={compIndex} className="p-4 text-center">
                      {renderFeatureStatus(featureMatrix[feature.name]?.[compIndex] || false)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Summary Section */}
        <div className="mt-16 bg-gradient-to-r from-primary/5 via-accent/5 to-primary/5 rounded-2xl p-8 border border-primary/20">
          <div className="max-w-3xl mx-auto text-center">
            <h3 className="text-2xl font-bold text-foreground mb-4">
              The Clear Choice for Modern ISPs
            </h3>
            
            <p className="text-muted-foreground mb-8">
              While our competitors offer fragmented solutions with outdated technology, 
              we provide a comprehensive, modern platform that grows with your business.
            </p>

            <div className="grid md:grid-cols-3 gap-6 mb-8">
              <div className="text-center">
                <div className="w-12 h-12 bg-green-100 dark:bg-green-900/20 rounded-xl flex items-center justify-center mb-3 mx-auto">
                  <CheckCircle className="w-6 h-6 text-green-600" />
                </div>
                <h4 className="font-semibold text-foreground mb-2">Complete Solution</h4>
                <p className="text-sm text-muted-foreground">
                  Everything you need in one platform, not a collection of separate tools
                </p>
              </div>
              
              <div className="text-center">
                <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/20 rounded-xl flex items-center justify-center mb-3 mx-auto">
                  <Star className="w-6 h-6 text-blue-600" />
                </div>
                <h4 className="font-semibold text-foreground mb-2">Modern Technology</h4>
                <p className="text-sm text-muted-foreground">
                  Built with the latest tech stack for performance and scalability
                </p>
              </div>
              
              <div className="text-center">
                <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/20 rounded-xl flex items-center justify-center mb-3 mx-auto">
                  <Crown className="w-6 h-6 text-purple-600" />
                </div>
                <h4 className="font-semibold text-foreground mb-2">Best Value</h4>
                <p className="text-sm text-muted-foreground">
                  More features for less money, with no hidden fees or expensive add-ons
                </p>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button size="lg">
                Start Free Trial Today
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
              <Button variant="outline" size="lg">
                Schedule Competitive Demo
              </Button>
            </div>

            <div className="mt-6 text-sm text-muted-foreground">
              <strong className="text-foreground">Special Migration Offer:</strong> Free data migration 
              and setup assistance when switching from any competitor (up to $5,000 value)
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}