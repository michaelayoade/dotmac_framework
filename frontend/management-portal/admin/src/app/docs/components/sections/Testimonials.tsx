'use client'

import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Star, Quote, ChevronLeft, ChevronRight, Play } from 'lucide-react'

const testimonials = [
  {
    id: 1,
    content: "ISP Framework transformed our operations completely. We went from manual processes to full automation in just weeks. The platform's network monitoring capabilities have reduced our downtime by 95%, and our customer satisfaction scores have never been higher.",
    author: "Sarah Chen",
    role: "CTO",
    company: "FiberTech Networks",
    location: "Austin, TX",
    avatar: "/images/avatars/sarah-chen.jpg",
    rating: 5,
    metrics: {
      uptime: "99.9%",
      costSaving: "40%",
      resolution: "85% faster"
    },
    videoTestimonial: true
  },
  {
    id: 2,
    content: "The customer portal alone has saved us countless hours. Our subscribers can now manage everything themselves - from billing to support tickets. The automated provisioning means new customers are online within minutes instead of days.",
    author: "Marcus Rodriguez",
    role: "Operations Director",
    company: "WirelessPlus",
    location: "Denver, CO",
    avatar: "/images/avatars/marcus-rodriguez.jpg",
    rating: 5,
    metrics: {
      customerSatisfaction: "95%",
      supportTickets: "60% reduction",
      provisioning: "15 minutes"
    }
  },
  {
    id: 3,
    content: "What impressed me most is the scalability. We started with 500 customers and now serve over 15,000 without any platform limitations. The analytics dashboard gives us insights we never had before, helping us make data-driven decisions.",
    author: "Jennifer Park",
    role: "CEO",
    company: "ConnectX ISP",
    location: "Phoenix, AZ",
    avatar: "/images/avatars/jennifer-park.jpg",
    rating: 5,
    metrics: {
      growth: "3000% scale",
      insights: "Real-time",
      roi: "300%"
    }
  },
  {
    id: 4,
    content: "The support team is incredible. They don't just fix issues - they help us optimize our entire operation. The platform has evolved with our needs, and new features are constantly being added based on real ISP feedback.",
    author: "David Kumar",
    role: "Network Engineer",
    company: "BroadbandPro",
    location: "Seattle, WA",
    avatar: "/images/avatars/david-kumar.jpg",
    rating: 5,
    metrics: {
      support: "< 15 min",
      optimization: "Ongoing",
      updates: "Monthly"
    }
  },
  {
    id: 5,
    content: "ROI was immediate. Within the first month, we'd already saved more in operational costs than the platform fee. The automation tools handle routine tasks, letting our team focus on strategic growth initiatives.",
    author: "Lisa Thompson",
    role: "CFO",
    company: "NetSphere",
    location: "Miami, FL",
    avatar: "/images/avatars/lisa-thompson.jpg",
    rating: 5,
    metrics: {
      roi: "Immediate",
      savings: "$50k/month",
      efficiency: "300%"
    }
  },
  {
    id: 6,
    content: "Security was our biggest concern when evaluating platforms. ISP Framework exceeded every requirement - SOC 2 compliance, GDPR readiness, and enterprise-grade encryption. Our auditors were impressed.",
    author: "Robert Kim",
    role: "Security Officer",
    company: "SecureNet ISP",
    location: "Boston, MA",
    avatar: "/images/avatars/robert-kim.jpg",
    rating: 5,
    metrics: {
      compliance: "SOC 2 Type II",
      security: "256-bit",
      audits: "100% pass"
    }
  }
]

const companyLogos = [
  "FiberTech Networks",
  "WirelessPlus",
  "ConnectX ISP",
  "BroadbandPro", 
  "NetSphere",
  "SecureNet ISP"
]

