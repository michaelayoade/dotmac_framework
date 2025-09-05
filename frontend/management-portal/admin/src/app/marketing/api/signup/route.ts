import { NextRequest, NextResponse } from 'next/server'

interface SignupRequest {
  companyName: string
  contactName: string
  email: string
  phone?: string
  planType: 'starter' | 'professional' | 'enterprise'
}

export async function POST(request: NextRequest) {
  try {
    const body: SignupRequest = await request.json()
    
    // Validate required fields
    if (!body.companyName || !body.contactName || !body.email) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      )
    }

    // Connect to existing onboarding service
    const managementApiUrl = process.env.MANAGEMENT_API_URL || 'http://localhost:3000'
    const serviceToken = process.env.MANAGEMENT_SERVICE_TOKEN

    // Create onboarding request using existing system
    const onboardingResponse = await fetch(`${managementApiUrl}/api/v1/onboarding/requests`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${serviceToken}`,
      },
      body: JSON.stringify({
        tenant_name: body.companyName,
        contact_name: body.contactName,
        email: body.email,
        phone: body.phone,
        plan_type: body.planType,
        source: 'marketing_website',
        metadata: {
          signup_timestamp: new Date().toISOString(),
          user_agent: request.headers.get('user-agent'),
        }
      }),
    })

    if (!onboardingResponse.ok) {
      throw new Error('Failed to create onboarding request')
    }

    const onboardingResult = await onboardingResponse.json()

    // Return signup token for payment processing
    return NextResponse.json({
      success: true,
      token: onboardingResult.id,
      message: 'Signup initiated successfully',
      next_step: 'payment',
      redirect_url: `/marketing/payment?token=${onboardingResult.id}`
    })

  } catch (error) {
    console.error('Signup error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}