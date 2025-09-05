import { NextRequest, NextResponse } from 'next/server'

interface LeadRequest {
  name: string
  email: string
  company?: string
  source: string
  status?: string
  initial_message?: string
  metadata?: Record<string, any>
}

export async function POST(request: NextRequest) {
  try {
    const body: LeadRequest = await request.json()
    
    // Validate required fields
    if (!body.name || !body.email || !body.source) {
      return NextResponse.json(
        { error: 'Missing required fields: name, email, source' },
        { status: 400 }
      )
    }

    const managementApiUrl = process.env.MANAGEMENT_API_URL || 'http://localhost:3000'
    const serviceToken = process.env.MANAGEMENT_SERVICE_TOKEN

    // Create lead in existing CRM system
    const leadResponse = await fetch(`${managementApiUrl}/api/v1/leads`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${serviceToken}`,
      },
      body: JSON.stringify({
        name: body.name,
        email: body.email,
        company: body.company,
        source: body.source,
        status: body.status || 'new',
        lead_score: calculateLeadScore(body),
        contact_method: 'email',
        initial_contact_date: new Date().toISOString(),
        initial_message: body.initial_message,
        metadata: {
          ...body.metadata,
          created_via: 'marketing_integration',
          timestamp: new Date().toISOString(),
          user_agent: request.headers.get('user-agent'),
          referrer: request.headers.get('referer'),
        }
      }),
    })

    if (leadResponse.ok) {
      const leadData = await leadResponse.json()
      
      // Trigger follow-up actions
      await triggerFollowUpActions(leadData, body)
      
      return NextResponse.json({
        success: true,
        lead_id: leadData.id,
        message: 'Lead created successfully',
        follow_up: 'Sales team has been notified'
      })

    } else {
      const errorData = await leadResponse.json()
      throw new Error(errorData.message || 'Failed to create lead')
    }

  } catch (error) {
    console.error('Lead creation error:', error)
    
    // Fallback: Log lead locally for manual processing
    console.log('Lead (fallback logging):', {
      name: body.name,
      email: body.email,
      company: body.company,
      source: body.source,
      timestamp: new Date().toISOString(),
      initial_message: body.initial_message
    })

    return NextResponse.json({
      success: false,
      error: 'Failed to create lead in CRM',
      fallback: 'Lead information has been logged for manual processing'
    }, { status: 500 })
  }
}

function calculateLeadScore(lead: LeadRequest): number {
  let score = 50 // Base score
  
  // Score based on source
  const sourceScores: Record<string, number> = {
    'live_chat': 30,
    'contact_form': 20,
    'pricing_page': 25,
    'demo_request': 40,
    'signup_form': 35
  }
  score += sourceScores[lead.source] || 10
  
  // Score based on company info
  if (lead.company && lead.company.length > 0) {
    score += 15
  }
  
  // Score based on message content (if provided)
  if (lead.initial_message) {
    const message = lead.initial_message.toLowerCase()
    if (message.includes('enterprise') || message.includes('large scale')) {
      score += 20
    }
    if (message.includes('urgent') || message.includes('asap')) {
      score += 15
    }
    if (message.includes('budget') || message.includes('pricing')) {
      score += 10
    }
  }
  
  return Math.min(score, 100) // Cap at 100
}

async function triggerFollowUpActions(leadData: any, originalLead: LeadRequest) {
  try {
    const managementApiUrl = process.env.MANAGEMENT_API_URL || 'http://localhost:3000'
    const serviceToken = process.env.MANAGEMENT_SERVICE_TOKEN

    // Create follow-up tasks based on lead score and source
    const tasks = []
    
    if (leadData.lead_score >= 80) {
      tasks.push({
        type: 'call',
        priority: 'high',
        due_date: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(), // 2 hours
        description: `High-priority lead: Call ${originalLead.name} at ${originalLead.email}`
      })
    } else if (leadData.lead_score >= 60) {
      tasks.push({
        type: 'email',
        priority: 'medium',
        due_date: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(), // 24 hours
        description: `Follow up with ${originalLead.name} via email`
      })
    } else {
      tasks.push({
        type: 'email',
        priority: 'low',
        due_date: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(), // 3 days
        description: `Send product information to ${originalLead.name}`
      })
    }

    // Create tasks in the system
    for (const task of tasks) {
      await fetch(`${managementApiUrl}/api/v1/tasks`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${serviceToken}`,
        },
        body: JSON.stringify({
          ...task,
          lead_id: leadData.id,
          assigned_to: 'sales_team',
          created_by: 'marketing_integration'
        }),
      })
    }

    // Send notification to sales team
    await fetch(`${managementApiUrl}/api/v1/notifications`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${serviceToken}`,
      },
      body: JSON.stringify({
        type: 'new_lead',
        recipients: ['sales_team'],
        title: 'New Lead from Marketing Website',
        message: `${originalLead.name} (${originalLead.company || 'No company'}) just contacted us via ${originalLead.source}`,
        data: {
          lead_id: leadData.id,
          lead_score: leadData.lead_score,
          source: originalLead.source
        }
      }),
    })

  } catch (error) {
    console.error('Failed to trigger follow-up actions:', error)
    // Don't fail the lead creation if follow-up actions fail
  }
}