export function Testimonials() {
  const [activeTestimonial, setActiveTestimonial] = useState(0)
  const [showVideoModal, setShowVideoModal] = useState(false)

  const nextTestimonial = () => {
    setActiveTestimonial((prev) => (prev + 1) % testimonials.length)
  }

  const prevTestimonial = () => {
    setActiveTestimonial((prev) => (prev - 1 + testimonials.length) % testimonials.length)
  }

  const currentTestimonial = testimonials[activeTestimonial]

  return (
    <div className="py-24 sm:py-32 bg-muted/30">
      <div className="container-custom">
        {/* Section Header */}
        <div className="text-center mb-16">
          <Badge variant="secondary" className="mb-4">
            Customer Success Stories
          </Badge>
          <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl mb-6">
            Loved by ISPs worldwide
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Don't just take our word for it. See how ISPs like yours have transformed 
            their operations and achieved unprecedented growth with our platform.
          </p>
        </div>

        {/* Main Testimonial */}
        <div className="max-w-6xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center mb-16">
            {/* Testimonial Content */}
            <div className="space-y-8">
              <div className="relative">
                <Quote className="absolute -top-4 -left-4 w-8 h-8 text-primary/20" />
                <blockquote className="text-xl leading-relaxed text-foreground pl-8">
                  "{currentTestimonial.content}"
                </blockquote>
              </div>

              <div className="flex items-center space-x-4">
                <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center">
                  <span className="text-lg font-semibold text-foreground">
                    {currentTestimonial.author.split(' ').map(n => n[0]).join('')}
                  </span>
                </div>
                <div>
                  <div className="font-semibold text-foreground text-lg">
                    {currentTestimonial.author}
                  </div>
                  <div className="text-muted-foreground">
                    {currentTestimonial.role} at {currentTestimonial.company}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {currentTestimonial.location}
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-1">
                {Array.from({ length: currentTestimonial.rating }).map((_, i) => (
                  <Star key={i} className="w-5 h-5 text-yellow-500 fill-current" />
                ))}
                <span className="ml-2 text-sm text-muted-foreground">
                  {currentTestimonial.rating}.0/5
                </span>
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-3 gap-4 pt-6 border-t border-border">
                {Object.entries(currentTestimonial.metrics).map(([key, value]) => (
                  <div key={key} className="text-center">
                    <div className="text-2xl font-bold text-primary mb-1">
                      {value}
                    </div>
                    <div className="text-sm text-muted-foreground capitalize">
                      {key.replace(/([A-Z])/g, ' $1').toLowerCase()}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Video/Image Section */}
            <div className="relative">
              <div className="aspect-square rounded-2xl overflow-hidden bg-gradient-to-br from-primary/10 to-accent/10 border border-border">
                {currentTestimonial.videoTestimonial ? (
                  <div 
                    className="w-full h-full flex items-center justify-center cursor-pointer group bg-muted hover:bg-muted/80 transition-colors"
                    onClick={() => setShowVideoModal(true)}
                  >
                    <div className="text-center">
                      <div className="w-20 h-20 bg-primary rounded-full flex items-center justify-center mb-4 mx-auto group-hover:scale-110 transition-transform">
                        <Play className="w-8 h-8 text-primary-foreground ml-1" />
                      </div>
                      <p className="text-foreground font-semibold">Watch Video Testimonial</p>
                      <p className="text-sm text-muted-foreground">2:30 minutes</p>
                    </div>
                  </div>
                ) : (
                  <div className="w-full h-full bg-muted flex items-center justify-center">
                    <div className="text-center text-muted-foreground">
                      <div className="w-24 h-24 bg-background rounded-full flex items-center justify-center mb-4 mx-auto">
                        <span className="text-2xl font-bold">
                          {currentTestimonial.author.split(' ').map(n => n[0]).join('')}
                        </span>
                      </div>
                      <p className="font-semibold">{currentTestimonial.author}</p>
                      <p className="text-sm">{currentTestimonial.company}</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Navigation */}
          <div className="flex items-center justify-between">
            <Button
              variant="outline"
              size="lg"
              onClick={prevTestimonial}
              className="flex items-center gap-2"
            >
              <ChevronLeft className="w-4 h-4" />
              Previous
            </Button>

            <div className="flex items-center space-x-2">
              {testimonials.map((_, index) => (
                <button
                  key={index}
                  onClick={() => setActiveTestimonial(index)}
                  className={`w-3 h-3 rounded-full transition-colors ${
                    index === activeTestimonial 
                      ? 'bg-primary' 
                      : 'bg-muted hover:bg-muted-foreground/20'
                  }`}
                />
              ))}
            </div>

            <Button
              variant="outline"
              size="lg"
              onClick={nextTestimonial}
              className="flex items-center gap-2"
            >
              Next
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Company Logos */}
        <div className="mt-20">
          <p className="text-center text-sm text-muted-foreground mb-8">
            Trusted by these companies and 500+ more
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-8 opacity-60">
            {companyLogos.map((company, index) => (
              <div 
                key={company}
                className="flex items-center justify-center p-4 bg-background rounded-lg border border-border hover:opacity-100 transition-opacity"
              >
                <div className="text-xs font-semibold text-muted-foreground text-center">
                  {company}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Additional Social Proof */}
        <div className="mt-16 grid md:grid-cols-3 gap-8">
          <div className="text-center p-6 bg-background rounded-2xl border border-border">
            <div className="text-3xl font-bold text-primary mb-2">500+</div>
            <p className="text-muted-foreground">Happy Customers</p>
          </div>
          <div className="text-center p-6 bg-background rounded-2xl border border-border">
            <div className="text-3xl font-bold text-primary mb-2">4.9/5</div>
            <p className="text-muted-foreground">Average Rating</p>
          </div>
          <div className="text-center p-6 bg-background rounded-2xl border border-border">
            <div className="text-3xl font-bold text-primary mb-2">99.5%</div>
            <p className="text-muted-foreground">Customer Satisfaction</p>
          </div>
        </div>
      </div>

      {/* Video Modal */}
      {showVideoModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="relative w-full max-w-4xl aspect-video">
            <button
              onClick={() => setShowVideoModal(false)}
              className="absolute -top-10 right-0 text-white hover:text-muted-foreground transition-colors"
            >
              <span className="sr-only">Close</span>
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
            <div className="w-full h-full bg-black rounded-lg overflow-hidden">
              <iframe
                src="https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=1"
                title="Customer Testimonial"
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