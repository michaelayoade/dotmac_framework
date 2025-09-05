import { NextRequest, NextResponse } from 'next/server'

interface ContactSalesRequest {
  companyName: string
  firstName: string
  lastName: string
  email: string
  phone?: string
  jobTitle?: string
  customerCount?: string
  currentSolution?: string
  timeframe?: string
  requirements?: string
  budget?: string
  preferredContact: string
}

export async function POST(request: NextRequest) {
  try {
    const body: ContactSalesRequest = await request.json()
    
    // Validate required fields
    if (!body.companyName || !body.firstName || !body.lastName || !body.email) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      )
    }

    // Create enterprise lead in CRM
    const leadData = {
      ...body,
      source: 'marketing-website',
      leadType: 'enterprise',
      priority: 'high',
      assignedTo: 'enterprise-sales-team',
      createdAt: new Date().toISOString()
    }

    // Send to CRM system (Salesforce, HubSpot, etc.)
    try {
      const crmResponse = await createCRMLead(leadData)
      console.log('CRM Lead created:', crmResponse.id)
    } catch (error) {
      console.error('Failed to create CRM lead:', error)
      // Continue processing even if CRM fails
    }

    // Send notification to enterprise sales team
    await notifyEnterpriseTeam({
      lead: leadData,
      urgency: determineUrgency(body),
      estimatedValue: estimateAnnualValue(body.customerCount, body.budget)
    })

    // Send immediate acknowledgment email to prospect
    await sendAcknowledgmentEmail({
      email: body.email,
      firstName: body.firstName,
      companyName: body.companyName,
      preferredContact: body.preferredContact
    })

    // Schedule follow-up tasks
    await scheduleFollowUp({
      email: body.email,
      companyName: body.companyName,
      priority: determineUrgency(body),
      preferredContact: body.preferredContact
    })

    return NextResponse.json({
      success: true,
      message: 'Enterprise sales request submitted successfully',
      expectedResponse: 'within 2 business hours'
    })

  } catch (error) {
    console.error('Contact sales error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

async function createCRMLead(leadData: any) {
  // Integration with CRM system
  const crmUrl = process.env.CRM_API_URL || 'https://api.salesforce.com'
  const crmToken = process.env.CRM_API_TOKEN

  if (!crmToken) {
    throw new Error('CRM API token not configured')
  }

  const response = await fetch(`${crmUrl}/leads`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${crmToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      company: leadData.companyName,
      firstName: leadData.firstName,
      lastName: leadData.lastName,
      email: leadData.email,
      phone: leadData.phone,
      title: leadData.jobTitle,
      leadSource: leadData.source,
      description: `Enterprise inquiry: ${leadData.requirements || 'No specific requirements provided'}`,
      customFields: {
        customerCount: leadData.customerCount,
        currentSolution: leadData.currentSolution,
        timeframe: leadData.timeframe,
        budget: leadData.budget,
        preferredContact: leadData.preferredContact
      }
    })
  })

  if (!response.ok) {
    throw new Error(`CRM API error: ${response.status}`)
  }

  return await response.json()
}

function determineUrgency(body: ContactSalesRequest): 'high' | 'medium' | 'low' {
  // High priority indicators
  if (body.timeframe === 'Immediate (within 30 days)' || 
      body.customerCount === '50,000+' ||
      body.budget === '$250K+ annually') {
    return 'high'
  }
  
  // Medium priority indicators
  if (body.timeframe === '1-3 months' ||
      body.customerCount === '25,001-50,000' ||
      body.budget === '$100K-$250K annually') {
    return 'medium'
  }
  
  return 'low'
}

function estimateAnnualValue(customerCount?: string, budget?: string): number {
  // Estimate potential annual contract value
  if (budget?.includes('$250K+')) return 250000
  if (budget?.includes('$100K-$250K')) return 175000
  if (budget?.includes('$50K-$100K')) return 75000
  if (budget?.includes('$10K-$50K')) return 30000
  
  // Estimate based on customer count if no budget provided
  if (customerCount?.includes('50,000+')) return 200000
  if (customerCount?.includes('25,001-50,000')) return 150000
  if (customerCount?.includes('10,001-25,000')) return 100000
  if (customerCount?.includes('5,001-10,000')) return 60000
  
  return 50000 // Default estimate
}

