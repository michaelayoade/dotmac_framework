'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  ArrowRight, 
  Play, 
  CheckCircle, 
  Zap,
  Clock,
  Users,
  Shield,
  Star
} from 'lucide-react'

const benefits = [
  {
    icon: Zap,
    title: 'Quick Setup',
    description: 'Get your ISP online in 15 minutes'
  },
  {
    icon: Shield,
    title: 'Enterprise Security',
    description: 'SOC 2 certified with end-to-end encryption'
  },
  {
    icon: Users,
    title: 'Expert Support',
    description: '24/7 technical support from ISP specialists'
  }
]

const guarantees = [
  '14-day free trial',
  '99.9% uptime SLA',
  'No setup fees',
  'Cancel anytime'
]

const urgencyFactors = [
  { 
    label: 'Limited Time Offer',
    value: '50% off first 3 months',
    highlight: true
  },
  {
    label: 'Implementation Bonus',
    value: 'Free migration & setup ($5,000 value)'
  },
  {
    label: 'Exclusive Access',
    value: 'Early access to new features'
  }
]

export function CTA() {
  const [isVideoPlaying, setIsVideoPlaying] = useState(false)

  return (
    <div className="relative py-24 sm:py-32 bg-gradient-to-br from-primary/5 via-background to-accent/5 overflow-hidden">
      {/* Background Elements */}
      <div className="absolute inset-0 bg-grid-pattern opacity-5" />
      <div className="absolute top-20 left-10 w-72 h-72 bg-primary/10 rounded-full blur-3xl animate-pulse" />
      <div className="absolute bottom-20 right-10 w-96 h-96 bg-accent/10 rounded-full blur-3xl animate-pulse animation-delay-2000" />
      
      <div className="relative container-custom">
        {/* Urgency Banner */}
        <div className="text-center mb-8">
          <Badge variant="secondary" className="bg-primary text-primary-foreground px-4 py-2 animate-pulse">
            <Star className="w-4 h-4 mr-2" />
            Limited Time: Launch Special Pricing Available
          </Badge>
        </div>

        {/* Main CTA Content */}
        <div className="max-w-4xl mx-auto text-center mb-16">
          <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-5xl lg:text-6xl mb-6">
            Ready to transform your{' '}
            <span className="text-gradient">ISP operations?</span>
          </h2>
          
          <p className="text-xl text-muted-foreground mb-8 max-w-3xl mx-auto leading-relaxed">
            Join 500+ ISPs who have already revolutionized their operations with our platform. 
            Start your free trial today and see results within hours, not months.
          </p>

          {/* Key Benefits */}
          <div className="grid md:grid-cols-3 gap-6 mb-12">
            {benefits.map((benefit, index) => (
              <div 
                key={benefit.title}
                className={`flex flex-col items-center p-6 rounded-2xl bg-background/50 border border-border backdrop-blur-sm hover:bg-background transition-all duration-200 stagger-${index + 1}`}
              >
                <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center mb-4">
                  <benefit.icon className="w-6 h-6 text-primary" />
                </div>
                <h3 className="text-lg font-semibold text-foreground mb-2">
                  {benefit.title}
                </h3>
                <p className="text-sm text-muted-foreground text-center">
                  {benefit.description}
                </p>
              </div>
            ))}
          </div>

          {/* Primary CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-8">
            <Button asChild size="lg" className="px-8 py-6 text-lg font-semibold shadow-lg hover:shadow-xl transition-shadow">
              <Link href="/demo">
                Start Free Trial Now
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
            </Button>
            
            <Button
              variant="outline"
              size="lg"
              className="px-8 py-6 text-lg font-semibold group bg-background/50 backdrop-blur-sm"
              onClick={() => setIsVideoPlaying(true)}
            >
              <Play className="mr-2 h-5 w-5 group-hover:scale-110 transition-transform" />
              Watch 5-Min Demo
            </Button>
          </div>

          {/* Guarantees */}
          <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-muted-foreground mb-12">
            {guarantees.map((guarantee, index) => (
              <div key={guarantee} className="flex items-center">
                <CheckCircle className="w-4 h-4 text-green-600 mr-2" />
                {guarantee}
              </div>
            ))}
          </div>
        </div>

        {/* Urgency Factors */}
        <div className="max-w-4xl mx-auto mb-16">
          <div className="bg-background/80 backdrop-blur-sm rounded-2xl border border-border p-8 shadow-lg">
            <div className="text-center mb-8">
              <h3 className="text-2xl font-bold text-foreground mb-2">
                🚀 Launch Special - Act Fast!
              </h3>
              <p className="text-muted-foreground">
                Exclusive offers for the first 100 ISPs to join our platform
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
              {urgencyFactors.map((factor, index) => (
                <div 
                  key={factor.label}
                  className={`p-4 rounded-xl border text-center ${
                    factor.highlight 
                      ? 'bg-primary/10 border-primary/30' 
                      : 'bg-muted/30 border-border'
                  }`}
                >
                  <div className={`text-sm font-medium mb-1 ${
                    factor.highlight ? 'text-primary' : 'text-muted-foreground'
                  }`}>
                    {factor.label}
                  </div>
                  <div className={`font-bold ${
                    factor.highlight ? 'text-primary text-lg' : 'text-foreground'
                  }`}>
                    {factor.value}
                  </div>
                </div>
              ))}
            </div>

            <div className="text-center mt-8">
              <div className="inline-flex items-center text-sm text-muted-foreground">
                <Clock className="w-4 h-4 mr-2" />
                Offer expires in: <span className="font-mono font-bold ml-2 text-foreground">23:47:12</span>
              </div>
            </div>
          </div>
        </div>

        {/* Secondary CTAs */}
        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto mb-16">
          {/* Talk to Sales */}
          <div className="bg-background/80 backdrop-blur-sm rounded-2xl border border-border p-8 text-center hover:bg-background transition-colors">
            <h4 className="text-xl font-bold text-foreground mb-4">
              Talk to Sales
            </h4>
            <p className="text-muted-foreground mb-6">
              Need a custom solution? Our ISP specialists will design the perfect setup for your business.
            </p>
            <Button variant="outline" className="w-full" asChild>
              <Link href="/contact-sales">
                Schedule Consultation
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>

          {/* Documentation */}
          <div className="bg-background/80 backdrop-blur-sm rounded-2xl border border-border p-8 text-center hover:bg-background transition-colors">
            <h4 className="text-xl font-bold text-foreground mb-4">
              Explore Documentation
            </h4>
            <p className="text-muted-foreground mb-6">
              Technical decision maker? Dive deep into our APIs, architecture, and integration guides.
            </p>
            <Button variant="outline" className="w-full" asChild>
              <Link href="/docs">
                View Documentation
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>

        {/* Social Proof Footer */}
        <div className="text-center">
          <div className="flex items-center justify-center space-x-8 text-sm text-muted-foreground mb-4">
            <div className="flex items-center">
              <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse" />
              <span>47 ISPs signed up this week</span>
            </div>
            <div className="flex items-center">
              <Star className="w-4 h-4 text-yellow-500 mr-1" />
              <span>4.9/5 average rating</span>
            </div>
          </div>
          <p className="text-xs text-muted-foreground max-w-2xl mx-auto">
            By starting your trial, you agree to our{' '}
            <Link href="/terms" className="text-primary hover:underline">Terms of Service</Link>
            {' '}and{' '}
            <Link href="/privacy" className="text-primary hover:underline">Privacy Policy</Link>.
            No credit card required for trial.
          </p>
        </div>
      </div>

      {/* Video Modal */}
      {isVideoPlaying && (
        <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4">
          <div className="relative w-full max-w-4xl aspect-video">
            <button
              onClick={() => setIsVideoPlaying(false)}
              className="absolute -top-12 right-0 text-white hover:text-gray-300 transition-colors text-lg"
            >
              ✕ Close
            </button>
            <div className="w-full h-full bg-black rounded-xl overflow-hidden shadow-2xl">
              <iframe
                src="https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=1"
                title="ISP Framework Demo"
                className="w-full h-full"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}