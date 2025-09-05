'use client'

import { useState, useEffect } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Slider } from '@/components/ui/slider'
import { 
  Calculator,
  TrendingUp,
  DollarSign,
  Clock,
  Users,
  Zap,
  ArrowRight,
  CheckCircle,
  Target
} from 'lucide-react'

interface ROIInputs {
  customers: number
  avgTicketCost: number
  technicianHours: number
  downtimeHours: number
  supportTickets: number
}

interface ROISavings {
  operationalSavings: number
  technicianSavings: number
  downtimeSavings: number
  supportSavings: number
  totalMonthlySavings: number
  totalYearlySavings: number
  roiPercentage: number
  paybackPeriod: number
}

const platformCost = 299 // Monthly platform cost

export function ROICalculator() {
  const [inputs, setInputs] = useState<ROIInputs>({
    customers: 1000,
    avgTicketCost: 50,
    technicianHours: 160,
    downtimeHours: 8,
    supportTickets: 200
  })

  const [showResults, setShowResults] = useState(false)
  const [savings, setSavings] = useState<ROISavings>({} as ROISavings)

  const calculateROI = (inputs: ROIInputs): ROISavings => {
    // Operational efficiency savings (20% reduction in manual tasks)
    const operationalSavings = (inputs.customers * 2) * 0.2 // $2 per customer saved through automation
    
    // Technician time savings (30% efficiency improvement)
    const technicianSavings = (inputs.technicianHours * 35) * 0.3 // $35/hour, 30% time saved
    
    // Downtime cost savings (80% reduction in downtime)
    const downtimeSavings = (inputs.downtimeHours * inputs.customers * 5) * 0.8 // $5 per customer per hour
    
    // Support ticket reduction (60% fewer tickets)
    const supportSavings = (inputs.supportTickets * inputs.avgTicketCost) * 0.6
    
    const totalMonthlySavings = operationalSavings + technicianSavings + downtimeSavings + supportSavings
    const totalYearlySavings = totalMonthlySavings * 12
    const netMonthlySavings = totalMonthlySavings - platformCost
    const roiPercentage = ((netMonthlySavings * 12) / (platformCost * 12)) * 100
    const paybackPeriod = platformCost / totalMonthlySavings

    return {
      operationalSavings,
      technicianSavings,
      downtimeSavings,
      supportSavings,
      totalMonthlySavings,
      totalYearlySavings,
      roiPercentage,
      paybackPeriod
    }
  }

  useEffect(() => {
    setSavings(calculateROI(inputs))
  }, [inputs])

  const handleInputChange = (key: keyof ROIInputs, value: number[]) => {
    setInputs(prev => ({ ...prev, [key]: value[0] }))
  }

  return (
    <div className="py-24 sm:py-32 bg-muted/30">
      <div className="container-custom">
        {/* Section Header */}
        <div className="text-center mb-16">
          <Badge variant="secondary" className="mb-4">
            ROI Calculator
          </Badge>
          <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl mb-6">
            Calculate your <span className="text-gradient">potential savings</span>
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            See exactly how much your ISP can save with our platform. 
            Adjust the parameters below to match your current operations.
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-12 max-w-6xl mx-auto">
          {/* Input Controls */}
          <Card className="p-8">
            <CardHeader className="px-0 pt-0">
              <CardTitle className="flex items-center gap-3">
                <Calculator className="w-6 h-6 text-primary" />
                Your ISP Parameters
              </CardTitle>
            </CardHeader>
            <CardContent className="px-0 space-y-8">
              {/* Number of Customers */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <label className="text-sm font-medium text-foreground flex items-center gap-2">
                    <Users className="w-4 h-4" />
                    Number of Customers
                  </label>
                  <span className="text-lg font-bold text-primary">
                    {inputs.customers.toLocaleString()}
                  </span>
                </div>
                <Slider
                  value={[inputs.customers]}
                  onValueChange={(value) => handleInputChange('customers', value)}
                  min={100}
                  max={50000}
                  step={100}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-muted-foreground mt-2">
                  <span>100</span>
                  <span>50,000</span>
                </div>
              </div>

              {/* Average Ticket Cost */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <label className="text-sm font-medium text-foreground flex items-center gap-2">
                    <DollarSign className="w-4 h-4" />
                    Avg Support Ticket Cost
                  </label>
                  <span className="text-lg font-bold text-primary">
                    ${inputs.avgTicketCost}
                  </span>
                </div>
                <Slider
                  value={[inputs.avgTicketCost]}
                  onValueChange={(value) => handleInputChange('avgTicketCost', value)}
                  min={20}
                  max={200}
                  step={5}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-muted-foreground mt-2">
                  <span>$20</span>
                  <span>$200</span>
                </div>
              </div>

              {/* Technician Hours per Month */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <label className="text-sm font-medium text-foreground flex items-center gap-2">
                    <Clock className="w-4 h-4" />
                    Technician Hours/Month
                  </label>
                  <span className="text-lg font-bold text-primary">
                    {inputs.technicianHours}
                  </span>
                </div>
                <Slider
                  value={[inputs.technicianHours]}
                  onValueChange={(value) => handleInputChange('technicianHours', value)}
                  min={40}
                  max={1000}
                  step={10}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-muted-foreground mt-2">
                  <span>40</span>
                  <span>1,000</span>
                </div>
              </div>

              {/* Monthly Downtime Hours */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <label className="text-sm font-medium text-foreground flex items-center gap-2">
                    <Zap className="w-4 h-4" />
                    Monthly Downtime Hours
                  </label>
                  <span className="text-lg font-bold text-primary">
                    {inputs.downtimeHours}
                  </span>
                </div>
                <Slider
                  value={[inputs.downtimeHours]}
                  onValueChange={(value) => handleInputChange('downtimeHours', value)}
                  min={1}
                  max={100}
                  step={1}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-muted-foreground mt-2">
                  <span>1</span>
                  <span>100</span>
                </div>
              </div>

              {/* Support Tickets per Month */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <label className="text-sm font-medium text-foreground flex items-center gap-2">
                    <Target className="w-4 h-4" />
                    Support Tickets/Month
                  </label>
                  <span className="text-lg font-bold text-primary">
                    {inputs.supportTickets}
                  </span>
                </div>
                <Slider
                  value={[inputs.supportTickets]}
                  onValueChange={(value) => handleInputChange('supportTickets', value)}
                  min={10}
                  max={2000}
                  step={10}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-muted-foreground mt-2">
                  <span>10</span>
                  <span>2,000</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Results */}
          <Card className="p-8 bg-gradient-to-br from-primary/5 to-accent/5 border-primary/20">
            <CardHeader className="px-0 pt-0">
              <CardTitle className="flex items-center gap-3">
                <TrendingUp className="w-6 h-6 text-primary" />
                Your Potential Savings
              </CardTitle>
            </CardHeader>
            <CardContent className="px-0 space-y-6">
              {/* Monthly Savings Breakdown */}
              <div className="space-y-4">
                <h4 className="font-semibold text-foreground">Monthly Savings Breakdown:</h4>
                
                <div className="space-y-3">
                  <div className="flex justify-between items-center p-3 bg-background/50 rounded-lg">
                    <span className="text-sm text-muted-foreground">Operational Efficiency</span>
                    <span className="font-semibold text-green-600">
                      +${savings.operationalSavings?.toFixed(0) || 0}
                    </span>
                  </div>
                  
                  <div className="flex justify-between items-center p-3 bg-background/50 rounded-lg">
                    <span className="text-sm text-muted-foreground">Technician Time Saved</span>
                    <span className="font-semibold text-green-600">
                      +${savings.technicianSavings?.toFixed(0) || 0}
                    </span>
                  </div>
                  
                  <div className="flex justify-between items-center p-3 bg-background/50 rounded-lg">
                    <span className="text-sm text-muted-foreground">Downtime Reduction</span>
                    <span className="font-semibold text-green-600">
                      +${savings.downtimeSavings?.toFixed(0) || 0}
                    </span>
                  </div>
                  
                  <div className="flex justify-between items-center p-3 bg-background/50 rounded-lg">
                    <span className="text-sm text-muted-foreground">Support Cost Reduction</span>
                    <span className="font-semibold text-green-600">
                      +${savings.supportSavings?.toFixed(0) || 0}
                    </span>
                  </div>
                </div>
              </div>

              {/* Platform Cost */}
              <div className="border-t border-border pt-4">
                <div className="flex justify-between items-center p-3 bg-red-50 dark:bg-red-900/10 rounded-lg border border-red-200 dark:border-red-800">
                  <span className="text-sm text-muted-foreground">Platform Cost</span>
                  <span className="font-semibold text-red-600">
                    -${platformCost}
                  </span>
                </div>
              </div>

              {/* Net Savings */}
              <div className="border-t border-border pt-4">
                <div className="p-4 bg-primary/10 rounded-xl border border-primary/20">
                  <div className="text-center">
                    <div className="text-3xl font-bold text-primary mb-2">
                      ${(savings.totalMonthlySavings - platformCost).toFixed(0)}
                    </div>
                    <div className="text-sm text-muted-foreground mb-4">
                      Net Monthly Savings
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <div className="font-bold text-foreground">
                          ${savings.totalYearlySavings?.toFixed(0) || 0}
                        </div>
                        <div className="text-muted-foreground">Annual Savings</div>
                      </div>
                      <div>
                        <div className="font-bold text-foreground">
                          {savings.roiPercentage?.toFixed(0) || 0}%
                        </div>
                        <div className="text-muted-foreground">ROI</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Payback Period */}
              <div className="text-center p-4 bg-accent/10 rounded-lg">
                <div className="text-lg font-bold text-foreground mb-1">
                  {savings.paybackPeriod?.toFixed(1) || 0} months
                </div>
                <div className="text-sm text-muted-foreground">
                  Payback Period
                </div>
              </div>

              {/* CTA */}
              <div className="pt-4">
                <Button className="w-full" size="lg">
                  Start Free Trial to Realize These Savings
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
                
                <div className="mt-4 space-y-2">
                  {[
                    '14-day free trial',
                    'No setup costs',
                    'Cancel anytime'
                  ].map((guarantee, index) => (
                    <div key={index} className="flex items-center text-sm text-muted-foreground">
                      <CheckCircle className="w-4 h-4 text-green-600 mr-2" />
                      {guarantee}
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Additional Benefits */}
        <div className="mt-16 text-center">
          <h3 className="text-xl font-bold text-foreground mb-8">
            Beyond Cost Savings: Additional Benefits
          </h3>
          
          <div className="grid md:grid-cols-4 gap-6 max-w-4xl mx-auto">
            {[
              {
                title: 'Customer Satisfaction',
                value: '+25%',
                description: 'Improved service quality and response times'
              },
              {
                title: 'Team Productivity',
                value: '+40%',
                description: 'Automated workflows free up staff time'
              },
              {
                title: 'Revenue Growth',
                value: '+30%',
                description: 'Better insights drive revenue opportunities'
              },
              {
                title: 'Market Position',
                value: 'Competitive Edge',
                description: 'Stay ahead with modern technology'
              }
            ].map((benefit, index) => (
              <div key={index} className="p-4 bg-background rounded-xl border border-border">
                <div className="text-2xl font-bold text-primary mb-2">
                  {benefit.value}
                </div>
                <div className="font-semibold text-foreground mb-2">
                  {benefit.title}
                </div>
                <div className="text-sm text-muted-foreground">
                  {benefit.description}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}