async function notifyEnterpriseTeam(data: {
  lead: any
  urgency: string
  estimatedValue: number
}) {
  // Send Slack notification to enterprise sales team
  const slackWebhook = process.env.SLACK_ENTERPRISE_WEBHOOK
  
  if (slackWebhook) {
    try {
      await fetch(slackWebhook, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: `🚨 New Enterprise Lead - ${data.urgency.toUpperCase()} Priority`,
          blocks: [
            {
              type: 'section',
              text: {
                type: 'mrkdwn',
                text: `*New Enterprise Inquiry*\n*Company:* ${data.lead.companyName}\n*Contact:* ${data.lead.firstName} ${data.lead.lastName} (${data.lead.email})\n*Est. Value:* $${data.estimatedValue.toLocaleString()}\n*Urgency:* ${data.urgency}`
              }
            },
            {
              type: 'section',
              fields: [
                {
                  type: 'mrkdwn',
                  text: `*Customers:* ${data.lead.customerCount || 'Not specified'}`
                },
                {
                  type: 'mrkdwn',
                  text: `*Timeframe:* ${data.lead.timeframe || 'Not specified'}`
                },
                {
                  type: 'mrkdwn',
                  text: `*Budget:* ${data.lead.budget || 'Not specified'}`
                },
                {
                  type: 'mrkdwn',
                  text: `*Current Solution:* ${data.lead.currentSolution || 'Not specified'}`
                }
              ]
            }
          ]
        })
      })
    } catch (error) {
      console.error('Failed to send Slack notification:', error)
    }
  }

  // Send email notification to enterprise sales team
  const enterpriseEmail = process.env.ENTERPRISE_SALES_EMAIL || 'enterprise@dotmac.platform'
  
  // TODO: Implement email service integration
  console.log(`Enterprise notification sent to ${enterpriseEmail}`, data)
}

async function sendAcknowledgmentEmail(data: {
  email: string
  firstName: string
  companyName: string
  preferredContact: string
}) {
  // Send immediate acknowledgment to prospect
  const emailService = process.env.EMAIL_SERVICE_URL
  const emailToken = process.env.EMAIL_SERVICE_TOKEN
  
  if (emailService && emailToken) {
    try {
      await fetch(`${emailService}/send`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${emailToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          to: data.email,
          subject: `Thank you for your enterprise inquiry, ${data.firstName}`,
          template: 'enterprise-acknowledgment',
          variables: {
            firstName: data.firstName,
            companyName: data.companyName,
            preferredContact: data.preferredContact,
            responseTime: '2 business hours',
            enterprisePhone: '+1 (555) 123-ENTER',
            enterpriseEmail: 'enterprise@dotmac.platform'
          }
        })
      })
    } catch (error) {
      console.error('Failed to send acknowledgment email:', error)
    }
  }
}

async function scheduleFollowUp(data: {
  email: string
  companyName: string
  priority: string
  preferredContact: string
}) {
  // Schedule follow-up tasks in CRM or task management system
  const followUpDelay = data.priority === 'high' ? 1 : data.priority === 'medium' ? 2 : 4 // hours
  
  const taskData = {
    type: 'enterprise_followup',
    priority: data.priority,
    assignee: 'enterprise-sales-team',
    dueDate: new Date(Date.now() + followUpDelay * 60 * 60 * 1000).toISOString(),
    description: `Follow up with ${data.companyName} - ${data.preferredContact} preferred`,
    metadata: {
      email: data.email,
      companyName: data.companyName,
      preferredContact: data.preferredContact
    }
  }
  
  // TODO: Integration with task management system
  console.log('Follow-up scheduled:', taskData)
}

export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  })
}