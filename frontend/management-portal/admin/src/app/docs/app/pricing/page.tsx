import { Metadata } from 'next'
import { Header } from '@/components/layout/Header'
import { Footer } from '@/components/layout/Footer'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { 
  CheckCircle, 
  X, 
  ArrowRight, 
  Users, 
  Zap,
  Crown,
  Shield,
  Star,
  Clock,
  Phone,
  Mail
} from 'lucide-react'

export const metadata: Metadata = {
  title: 'Pricing - ISP Framework',
  description: 'Simple, transparent pricing for ISPs of all sizes. Start free, scale as you grow.',
}

const plans = [
  {
    name: 'Starter',
    description: 'Perfect for small ISPs getting started',
    price: 'Free',
    period: 'forever',
    popular: false,
    features: [
      'Up to 100 customers',
      'Basic network monitoring',
      'Customer portal',
      'Email support',
      'API access',
      'Basic reporting',
      'Community support'
    ],
    limits: [
      '100 customers max',
      'Basic features only',
      'Email support only'
    ],
    cta: 'Start Free',
    href: '/signup?plan=starter'
  },
  {
    name: 'Professional',
    description: 'Most popular for growing ISPs',
    price: '$299',
    period: 'per month',
    popular: true,
    features: [
      'Up to 5,000 customers',
      'Advanced network automation',
      'Full customer portal',
      'Priority support',
      'Advanced API access',
      'Custom reporting',
      'Mobile apps',
      'Integrations included',
      'SLA monitoring',
      'Automated provisioning'
    ],
    limits: [],
    cta: 'Start Trial',
    href: '/signup?plan=professional'
  },
  {
    name: 'Enterprise',
    description: 'For large ISPs with complex needs',
    price: 'Custom',
    period: 'pricing',
    popular: false,
    features: [
      'Unlimited customers',
      'White-label solution',
      'Dedicated support manager',
      'Custom integrations',
      'Advanced security',
      'Custom reporting',
      'Professional services',
      'Training included',
      'SLA guarantee',
      'Custom development'
    ],
    limits: [],
    cta: 'Contact Sales',
    href: '/contact-sales'
  }
]

const enterpriseFeatures = [
  {
    icon: Shield,
    title: 'Enhanced Security',
    description: 'SOC 2 Type II, custom security controls, and compliance support'
  },
  {
    icon: Users,
    title: 'Dedicated Support',
    description: 'Named support manager and priority technical assistance'
  },
  {
    icon: Zap,
    title: 'Custom Development',
    description: 'Bespoke features and integrations tailored to your needs'
  },
  {
    icon: Crown,
    title: 'White-Label',
    description: 'Fully branded experience with your company identity'
  }
]

const faq = [
  {
    question: 'How does the free plan work?',
    answer: 'Our Starter plan is completely free forever for up to 100 customers. No credit card required, no hidden fees. Perfect for small ISPs to get started.'
  },
  {
    question: 'What happens if I exceed my plan limits?',
    answer: 'We\'ll notify you as you approach your limits and help you upgrade to the next plan. Your service won\'t be interrupted - we\'ll work with you to find the right solution.'
  },
  {
    question: 'Can I change plans anytime?',
    answer: 'Yes! You can upgrade or downgrade your plan at any time. Changes take effect at your next billing cycle, and we\'ll prorate any differences.'
  },
  {
    question: 'Do you offer custom pricing for large ISPs?',
    answer: 'Absolutely. For ISPs with over 10,000 customers or specific requirements, we offer custom pricing and features. Contact our sales team for a personalized quote.'
  },
  {
    question: 'What\'s included in support?',
    answer: 'All plans include technical support. Starter gets email support, Professional gets priority support, and Enterprise gets a dedicated support manager with SLA guarantees.'
  },
  {
    question: 'Is there a setup fee?',
    answer: 'No setup fees for any plan. We include onboarding assistance, and Enterprise customers get full implementation support at no additional cost.'
  }
]

