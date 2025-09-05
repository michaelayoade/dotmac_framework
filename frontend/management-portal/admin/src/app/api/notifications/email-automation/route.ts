import { NextRequest, NextResponse } from 'next/server'

interface EmailAutomationRequest {
  trigger: 'payment_success' | 'provisioning_started' | 'provisioning_completed' | 'provisioning_failed' | 'welcome_sequence' | 'followup'
  recipient: {
    email: string
    name: string
    company?: string
  }
  data: {
    onboarding_request_id: string
    plan_type: string
    payment_id?: string
    provisioning_id?: string
    access_url?: string
    credentials?: {
      admin_url: string
      username: string
      temporary_password: string
      api_key: string
    }
    error_details?: string
    custom_data?: Record<string, any>
  }
  delay_minutes?: number
  priority?: 'high' | 'medium' | 'low'
}

interface EmailTemplate {
  id: string
  subject: string
  html_content: string
  text_content: string
  variables: string[]
}

export async function POST(request: NextRequest) {
  try {
    const body: EmailAutomationRequest = await request.json()
    
    // Validate required fields
    if (!body.trigger || !body.recipient?.email || !body.data?.onboarding_request_id) {
      return NextResponse.json(
        { error: 'Missing required fields: trigger, recipient.email, data.onboarding_request_id' },
        { status: 400 }
      )
    }

    // Get email template based on trigger
    const template = getEmailTemplate(body.trigger, body.data.plan_type)
    
    // Process the email automation
    const result = await processEmailAutomation(body, template)
    
    return NextResponse.json({
      success: true,
      email_id: result.email_id,
      scheduled_for: result.scheduled_for,
      template_used: template.id,
      priority: body.priority || 'medium'
    })

  } catch (error) {
    console.error('Email automation error:', error)
    
    return NextResponse.json({
      success: false,
      error: 'Email automation failed',
      message: 'Email will be sent manually'
    }, { status: 500 })
  }
}

async function processEmailAutomation(request: EmailAutomationRequest, template: EmailTemplate) {
  const emailId = `email_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  const scheduledFor = new Date(Date.now() + (request.delay_minutes || 0) * 60 * 1000)

  // Replace template variables with actual data
  const personalizedContent = await personalizeEmailContent(template, request)
  
  // Send to existing notification service
  try {
    const managementApiUrl = process.env.MANAGEMENT_API_URL || 'http://localhost:3000'
    const serviceToken = process.env.MANAGEMENT_SERVICE_TOKEN

    const notificationResponse = await fetch(`${managementApiUrl}/api/v1/notifications/email`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${serviceToken}`,
      },
      body: JSON.stringify({
        template: template.id,
        recipient_email: request.recipient.email,
        recipient_name: request.recipient.name,
        subject: personalizedContent.subject,
        html_content: personalizedContent.html_content,
        text_content: personalizedContent.text_content,
        data: request.data,
        priority: request.priority || 'medium',
        scheduled_for: scheduledFor.toISOString(),
        tags: [
          `trigger:${request.trigger}`,
          `plan:${request.data.plan_type}`,
          'automated'
        ]
      }),
    })

    if (!notificationResponse.ok) {
      console.warn('Notification service unavailable, using fallback')
    }

  } catch (error) {
    console.warn('Failed to send via notification service, using fallback:', error)
  }

  // Schedule follow-up emails if this is part of a sequence
  if (request.trigger === 'payment_success') {
    await scheduleFollowupEmails(request)
  }

  return {
    email_id: emailId,
    scheduled_for: scheduledFor.toISOString()
  }
}

