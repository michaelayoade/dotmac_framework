import { NextRequest, NextResponse } from 'next/server'

interface SignupRequest {
  companyName: string
  firstName: string
  lastName: string
  email: string
  phone?: string
  customerCount?: string
  plan: string
  agreedToTerms: boolean
  wantsUpdates: boolean
  source: string
  planDetails: {
    name: string
    price: string
    period: string
    trialDays: number
    features: string[]
  }
}

interface ProvisioningRequest {
  tenant_name: string
  admin_email: string
  admin_first_name: string
  admin_last_name: string
  company_name: string
  plan_type: string
  trial_days: number
  customer_limit: number
  phone?: string
  estimated_customers?: string
  marketing_consent: boolean
  source: string
}

interface LicenseResponse {
  license_key: string
  tenant_id: string
  expires_at: string
  features: string[]
  limits: {
    max_customers: number
    max_users: number
    max_integrations: number
  }
}

interface ProvisioningResponse {
  success: boolean
  tenant_id: string
  admin_user_id: string
  onboarding_token: string
  license: LicenseResponse
  environment: {
    management_url: string
    api_base_url: string
    documentation_url: string
  }
  credentials: {
    initial_password: string
    requires_password_change: boolean
  }
}

// Plan configuration mapping
const planConfigs = {
  starter: {
    customer_limit: 100,
    trial_days: 0, // Free forever
    features: ['basic_monitoring', 'customer_portal', 'email_support', 'api_access']
  },
  professional: {
    customer_limit: 5000,
    trial_days: 14,
    features: ['advanced_automation', 'priority_support', 'mobile_apps', 'integrations', 'sla_monitoring']
  },
  enterprise: {
    customer_limit: -1, // Unlimited
    trial_days: 30,
    features: ['white_label', 'dedicated_support', 'custom_integrations', 'advanced_security', 'custom_development']
  }
}

export async function POST(request: NextRequest) {
  try {
    const body: SignupRequest = await request.json()
    
    // Validate required fields
    if (!body.companyName || !body.firstName || !body.lastName || !body.email || !body.plan) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      )
    }

    if (!body.agreedToTerms) {
      return NextResponse.json(
        { error: 'Terms of service must be accepted' },
        { status: 400 }
      )
    }

    // Get plan configuration
    const planConfig = planConfigs[body.plan as keyof typeof planConfigs]
    if (!planConfig) {
      return NextResponse.json(
        { error: 'Invalid plan selected' },
        { status: 400 }
      )
    }

    // Prepare provisioning request for DotMac Management Platform
    const provisioningData: ProvisioningRequest = {
      tenant_name: body.companyName.toLowerCase().replace(/[^a-z0-9]/g, ''),
      admin_email: body.email,
      admin_first_name: body.firstName,
      admin_last_name: body.lastName,
      company_name: body.companyName,
      plan_type: body.plan,
      trial_days: planConfig.trial_days,
      customer_limit: planConfig.customer_limit,
      phone: body.phone,
      estimated_customers: body.customerCount,
      marketing_consent: body.wantsUpdates,
      source: body.source
    }

    // Call DotMac Management Platform API for tenant provisioning
    const managementPlatformUrl = process.env.DOTMAC_MANAGEMENT_PLATFORM_URL || 'https://manage.dotmac.platform'
    const apiKey = process.env.DOTMAC_API_KEY

    if (!apiKey) {
      console.error('DOTMAC_API_KEY not configured')
      return NextResponse.json(
        { error: 'Service configuration error' },
        { status: 500 }
      )
    }

    const provisioningResponse = await fetch(`${managementPlatformUrl}/api/v1/tenants/provision`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
        'X-Source': 'marketing-website'
      },
      body: JSON.stringify(provisioningData)
    })

    if (!provisioningResponse.ok) {
      const errorData = await provisioningResponse.json().catch(() => ({}))
      console.error('Provisioning failed:', errorData)
      
      return NextResponse.json(
        { error: 'Failed to create account. Please try again or contact support.' },
        { status: 500 }
      )
    }

    const provisioningResult: ProvisioningResponse = await provisioningResponse.json()

    // Generate test period license
    const licenseData = await generateTestLicense(
      provisioningResult.tenant_id,
      body.plan,
      planConfig
    )

    // Send welcome email with onboarding details
    await sendWelcomeEmail({
      email: body.email,
      firstName: body.firstName,
      companyName: body.companyName,
      planName: body.planDetails.name,
      trialDays: planConfig.trial_days,
      tenantId: provisioningResult.tenant_id,
      onboardingToken: provisioningResult.onboarding_token,
      managementUrl: provisioningResult.environment.management_url,
      initialPassword: provisioningResult.credentials.initial_password
    })

    // Log successful signup for analytics
    await logSignupEvent({
      email: body.email,
      companyName: body.companyName,
      plan: body.plan,
      source: body.source,
      tenantId: provisioningResult.tenant_id
    })

    // Return success response with onboarding token
    return NextResponse.json({
      success: true,
      message: 'Account created successfully',
      token: provisioningResult.onboarding_token,
      tenant_id: provisioningResult.tenant_id,
      management_url: provisioningResult.environment.management_url,
      trial_days: planConfig.trial_days,
      license: licenseData
    })

  } catch (error) {
    console.error('Signup error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

async function generateTestLicense(
  tenantId: string, 
  planType: string, 
  planConfig: any
): Promise<LicenseResponse> {
  // Generate time-limited test license
  const now = new Date()
  const expiresAt = new Date(now.getTime() + (planConfig.trial_days * 24 * 60 * 60 * 1000))
  
  // In production, this would call the licensing service
  const licenseKey = `TEST-${tenantId.slice(0, 8).toUpperCase()}-${Date.now().toString(36).slice(-4).toUpperCase()}`
  
  return {
    license_key: licenseKey,
    tenant_id: tenantId,
    expires_at: expiresAt.toISOString(),
    features: planConfig.features,
    limits: {
      max_customers: planConfig.customer_limit,
      max_users: planType === 'starter' ? 3 : planType === 'professional' ? 10 : -1,
      max_integrations: planType === 'starter' ? 5 : planType === 'professional' ? 50 : -1
    }
  }
}

async function sendWelcomeEmail(data: {
  email: string
  firstName: string
  companyName: string
  planName: string
  trialDays: number
  tenantId: string
  onboardingToken: string
  managementUrl: string
  initialPassword: string
}) {
  // In production, integrate with email service (SendGrid, etc.)
  console.log('Sending welcome email to:', data.email)
  
  // This would typically use an email service
  const emailData = {
    to: data.email,
    subject: `Welcome to ISP Framework, ${data.firstName}!`,
    template: 'welcome-onboarding',
    variables: {
      firstName: data.firstName,
      companyName: data.companyName,
      planName: data.planName,
      trialDays: data.trialDays,
      loginUrl: `${data.managementUrl}/login?token=${data.onboardingToken}`,
      initialPassword: data.initialPassword,
      supportEmail: 'support@dotmac.platform'
    }
  }
  
  // TODO: Implement actual email sending
  // await sendEmail(emailData)
}

async function logSignupEvent(data: {
  email: string
  companyName: string
  plan: string
  source: string
  tenantId: string
}) {
  // Log to analytics service for tracking conversion metrics
  console.log('Signup event:', data)
  
  // In production, this would send to analytics platforms
  // await analytics.track('account_created', data)
}

// Handle OPTIONS request for CORS
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