export default function PricingPage() {
  return (
    <>
      <Header />
      <main>
        {/* Hero Section */}
        <div className="pt-32 pb-16 bg-gradient-to-br from-background via-background to-muted/20">
          <div className="container-custom text-center">
            <Badge variant="secondary" className="mb-4">
              Simple, Transparent Pricing
            </Badge>
            <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl mb-6">
              Start free, scale as you <span className="text-gradient">grow</span>
            </h1>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto mb-8">
              No hidden fees, no surprises. Choose the plan that fits your ISP's size 
              and needs. Upgrade or downgrade anytime.
            </p>
            
            {/* Pricing Toggle (Annual/Monthly) could go here */}
            <div className="flex items-center justify-center space-x-4 mb-12">
              <div className="flex items-center text-sm text-muted-foreground">
                <CheckCircle className="w-4 h-4 text-green-600 mr-2" />
                14-day free trial
              </div>
              <div className="flex items-center text-sm text-muted-foreground">
                <CheckCircle className="w-4 h-4 text-green-600 mr-2" />
                No setup fees
              </div>
              <div className="flex items-center text-sm text-muted-foreground">
                <CheckCircle className="w-4 h-4 text-green-600 mr-2" />
                Cancel anytime
              </div>
            </div>
          </div>
        </div>

        {/* Pricing Plans */}
        <div className="py-16 bg-background">
          <div className="container-custom">
            <div className="grid lg:grid-cols-3 gap-8 max-w-6xl mx-auto">
              {plans.map((plan, index) => (
                <Card 
                  key={plan.name}
                  className={`relative ${
                    plan.popular 
                      ? 'border-primary shadow-lg ring-2 ring-primary/20 scale-105' 
                      : 'border-border'
                  }`}
                >
                  {plan.popular && (
                    <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                      <Badge className="bg-primary text-primary-foreground px-4 py-1">
                        <Star className="w-3 h-3 mr-1" />
                        Most Popular
                      </Badge>
                    </div>
                  )}
                  
                  <CardHeader className="text-center pb-8">
                    <CardTitle className="text-2xl font-bold text-foreground mb-2">
                      {plan.name}
                    </CardTitle>
                    <p className="text-muted-foreground mb-6">
                      {plan.description}
                    </p>
                    
                    <div className="mb-6">
                      <div className={`text-4xl font-bold mb-1 ${
                        plan.popular ? 'text-primary' : 'text-foreground'
                      }`}>
                        {plan.price}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {plan.period}
                      </div>
                    </div>
                    
                    <Button 
                      className="w-full" 
                      variant={plan.popular ? 'default' : 'outline'}
                      size="lg"
                      asChild
                    >
                      <a href={plan.href}>
                        {plan.cta}
                        <ArrowRight className="ml-2 h-4 w-4" />
                      </a>
                    </Button>
                  </CardHeader>
                  
                  <CardContent>
                    <div className="space-y-3">
                      {plan.features.map((feature, i) => (
                        <div key={i} className="flex items-start">
                          <CheckCircle className="w-4 h-4 text-green-600 mt-0.5 mr-3 flex-shrink-0" />
                          <span className="text-sm text-foreground">{feature}</span>
                        </div>
                      ))}
                      
                      {plan.limits.map((limit, i) => (
                        <div key={i} className="flex items-start">
                          <X className="w-4 h-4 text-red-500 mt-0.5 mr-3 flex-shrink-0" />
                          <span className="text-sm text-muted-foreground">{limit}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </div>

        {/* Enterprise Features */}
        <div className="py-16 bg-muted/30">
          <div className="container-custom">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-foreground mb-4">
                Enterprise-grade features
              </h2>
              <p className="text-muted-foreground max-w-2xl mx-auto">
                Our Enterprise plan includes everything you need to scale your ISP 
                operations with confidence and security.
              </p>
            </div>
            
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
              {enterpriseFeatures.map((feature, index) => (
                <div key={index} className="text-center">
                  <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mb-4 mx-auto">
                    <feature.icon className="w-8 h-8 text-primary" />
                  </div>
                  <h3 className="text-lg font-semibold text-foreground mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* FAQ Section */}
        <div className="py-16 bg-background">
          <div className="container-custom">
            <div className="max-w-3xl mx-auto">
              <div className="text-center mb-12">
                <h2 className="text-3xl font-bold text-foreground mb-4">
                  Frequently asked questions
                </h2>
                <p className="text-muted-foreground">
                  Can't find what you're looking for? Contact our sales team.
                </p>
              </div>
              
              <div className="space-y-8">
                {faq.map((item, index) => (
                  <div key={index} className="border-b border-border pb-8 last:border-b-0">
                    <h3 className="text-lg font-semibold text-foreground mb-3">
                      {item.question}
                    </h3>
                    <p className="text-muted-foreground leading-relaxed">
                      {item.answer}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Contact Section */}
        <div className="py-16 bg-muted/30">
          <div className="container-custom">
            <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
              <Card className="p-8">
                <CardHeader className="px-0 pt-0">
                  <CardTitle className="flex items-center gap-3 text-xl">
                    <Phone className="w-6 h-6 text-primary" />
                    Sales Support
                  </CardTitle>
                </CardHeader>
                <CardContent className="px-0">
                  <p className="text-muted-foreground mb-6">
                    Need help choosing the right plan? Our sales team can help you 
                    find the perfect solution for your ISP.
                  </p>
                  <Button>
                    Schedule a Call
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </CardContent>
              </Card>
              
              <Card className="p-8">
                <CardHeader className="px-0 pt-0">
                  <CardTitle className="flex items-center gap-3 text-xl">
                    <Mail className="w-6 h-6 text-primary" />
                    Technical Questions
                  </CardTitle>
                </CardHeader>
                <CardContent className="px-0">
                  <p className="text-muted-foreground mb-6">
                    Have technical questions about features, integrations, or implementation? 
                    Our technical team is here to help.
                  </p>
                  <Button variant="outline">
                    Contact Technical Team
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>

        {/* Final CTA */}
        <div className="py-16 bg-gradient-to-r from-primary/5 via-accent/5 to-primary/5">
          <div className="container-custom text-center">
            <h2 className="text-3xl font-bold text-foreground mb-4">
              Ready to transform your ISP operations?
            </h2>
            <p className="text-muted-foreground mb-8 max-w-2xl mx-auto">
              Join hundreds of ISPs who trust our platform. Start your free trial today 
              and see the difference modern technology can make.
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
            <div className="mt-6 text-sm text-muted-foreground">
              No credit card required • 14-day free trial • Cancel anytime
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  )
}