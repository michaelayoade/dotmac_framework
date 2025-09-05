'use client'

import { useEffect, useRef, useState } from 'react'
import { Badge } from '@/components/ui/badge'

const stats = [
  {
    value: 500,
    suffix: '+',
    label: 'ISPs Served',
    description: 'Service providers trust our platform worldwide',
    color: 'text-blue-600'
  },
  {
    value: 99.9,
    suffix: '%',
    label: 'Uptime SLA',
    description: 'Enterprise-grade reliability and availability',
    color: 'text-green-600'
  },
  {
    value: 50,
    suffix: 'M+',
    label: 'Connections Managed',
    description: 'Customer connections powered by our platform',
    color: 'text-purple-600'
  },
  {
    value: 24,
    suffix: '/7',
    label: 'Support Available',
    description: 'Round-the-clock expert technical support',
    color: 'text-orange-600'
  },
  {
    value: 80,
    suffix: '%',
    label: 'Cost Reduction',
    description: 'Average operational cost savings for clients',
    color: 'text-red-600'
  },
  {
    value: 15,
    suffix: 'min',
    label: 'Deployment Time',
    description: 'Average time to get your ISP online',
    color: 'text-indigo-600'
  }
]

function CounterAnimation({ 
  value, 
  suffix = '', 
  duration = 2000 
}: { 
  value: number
  suffix: string
  duration?: number 
}) {
  const [count, setCount] = useState(0)
  const [isVisible, setIsVisible] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !isVisible) {
          setIsVisible(true)
        }
      },
      { threshold: 0.1 }
    )

    if (ref.current) {
      observer.observe(ref.current)
    }

    return () => observer.disconnect()
  }, [isVisible])

  useEffect(() => {
    if (!isVisible) return

    let startTime: number
    let animationFrame: number

    const animate = (timestamp: number) => {
      if (!startTime) startTime = timestamp
      const progress = Math.min((timestamp - startTime) / duration, 1)
      
      // Ease-out function for smooth animation
      const easedProgress = 1 - Math.pow(1 - progress, 3)
      const currentValue = Math.floor(easedProgress * value)
      
      setCount(currentValue)

      if (progress < 1) {
        animationFrame = requestAnimationFrame(animate)
      }
    }

    animationFrame = requestAnimationFrame(animate)

    return () => {
      if (animationFrame) {
        cancelAnimationFrame(animationFrame)
      }
    }
  }, [isVisible, value, duration])

  return (
    <div ref={ref} className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground">
      {count === value ? `${value}${suffix}` : `${count}${suffix}`}
    </div>
  )
}

export function Stats() {
  return (
    <div className="py-16 sm:py-24 bg-muted/30">
      <div className="container-custom">
        {/* Section Header */}
        <div className="text-center mb-16">
          <Badge variant="secondary" className="mb-4">
            Trusted Worldwide
          </Badge>
          <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl mb-6">
            Numbers that speak for themselves
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Join hundreds of ISPs worldwide who have transformed their operations 
            with our platform. These numbers reflect our commitment to excellence.
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {stats.map((stat, index) => (
            <div 
              key={stat.label}
              className={`group text-center p-6 rounded-2xl bg-background border border-border hover:border-primary/50 transition-all duration-300 card-hover feature-card stagger-${(index % 6) + 1}`}
            >
              <div className="mb-4">
                <CounterAnimation 
                  value={stat.value} 
                  suffix={stat.suffix}
                  duration={2000 + (index * 200)} 
                />
              </div>
              
              <h3 className="text-lg font-semibold text-foreground mb-2">
                {stat.label}
              </h3>
              
              <p className="text-sm text-muted-foreground leading-relaxed">
                {stat.description}
              </p>

              {/* Decorative Element */}
              <div className="mt-4 h-1 w-12 bg-gradient-to-r from-primary/50 to-accent/50 rounded-full mx-auto group-hover:w-16 transition-all duration-300" />
            </div>
          ))}
        </div>

        {/* Additional Context */}
        <div className="mt-16 text-center">
          <div className="bg-background rounded-2xl p-8 border border-border shadow-sm max-w-4xl mx-auto">
            <div className="grid md:grid-cols-3 gap-8 text-sm">
              <div>
                <div className="text-2xl font-bold text-primary mb-2">SOC 2</div>
                <p className="text-muted-foreground">Type II Certified</p>
              </div>
              <div>
                <div className="text-2xl font-bold text-primary mb-2">GDPR</div>
                <p className="text-muted-foreground">Fully Compliant</p>
              </div>
              <div>
                <div className="text-2xl font-bold text-primary mb-2">99.95%</div>
                <p className="text-muted-foreground">Customer Satisfaction</p>
              </div>
            </div>
          </div>
        </div>

        {/* Growth Timeline */}
        <div className="mt-16">
          <div className="max-w-4xl mx-auto">
            <h3 className="text-2xl font-bold text-center text-foreground mb-8">
              Our Growth Journey
            </h3>
            
            <div className="relative">
              {/* Timeline Line */}
              <div className="absolute left-1/2 transform -translate-x-0.5 w-0.5 h-full bg-gradient-to-b from-primary to-accent" />
              
              <div className="space-y-8">
                {[
                  { year: '2020', milestone: 'Platform Launch', metric: '10 ISPs' },
                  { year: '2021', milestone: '100th Customer', metric: '1M Connections' },
                  { year: '2022', milestone: 'Global Expansion', metric: '10M Connections' },
                  { year: '2023', milestone: 'Enterprise Scale', metric: '50M Connections' },
                  { year: '2024', milestone: 'AI Integration', metric: '500+ ISPs' },
                ].map((item, index) => (
                  <div 
                    key={item.year}
                    className={`relative flex items-center ${
                      index % 2 === 0 ? 'justify-start' : 'justify-end'
                    }`}
                  >
                    {/* Timeline Node */}
                    <div className="absolute left-1/2 transform -translate-x-1/2 w-4 h-4 bg-primary rounded-full border-4 border-background shadow-sm z-10" />
                    
                    {/* Content */}
                    <div className={`w-5/12 p-4 bg-background rounded-lg border border-border shadow-sm ${
                      index % 2 === 0 ? 'mr-auto' : 'ml-auto text-right'
                    }`}>
                      <div className="text-sm font-semibold text-primary mb-1">{item.year}</div>
                      <h4 className="font-semibold text-foreground mb-1">{item.milestone}</h4>
                      <p className="text-sm text-muted-foreground">{item.metric}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}