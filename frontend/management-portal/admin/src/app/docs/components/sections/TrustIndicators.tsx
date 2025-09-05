'use client'

import { Badge } from '@/components/ui/badge'
import { CheckCircle, Star } from 'lucide-react'

const logos = [
  { name: 'TechCorp ISP', logo: '/images/logos/techcorp.svg' },
  { name: 'NetConnect', logo: '/images/logos/netconnect.svg' },
  { name: 'FiberLink', logo: '/images/logos/fiberlink.svg' },
  { name: 'WirelessPlus', logo: '/images/logos/wirelessplus.svg' },
  { name: 'BroadbandPro', logo: '/images/logos/broadbandpro.svg' },
  { name: 'ConnectX', logo: '/images/logos/connectx.svg' },
  { name: 'NetSphere', logo: '/images/logos/netsphere.svg' },
  { name: 'DataFlow ISP', logo: '/images/logos/dataflow.svg' },
]

const certifications = [
  {
    name: 'SOC 2 Type II',
    description: 'Security & Compliance',
    icon: '/images/certifications/soc2.svg',
    verified: true
  },
  {
    name: 'ISO 27001',
    description: 'Information Security',
    icon: '/images/certifications/iso27001.svg',
    verified: true
  },
  {
    name: 'GDPR Compliant',
    description: 'Data Protection',
    icon: '/images/certifications/gdpr.svg',
    verified: true
  },
  {
    name: 'HIPAA Ready',
    description: 'Healthcare Compliance',
    icon: '/images/certifications/hipaa.svg',
    verified: true
  }
]

const awards = [
  {
    title: 'ISP Platform of the Year',
    organization: 'TelecomTech Awards 2024',
    rating: 5
  },
  {
    title: 'Best Network Management Solution',
    organization: 'Industry Excellence Awards',
    rating: 5
  },
  {
    title: 'Innovation in ISP Technology',
    organization: 'Global Telecom Summit',
    rating: 5
  }
]

