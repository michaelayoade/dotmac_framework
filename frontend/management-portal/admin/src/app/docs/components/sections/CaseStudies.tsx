'use client'

import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { 
  ArrowRight,
  TrendingUp,
  Users,
  DollarSign,
  Clock,
  Zap,
  Network,
  BarChart3,
  CheckCircle,
  Quote,
  Play,
  Download,
  ExternalLink
} from 'lucide-react'

const caseStudies = [
  {
    id: 'fibertech',
    company: 'FiberTech Networks',
    industry: 'Fiber ISP',
    size: '15,000 customers',
    location: 'Austin, Texas',
    challenge: 'Manual provisioning and poor customer experience',
    solution: 'Complete platform automation and customer portal',
    timeline: '3 months implementation',
    featured: true,
    logo: '/images/case-studies/fibertech-logo.svg',
    heroImage: '/images/case-studies/fibertech-hero.jpg',
    results: [
      { metric: '95%', label: 'Reduction in Support Tickets', icon: Users },
      { metric: '15min', label: 'Service Provisioning Time', icon: Clock },
      { metric: '$250K', label: 'Annual Cost Savings', icon: DollarSign },
      { metric: '99.9%', label: 'Network Uptime', icon: Network }
    ],
    quote: "ISP Framework transformed our entire operation. What used to take days now happens in minutes. Our customers are happier, our team is more efficient, and our bottom line has never looked better.",
    author: {
      name: 'Sarah Chen',
      role: 'CTO',
      avatar: '/images/avatars/sarah-chen.jpg'
    },
    challenges: [
      'Manual service provisioning taking 2-3 days per customer',
      'High support ticket volume overwhelming staff',
      'No real-time visibility into network performance',
      'Billing errors causing customer churn',
      'Technician scheduling inefficiencies'
    ],
    solutionDetails: [
      'Automated service provisioning and activation',
      'Customer self-service portal with billing integration',
      'Real-time network monitoring and alerting',
      'Automated billing with error reduction systems',
      'Mobile app for field technicians'
    ],
    outcomes: [
      'Customer satisfaction increased from 72% to 96%',
      'Support team reduced from 12 to 5 agents',
      'Network issues detected 80% faster',
      'Billing accuracy improved to 99.8%',
      'Technician productivity increased 40%'
    ],
    videoTestimonial: true,
    downloadableCase: true
  },
  {
    id: 'wirelessplus',
    company: 'WirelessPlus',
    industry: 'Fixed Wireless ISP',
    size: '8,500 customers',
    location: 'Denver, Colorado',
    challenge: 'Scaling operations without increasing overhead',
    solution: 'AI-powered automation and analytics',
    timeline: '2 months implementation',
    featured: false,
    logo: '/images/case-studies/wirelessplus-logo.svg',
    heroImage: '/images/case-studies/wirelessplus-hero.jpg',
    results: [
      { metric: '300%', label: 'Customer Growth', icon: TrendingUp },
      { metric: '60%', label: 'Cost Reduction', icon: DollarSign },
      { metric: '2min', label: 'Average Response Time', icon: Clock },
      { metric: '45%', label: 'Revenue Increase', icon: BarChart3 }
    ],
    quote: "We've grown from 2,500 to 8,500 customers using the same team size. The platform's automation capabilities are incredible - it's like having a team of robots handling all the routine work.",
    author: {
      name: 'Marcus Rodriguez',
      role: 'Operations Director',
      avatar: '/images/avatars/marcus-rodriguez.jpg'
    },
    challenges: [
      'Limited scalability with existing systems',
      'Manual network monitoring requiring 24/7 staff',
      'Customer onboarding bottlenecks',
      'Lack of business intelligence and analytics',
      'High operational costs per customer'
    ],
    solutionDetails: [
      'AI-powered predictive network monitoring',
      'Automated customer onboarding workflows',
      'Real-time business intelligence dashboard',
      'Predictive analytics for capacity planning',
      'Cost optimization through automation'
    ],
    outcomes: [
      'Scaled to 3x customers with same team',
      'Proactive issue detection reduced downtime 85%',
      'Customer onboarding time reduced from 4 days to 2 hours',
      'Data-driven decisions increased revenue 45%',
      'Operational costs per customer reduced 60%'
    ],
    videoTestimonial: false,
    downloadableCase: true
  },
  {
    id: 'connectx',
    company: 'ConnectX ISP',
    industry: 'Multi-Service Provider',
    size: '25,000 customers',
    location: 'Phoenix, Arizona',
    challenge: 'Legacy system modernization',
    solution: 'Platform migration and digital transformation',
    timeline: '6 months implementation',
    featured: false,
    logo: '/images/case-studies/connectx-logo.svg',
    heroImage: '/images/case-studies/connectx-hero.jpg',
    results: [
      { metric: '50%', label: 'Faster Issue Resolution', icon: Zap },
      { metric: '90%', label: 'Customer Portal Adoption', icon: Users },
      { metric: '$500K', label: 'Annual Savings', icon: DollarSign },
      { metric: '99.95%', label: 'System Reliability', icon: Network }
    ],
    quote: "Moving from our 15-year-old legacy system to ISP Framework was the best decision we've made. The difference in capabilities and user experience is night and day.",
    author: {
      name: 'Jennifer Park',
      role: 'CEO',
      avatar: '/images/avatars/jennifer-park.jpg'
    },
    challenges: [
      '15-year-old legacy system limitations',
      'Poor integration between different tools',
      'Limited customer self-service options',
      'Difficulty accessing real-time data',
      'High maintenance costs for outdated systems'
    ],
    solutionDetails: [
      'Complete legacy system replacement',
      'Unified platform integrating all operations',
      'Modern customer portal with self-service',
      'Real-time data access and reporting',
      'Cloud-native architecture reducing maintenance'
    ],
    outcomes: [
      'Unified operations reducing complexity 70%',
      'Customer self-service adoption at 90%',
      'Real-time visibility across all operations',
      'System maintenance costs reduced 65%',
      'Team productivity increased 55%'
    ],
    videoTestimonial: true,
    downloadableCase: true
  }
]