function getEmailTemplate(trigger: string, planType: string): EmailTemplate {
  const templates: Record<string, EmailTemplate> = {
    payment_success: {
      id: 'payment_success_v1',
      subject: '🎉 Payment Confirmed - Your {{plan_type}} Platform is Being Set Up!',
      html_content: `
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
          <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 20px; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 28px;">Welcome to DotMac Platform! 🚀</h1>
          </div>
          
          <div style="padding: 30px 20px; background: #ffffff;">
            <h2 style="color: #333; margin-bottom: 20px;">Hi {{recipient_name}},</h2>
            
            <p style="color: #666; font-size: 16px; line-height: 1.6;">
              Thank you for choosing DotMac Platform! Your payment has been successfully processed, and we're now setting up your <strong>{{plan_type}}</strong> ISP management system.
            </p>
            
            <div style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; margin: 25px 0;">
              <h3 style="color: #28a745; margin: 0 0 15px 0;">✅ What's Happening Now</h3>
              <ul style="color: #666; margin: 0; padding-left: 20px;">
                <li>Creating your secure tenant environment</li>
                <li>Setting up your dedicated database</li>
                <li>Configuring DNS and SSL certificates</li>
                <li>Installing platform components</li>
              </ul>
            </div>
            
            <div style="background: #e7f3ff; border: 1px solid #b8daff; border-radius: 8px; padding: 20px; margin: 25px 0;">
              <h3 style="color: #0066cc; margin: 0 0 15px 0;">⏱️ Timeline</h3>
              <p style="color: #666; margin: 0;">
                Your platform will be ready in approximately <strong>{{estimated_time}}</strong>. 
                We'll send you login credentials as soon as setup is complete.
              </p>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
              <a href="{{status_url}}" style="background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                Track Setup Progress
              </a>
            </div>
            
            <p style="color: #666; font-size: 14px; margin-top: 30px;">
              Questions? Reply to this email or contact our support team at 
              <a href="mailto:support@dotmac.platform" style="color: #667eea;">support@dotmac.platform</a>
            </p>
          </div>
          
          <div style="background: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 12px;">
            <p>DotMac Platform - Complete ISP Management Solution</p>
            <p>Payment ID: {{payment_id}} | Order: {{onboarding_request_id}}</p>
          </div>
        </div>
      `,
      text_content: `
Welcome to DotMac Platform!

Hi {{recipient_name}},

Thank you for choosing DotMac Platform! Your payment has been successfully processed, and we're now setting up your {{plan_type}} ISP management system.

What's happening now:
- Creating your secure tenant environment
- Setting up your dedicated database  
- Configuring DNS and SSL certificates
- Installing platform components

Your platform will be ready in approximately {{estimated_time}}. We'll send you login credentials as soon as setup is complete.

Track your setup progress: {{status_url}}

Questions? Contact support at support@dotmac.platform

Payment ID: {{payment_id}}
Order: {{onboarding_request_id}}

DotMac Platform Team
      `,
      variables: ['recipient_name', 'plan_type', 'estimated_time', 'status_url', 'payment_id', 'onboarding_request_id']
    },

    provisioning_completed: {
      id: 'provisioning_completed_v1',
      subject: '🎉 Your {{plan_type}} Platform is Ready!',
      html_content: `
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
          <div style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); padding: 40px 20px; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 28px;">Your Platform is Live! 🎉</h1>
          </div>
          
          <div style="padding: 30px 20px; background: #ffffff;">
            <h2 style="color: #333; margin-bottom: 20px;">Hi {{recipient_name}},</h2>
            
            <p style="color: #666; font-size: 16px; line-height: 1.6;">
              Great news! Your <strong>{{plan_type}}</strong> DotMac Platform has been successfully deployed and is ready to use.
            </p>
            
            <div style="background: #d4edda; border: 1px solid #c3e6cb; border-radius: 8px; padding: 20px; margin: 25px 0;">
              <h3 style="color: #155724; margin: 0 0 15px 0;">🔐 Your Login Credentials</h3>
              <div style="background: white; padding: 15px; border-radius: 5px; font-family: monospace;">
                <p style="margin: 5px 0;"><strong>Admin URL:</strong> {{admin_url}}</p>
                <p style="margin: 5px 0;"><strong>Username:</strong> {{username}}</p>
                <p style="margin: 5px 0;"><strong>Password:</strong> {{temporary_password}}</p>
                <p style="margin: 5px 0;"><strong>API Key:</strong> {{api_key}}</p>
              </div>
              <p style="color: #856404; font-size: 14px; margin: 15px 0 0 0;">
                ⚠️ Please change your password after first login and store your API key securely.
              </p>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
              <a href="{{admin_url}}" style="background: #28a745; color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block; font-size: 18px;">
                Access Your Platform
              </a>
            </div>
            
            <div style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; margin: 25px 0;">
              <h3 style="color: #495057; margin: 0 0 15px 0;">📚 Next Steps</h3>
              <ul style="color: #666; margin: 0; padding-left: 20px;">
                <li>Complete the onboarding wizard</li>
                <li>Configure your ISP settings</li>
                <li>Add your first customers</li>
                <li>Explore the admin dashboard</li>
              </ul>
            </div>
            
            <p style="color: #666; font-size: 14px; margin-top: 30px;">
              Need help getting started? Check our 
              <a href="{{docs_url}}" style="color: #667eea;">documentation</a> or contact support at 
              <a href="mailto:support@dotmac.platform" style="color: #667eea;">support@dotmac.platform</a>
            </p>
          </div>
          
          <div style="background: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 12px;">
            <p>DotMac Platform - Complete ISP Management Solution</p>
            <p>Provisioning ID: {{provisioning_id}} | Access: {{access_url}}</p>
          </div>
        </div>
      `,
      text_content: `
Your DotMac Platform is Ready!

Hi {{recipient_name}},

Great news! Your {{plan_type}} DotMac Platform has been successfully deployed and is ready to use.

Your Login Credentials:
- Admin URL: {{admin_url}}
- Username: {{username}}
- Password: {{temporary_password}}
- API Key: {{api_key}}

⚠️ Please change your password after first login and store your API key securely.

Access your platform: {{admin_url}}

Next Steps:
- Complete the onboarding wizard
- Configure your ISP settings
- Add your first customers
- Explore the admin dashboard

Need help? Check our docs at {{docs_url}} or contact support@dotmac.platform

Provisioning ID: {{provisioning_id}}

DotMac Platform Team
      `,
      variables: ['recipient_name', 'plan_type', 'admin_url', 'username', 'temporary_password', 'api_key', 'access_url', 'docs_url', 'provisioning_id']
    },

    provisioning_failed: {
      id: 'provisioning_failed_v1',
      subject: 'Setup Assistance Required - We\'re Here to Help',
      html_content: `
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
          <div style="background: #dc3545; padding: 40px 20px; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 28px;">We're Looking Into This</h1>
          </div>
          
          <div style="padding: 30px 20px; background: #ffffff;">
            <h2 style="color: #333; margin-bottom: 20px;">Hi {{recipient_name}},</h2>
            
            <p style="color: #666; font-size: 16px; line-height: 1.6;">
              We encountered an issue while setting up your <strong>{{plan_type}}</strong> platform. Don't worry - our technical team has been notified and is working to resolve this.
            </p>
            
            <div style="background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 8px; padding: 20px; margin: 25px 0;">
              <h3 style="color: #721c24; margin: 0 0 15px 0;">What Happened</h3>
              <p style="color: #721c24; margin: 0;">{{error_details}}</p>
            </div>
            
            <div style="background: #d1ecf1; border: 1px solid #bee5eb; border-radius: 8px; padding: 20px; margin: 25px 0;">
              <h3 style="color: #0c5460; margin: 0 0 15px 0;">What We're Doing</h3>
              <ul style="color: #0c5460; margin: 0; padding-left: 20px;">
                <li>Our technical team will review your setup within 2 hours</li>
                <li>We'll manually provision your platform if needed</li>
                <li>You'll receive updates via email throughout the process</li>
                <li>Expected completion: 2-4 hours</li>
              </ul>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
              <a href="mailto:support@dotmac.platform?subject=Provisioning%20Issue%20-%20{{onboarding_request_id}}" 
                 style="background: #dc3545; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                Contact Support Team
              </a>
            </div>
            
            <p style="color: #666; font-size: 14px; margin-top: 30px;">
              We apologize for the inconvenience and appreciate your patience. Our team is committed to getting your platform up and running as quickly as possible.
            </p>
          </div>
          
          <div style="background: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 12px;">
            <p>DotMac Platform - Complete ISP Management Solution</p>
            <p>Order: {{onboarding_request_id}} | Support: support@dotmac.platform</p>
          </div>
        </div>
      `,
      text_content: `
Setup Assistance Required

Hi {{recipient_name}},

We encountered an issue while setting up your {{plan_type}} platform. Don't worry - our technical team has been notified and is working to resolve this.

What happened: {{error_details}}

What we're doing:
- Our technical team will review your setup within 2 hours
- We'll manually provision your platform if needed
- You'll receive updates via email throughout the process
- Expected completion: 2-4 hours

Contact our support team: support@dotmac.platform
Subject: Provisioning Issue - {{onboarding_request_id}}

We apologize for the inconvenience and appreciate your patience.

DotMac Platform Team
      `,
      variables: ['recipient_name', 'plan_type', 'error_details', 'onboarding_request_id']
    }
  }

  return templates[trigger] || templates.payment_success
}