export function TrustIndicators() {
  return (
    <div className="py-16 bg-background border-b border-border">
      <div className="container-custom">
        {/* Customer Logos */}
        <div className="text-center mb-12">
          <Badge variant="secondary" className="mb-4">
            Trusted by Industry Leaders
          </Badge>
          <p className="text-muted-foreground mb-8">
            Join 500+ ISPs worldwide who trust our platform for their critical operations
          </p>
          
          {/* Logo Carousel */}
          <div className="relative overflow-hidden">
            <div className="flex animate-scroll space-x-12 items-center justify-center opacity-60 hover:opacity-90 transition-opacity">
              {/* First set */}
              {logos.map((company, index) => (
                <div 
                  key={`${company.name}-1`}
                  className="flex-shrink-0 w-32 h-16 flex items-center justify-center grayscale hover:grayscale-0 transition-all duration-300"
                >
                  {/* Placeholder logo - in production, use actual logos */}
                  <div className="w-24 h-8 bg-muted rounded flex items-center justify-center text-xs font-semibold text-muted-foreground">
                    {company.name}
                  </div>
                </div>
              ))}
              {/* Duplicate set for seamless loop */}
              {logos.map((company, index) => (
                <div 
                  key={`${company.name}-2`}
                  className="flex-shrink-0 w-32 h-16 flex items-center justify-center grayscale hover:grayscale-0 transition-all duration-300"
                >
                  <div className="w-24 h-8 bg-muted rounded flex items-center justify-center text-xs font-semibold text-muted-foreground">
                    {company.name}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Trust Indicators Grid */}
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Certifications */}
          <div className="bg-muted/30 rounded-2xl p-6 border border-border">
            <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center">
              <CheckCircle className="w-5 h-5 text-green-600 mr-2" />
              Security & Compliance
            </h3>
            <div className="space-y-3">
              {certifications.map((cert) => (
                <div key={cert.name} className="flex items-center justify-between p-3 bg-background rounded-lg">
                  <div className="flex items-center">
                    <div className="w-8 h-8 bg-muted rounded flex items-center justify-center mr-3">
                      <CheckCircle className="w-4 h-4 text-green-600" />
                    </div>
                    <div>
                      <div className="font-medium text-foreground text-sm">{cert.name}</div>
                      <div className="text-xs text-muted-foreground">{cert.description}</div>
                    </div>
                  </div>
                  {cert.verified && (
                    <Badge variant="secondary" className="text-xs">
                      Verified
                    </Badge>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Awards & Recognition */}
          <div className="bg-muted/30 rounded-2xl p-6 border border-border">
            <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center">
              <Star className="w-5 h-5 text-yellow-600 mr-2" />
              Awards & Recognition
            </h3>
            <div className="space-y-4">
              {awards.map((award, index) => (
                <div key={index} className="p-3 bg-background rounded-lg">
                  <h4 className="font-medium text-foreground text-sm mb-1">
                    {award.title}
                  </h4>
                  <p className="text-xs text-muted-foreground mb-2">
                    {award.organization}
                  </p>
                  <div className="flex items-center">
                    {Array.from({ length: award.rating }).map((_, i) => (
                      <Star key={i} className="w-3 h-3 text-yellow-500 fill-current" />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Performance Metrics */}
          <div className="bg-muted/30 rounded-2xl p-6 border border-border">
            <h3 className="text-lg font-semibold text-foreground mb-4">
              Performance Guarantee
            </h3>
            <div className="space-y-4">
              <div className="p-3 bg-background rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-foreground">Uptime SLA</span>
                  <span className="text-sm font-bold text-green-600">99.9%</span>
                </div>
                <div className="w-full bg-muted rounded-full h-2">
                  <div className="bg-green-600 h-2 rounded-full" style={{ width: '99.9%' }} />
                </div>
              </div>

              <div className="p-3 bg-background rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-foreground">Customer Satisfaction</span>
                  <span className="text-sm font-bold text-blue-600">99.5%</span>
                </div>
                <div className="w-full bg-muted rounded-full h-2">
                  <div className="bg-blue-600 h-2 rounded-full" style={{ width: '99.5%' }} />
                </div>
              </div>

              <div className="p-3 bg-background rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-foreground">Support Response</span>
                  <span className="text-sm font-bold text-purple-600">&lt; 15min</span>
                </div>
                <div className="w-full bg-muted rounded-full h-2">
                  <div className="bg-purple-600 h-2 rounded-full" style={{ width: '95%' }} />
                </div>
              </div>

              <div className="mt-4 p-3 bg-gradient-to-r from-primary/10 to-accent/10 rounded-lg border border-primary/20">
                <div className="text-xs text-center text-muted-foreground">
                  Backed by our{' '}
                  <span className="font-semibold text-foreground">
                    99.9% Uptime Guarantee
                  </span>{' '}
                  with SLA credits
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Trust Statement */}
        <div className="mt-12 text-center">
          <div className="max-w-3xl mx-auto p-6 bg-gradient-to-r from-primary/5 via-accent/5 to-primary/5 rounded-2xl border border-border">
            <div className="flex items-center justify-center space-x-6 text-sm">
              <div className="flex items-center">
                <CheckCircle className="w-4 h-4 text-green-600 mr-2" />
                <span className="text-muted-foreground">Enterprise Security</span>
              </div>
              <div className="flex items-center">
                <CheckCircle className="w-4 h-4 text-green-600 mr-2" />
                <span className="text-muted-foreground">24/7 Support</span>
              </div>
              <div className="flex items-center">
                <CheckCircle className="w-4 h-4 text-green-600 mr-2" />
                <span className="text-muted-foreground">No Vendor Lock-in</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Custom CSS for logo animation */}
      <style jsx>{`
        @keyframes scroll {
          0% {
            transform: translateX(0);
          }
          100% {
            transform: translateX(-50%);
          }
        }
        
        .animate-scroll {
          animation: scroll 30s linear infinite;
        }
        
        .animate-scroll:hover {
          animation-play-state: paused;
        }
      `}</style>
    </div>
  )
}