const industryStats = [
  {
    icon: TrendingUp,
    stat: '400%',
    label: 'Average ROI',
    description: 'Clients see 4x return on investment within first year'
  },
  {
    icon: Clock,
    stat: '75%',
    label: 'Time Savings',
    description: 'Average reduction in manual operational tasks'
  },
  {
    icon: Users,
    stat: '98%',
    label: 'Customer Satisfaction',
    description: 'Average customer satisfaction score post-implementation'
  },
  {
    icon: DollarSign,
    stat: '$2.5M',
    label: 'Cost Savings',
    description: 'Combined annual savings across all clients'
  }
]

export function CaseStudies() {
  const [selectedCase, setSelectedCase] = useState(caseStudies[0])
  const [showVideoModal, setShowVideoModal] = useState(false)

  return (
    <div className="py-24 sm:py-32 bg-muted/30">
      <div className="container-custom">
        {/* Section Header */}
        <div className="text-center mb-16">
          <Badge variant="secondary" className="mb-4">
            Customer Success Stories
          </Badge>
          <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl mb-6">
            Real results from <span className="text-gradient">real ISPs</span>
          </h2>
          <p className="text-lg text-muted-foreground max-w-3xl mx-auto">
            See how ISPs like yours have transformed their operations, improved customer satisfaction, 
            and achieved significant cost savings with our platform.
          </p>
        </div>

        {/* Industry Stats */}
        <div className="grid md:grid-cols-4 gap-6 mb-16 max-w-4xl mx-auto">
          {industryStats.map((stat, index) => (
            <Card key={index} className="text-center p-6 bg-background border-border">
              <CardContent className="pt-6">
                <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center mb-4 mx-auto">
                  <stat.icon className="w-6 h-6 text-primary" />
                </div>
                <div className="text-3xl font-bold text-foreground mb-2">
                  {stat.stat}
                </div>
                <div className="font-semibold text-foreground mb-2">
                  {stat.label}
                </div>
                <div className="text-sm text-muted-foreground">
                  {stat.description}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Case Study Selector */}
        <div className="flex flex-col lg:flex-row gap-8 mb-16">
          {/* Case Study List */}
          <div className="lg:w-1/3 space-y-4">
            {caseStudies.map((caseStudy) => (
              <Card 
                key={caseStudy.id}
                className={`cursor-pointer transition-all duration-200 ${
                  selectedCase.id === caseStudy.id
                    ? 'border-primary bg-primary/5 shadow-lg'
                    : 'border-border hover:border-primary/50 hover:bg-muted/50'
                }`}
                onClick={() => setSelectedCase(caseStudy)}
              >
                <CardContent className="p-6">
                  <div className="flex items-start space-x-4">
                    <div className="w-12 h-12 bg-muted rounded-lg flex items-center justify-center flex-shrink-0">
                      <span className="text-sm font-bold text-foreground">
                        {caseStudy.company.split(' ').map(w => w[0]).join('')}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-foreground mb-1">
                        {caseStudy.company}
                      </h3>
                      <p className="text-sm text-muted-foreground mb-2">
                        {caseStudy.industry} • {caseStudy.size}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {caseStudy.challenge}
                      </p>
                      {caseStudy.featured && (
                        <Badge variant="secondary" className="mt-2">
                          Featured
                        </Badge>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Selected Case Study Detail */}
          <div className="lg:w-2/3">
            <Card className="overflow-hidden">
              {/* Hero Section */}
              <div className="relative h-48 bg-gradient-to-r from-primary/10 to-accent/10 flex items-center justify-center">
                <div className="text-center">
                  <h3 className="text-2xl font-bold text-foreground mb-2">
                    {selectedCase.company}
                  </h3>
                  <p className="text-muted-foreground">
                    {selectedCase.industry} • {selectedCase.location}
                  </p>
                </div>
                {selectedCase.videoTestimonial && (
                  <button
                    onClick={() => setShowVideoModal(true)}
                    className="absolute top-4 right-4 bg-background/80 hover:bg-background rounded-full p-3 transition-colors"
                  >
                    <Play className="w-5 h-5 text-primary" />
                  </button>
                )}
              </div>

              <CardContent className="p-8">
                {/* Results Metrics */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                  {selectedCase.results.map((result, index) => (
                    <div key={index} className="text-center p-4 bg-muted/50 rounded-lg">
                      <div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center mb-2 mx-auto">
                        <result.icon className="w-4 h-4 text-primary" />
                      </div>
                      <div className="text-xl font-bold text-foreground mb-1">
                        {result.metric}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {result.label}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Quote */}
                <div className="relative mb-8 p-6 bg-muted/30 rounded-xl">
                  <Quote className="absolute top-4 left-4 w-6 h-6 text-primary/20" />
                  <blockquote className="text-lg text-foreground pl-8 mb-4">
                    "{selectedCase.quote}"
                  </blockquote>
                  <div className="flex items-center pl-8">
                    <div className="w-12 h-12 bg-muted rounded-full flex items-center justify-center mr-3">
                      <span className="text-sm font-semibold text-foreground">
                        {selectedCase.author.name.split(' ').map(n => n[0]).join('')}
                      </span>
                    </div>
                    <div>
                      <div className="font-semibold text-foreground">
                        {selectedCase.author.name}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {selectedCase.author.role}, {selectedCase.company}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Implementation Details */}
                <div className="grid md:grid-cols-3 gap-6 mb-8">
                  {/* Challenges */}
                  <div>
                    <h4 className="font-semibold text-foreground mb-3">
                      Key Challenges
                    </h4>
                    <ul className="space-y-2">
                      {selectedCase.challenges.map((challenge, index) => (
                        <li key={index} className="text-sm text-muted-foreground flex items-start">
                          <span className="w-1.5 h-1.5 bg-red-500 rounded-full mt-2 mr-3 flex-shrink-0" />
                          {challenge}
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Solutions */}
                  <div>
                    <h4 className="font-semibold text-foreground mb-3">
                      Solutions Implemented
                    </h4>
                    <ul className="space-y-2">
                      {selectedCase.solutionDetails.map((solution, index) => (
                        <li key={index} className="text-sm text-muted-foreground flex items-start">
                          <CheckCircle className="w-4 h-4 text-green-600 mt-0.5 mr-2 flex-shrink-0" />
                          {solution}
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Outcomes */}
                  <div>
                    <h4 className="font-semibold text-foreground mb-3">
                      Key Outcomes
                    </h4>
                    <ul className="space-y-2">
                      {selectedCase.outcomes.map((outcome, index) => (
                        <li key={index} className="text-sm text-muted-foreground flex items-start">
                          <TrendingUp className="w-4 h-4 text-primary mt-0.5 mr-2 flex-shrink-0" />
                          {outcome}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Implementation Timeline */}
                <div className="mb-8 p-4 bg-muted/30 rounded-lg">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-foreground">
                      Implementation Timeline
                    </span>
                    <Badge variant="secondary">
                      {selectedCase.timeline}
                    </Badge>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex flex-col sm:flex-row gap-4">
                  {selectedCase.downloadableCase && (
                    <Button variant="outline" className="flex items-center">
                      <Download className="w-4 h-4 mr-2" />
                      Download Full Case Study
                    </Button>
                  )}
                  
                  <Button>
                    See Similar Results for Your ISP
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </Button>
                  
                  <Button variant="outline">
                    <ExternalLink className="w-4 h-4 mr-2" />
                    Visit {selectedCase.company}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* CTA Section */}
        <div className="text-center bg-background rounded-2xl p-8 border border-border">
          <h3 className="text-2xl font-bold text-foreground mb-4">
            Ready to write your own success story?
          </h3>
          <p className="text-muted-foreground mb-8 max-w-2xl mx-auto">
            Join hundreds of ISPs who have transformed their operations with our platform. 
            Schedule a demo to see how we can help you achieve similar results.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg">
              Schedule Your Demo
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
            <Button variant="outline" size="lg">
              Download All Case Studies
            </Button>
          </div>
        </div>

        {/* Video Modal */}
        {showVideoModal && (
          <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4">
            <div className="relative w-full max-w-4xl aspect-video">
              <button
                onClick={() => setShowVideoModal(false)}
                className="absolute -top-12 right-0 text-white hover:text-gray-300 transition-colors text-lg"
              >
                ✕ Close
              </button>
              <div className="w-full h-full bg-black rounded-xl overflow-hidden shadow-2xl">
                <iframe
                  src="https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=1"
                  title={`${selectedCase.company} Success Story`}
                  className="w-full h-full"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}