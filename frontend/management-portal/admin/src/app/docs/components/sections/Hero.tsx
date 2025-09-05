'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  Play, 
  ArrowRight, 
  Network, 
  Users, 
  BarChart3, 
  Shield,
  Zap,
  CheckCircle
} from 'lucide-react'

const features = [
  'Network Automation',
  'Customer Management',
  'Real-time Analytics',
  'Security & Compliance'
]

const stats = [
  { value: '500+', label: 'ISPs Trust Us' },
  { value: '99.9%', label: 'Uptime SLA' },
  { value: '50M+', label: 'Connections Managed' },
  { value: '24/7', label: 'Support Available' }
]

export function Hero() {
  const [isVideoPlaying, setIsVideoPlaying] = useState(false)

  return (
    <div className="relative overflow-hidden bg-gradient-to-br from-background via-background to-muted/20">
      {/* Background Pattern */}
      <div className="absolute inset-0 bg-grid-pattern opacity-5" />
      
      {/* Floating Elements */}
      <div className="absolute top-20 left-10 w-72 h-72 bg-primary/10 rounded-full blur-3xl animate-pulse" />
      <div className="absolute bottom-20 right-10 w-96 h-96 bg-accent/10 rounded-full blur-3xl animate-pulse animation-delay-2000" />
      
      <div className="relative pt-32 pb-16 sm:pb-24">
        <div className="container-custom">
          <div className="mx-auto max-w-4xl text-center">
            {/* Announcement Badge */}
            <div className="mb-8 hero-title">
              <Badge variant="secondary" className="px-4 py-2 text-sm font-medium">
                <Zap className="mr-2 h-4 w-4" />
                New: AI-Powered Network Optimization Available
                <ArrowRight className="ml-2 h-4 w-4" />
              </Badge>
            </div>

            {/* Main Headline */}
            <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-6xl lg:text-7xl hero-title">
              Transform Your{' '}
              <span className="text-gradient">ISP Operations</span>{' '}
              with Next-Gen Automation
            </h1>

            {/* Subtitle */}
            <p className="mt-6 text-lg leading-8 text-muted-foreground max-w-2xl mx-auto hero-subtitle">
              The complete ISP management platform that automates network operations, 
              streamlines customer experiences, and scales your business with enterprise-grade reliability.
            </p>

            {/* Feature Pills */}
            <div className="mt-8 flex flex-wrap justify-center gap-3 hero-subtitle">
              {features.map((feature, index) => (
                <div
                  key={feature}
                  className="flex items-center px-4 py-2 bg-muted/50 rounded-full text-sm font-medium text-foreground border border-border/50"
                >
                  <CheckCircle className="mr-2 h-4 w-4 text-primary" />
                  {feature}
                </div>
              ))}
            </div>

            {/* CTAs */}
            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4 hero-cta">
              <Button asChild size="lg" className="px-8 py-6 text-base font-semibold">
                <Link href="/demo">
                  Start Free Trial
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Link>
              </Button>
              
              <Button
                variant="outline"
                size="lg"
                className="px-8 py-6 text-base font-semibold group"
                onClick={() => setIsVideoPlaying(true)}
              >
                <Play className="mr-2 h-5 w-5 group-hover:scale-110 transition-transform" />
                Watch Demo
              </Button>
            </div>

            {/* Trust Indicators */}
            <div className="mt-16 hero-cta">
              <p className="text-sm text-muted-foreground mb-6">
                Trusted by ISPs worldwide
              </p>
              
              <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
                {stats.map((stat, index) => (
                  <div key={stat.label} className="text-center">
                    <div className="text-2xl sm:text-3xl font-bold text-foreground">
                      {stat.value}
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">
                      {stat.label}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Hero Visual */}
          <div className="mt-20 relative max-w-6xl mx-auto">
            <div className="relative rounded-2xl overflow-hidden shadow-hero bg-gradient-to-r from-primary/10 to-accent/10 backdrop-blur-sm border border-border/50">
              {!isVideoPlaying ? (
                <div className="aspect-video flex items-center justify-center bg-gradient-to-br from-muted/50 to-muted group cursor-pointer" onClick={() => setIsVideoPlaying(true)}>
                  <div className="relative">
                    <div className="absolute inset-0 bg-primary/20 rounded-full blur-2xl group-hover:blur-xl transition-all" />
                    <Button size="lg" variant="secondary" className="relative">
                      <Play className="mr-2 h-6 w-6" />
                      Play Demo Video
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="aspect-video">
                  <iframe
                    src="https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=1"
                    title="ISP Framework Demo"
                    className="w-full h-full"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                  />
                </div>
              )}
              
              {/* Overlay Dashboard Preview */}
              <div className="absolute -bottom-4 -right-4 w-64 h-40 bg-background rounded-lg shadow-lg border border-border p-4 hidden lg:block">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-primary rounded flex items-center justify-center">
                      <BarChart3 className="w-3 h-3 text-primary-foreground" />
                    </div>
                    <span className="text-sm font-semibold">Live Dashboard</span>
                  </div>
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                    <span className="text-xs text-muted-foreground">Live</span>
                  </div>
                </div>
                
                <div className="space-y-2">
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Network Status</span>
                    <span className="text-green-600 font-medium">Optimal</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Active Users</span>
                    <span className="font-medium">12,847</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Bandwidth Usage</span>
                    <span className="font-medium">67%</span>
                  </div>
                  
                  <div className="mt-2 h-16 bg-muted/50 rounded flex items-end justify-between px-2 pb-2">
                    {Array.from({ length: 12 }).map((_, i) => (
                      <div
                        key={i}
                        className="w-2 bg-primary rounded-t"
                        style={{ height: `${Math.random() * 100 + 20}%` }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}