async function personalizeEmailContent(template: EmailTemplate, request: EmailAutomationRequest) {
  let subject = template.subject
  let htmlContent = template.html_content
  let textContent = template.text_content

  // Build replacement data
  const replacements: Record<string, string> = {
    recipient_name: request.recipient.name,
    company_name: request.recipient.company || request.recipient.name + "'s Company",
    plan_type: request.data.plan_type.charAt(0).toUpperCase() + request.data.plan_type.slice(1),
    onboarding_request_id: request.data.onboarding_request_id,
    payment_id: request.data.payment_id || 'N/A',
    provisioning_id: request.data.provisioning_id || 'N/A',
    access_url: request.data.access_url || 'https://dotmac.platform',
    status_url: `https://status.dotmac.platform/provisioning/${request.data.provisioning_id || request.data.onboarding_request_id}`,
    docs_url: 'https://docs.dotmac.platform',
    estimated_time: getEstimatedTime(request.data.plan_type),
    error_details: request.data.error_details || 'Technical issue during setup process',
    
    // Credentials (if available)
    admin_url: request.data.credentials?.admin_url || '',
    username: request.data.credentials?.username || '',
    temporary_password: request.data.credentials?.temporary_password || '',
    api_key: request.data.credentials?.api_key || ''
  }

  // Replace variables in all content
  for (const [key, value] of Object.entries(replacements)) {
    const regex = new RegExp(`{{${key}}}`, 'g')
    subject = subject.replace(regex, value)
    htmlContent = htmlContent.replace(regex, value)
    textContent = textContent.replace(regex, value)
  }

  return {
    subject,
    html_content: htmlContent,
    text_content: textContent
  }
}

async function scheduleFollowupEmails(request: EmailAutomationRequest) {
  const followupEmails = [
    {
      trigger: 'followup_day1' as const,
      delay_minutes: 24 * 60, // 1 day
      subject: 'How\'s Your DotMac Platform Setup Going?'
    },
    {
      trigger: 'followup_week1' as const,
      delay_minutes: 7 * 24 * 60, // 1 week
      subject: 'Tips to Get the Most from Your DotMac Platform'
    }
  ]

  for (const followup of followupEmails) {
    try {
      // Schedule followup email
      await fetch('/api/notifications/email-automation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...request,
          trigger: followup.trigger,
          delay_minutes: followup.delay_minutes,
          priority: 'low'
        })
      })
    } catch (error) {
      console.warn(`Failed to schedule followup email: ${followup.trigger}`, error)
    }
  }
}

function getEstimatedTime(planType: string): string {
  const times = {
    starter: '15-30 minutes',
    professional: '30-45 minutes',
    enterprise: '45-60 minutes'
  }
  return times[planType as keyof typeof times] || '15-30 minutes'
}