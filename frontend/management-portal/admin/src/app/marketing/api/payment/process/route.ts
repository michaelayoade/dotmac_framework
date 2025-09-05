import { NextRequest, NextResponse } from 'next/server'

interface PaymentProcessRequest {
  token: string
  amount: number
  plan_type: 'starter' | 'professional' | 'enterprise'
  payment_method?: {
    card_number: string
    expiry: string
    cvv: string
  }
}

interface PaymentResult {
  success: boolean
  payment_id?: string
  transaction_id?: string
  message: string
  next_steps?: string[]
  provisioning_status?: string
}

export async function POST(request: NextRequest) {
  try {
    const body: PaymentProcessRequest = await request.json()
    
    // Validate required fields
    if (!body.token || !body.amount || !body.plan_type) {
      return NextResponse.json(
        { error: 'Missing required fields: token, amount, plan_type' },
        { status: 400 }
      )
    }

    const managementApiUrl = process.env.MANAGEMENT_API_URL || 'http://localhost:3000'
    const serviceToken = process.env.MANAGEMENT_SERVICE_TOKEN

    // Step 1: Process payment (demo mode for now, would integrate with Stripe/PayPal)
    const paymentResult = await processPayment(body)
    
    if (!paymentResult.success) {
      return NextResponse.json({
        success: false,
        error: paymentResult.message,
        code: 'PAYMENT_FAILED'
      }, { status: 400 })
    }

    // Step 2: Update onboarding request with payment info
    const onboardingUpdateResponse = await fetch(`${managementApiUrl}/api/v1/onboarding/requests/${body.token}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${serviceToken}`,
      },
      body: JSON.stringify({
        payment_status: 'completed',
        payment_id: paymentResult.payment_id,
        transaction_id: paymentResult.transaction_id,
        plan_type: body.plan_type,
        monthly_amount: body.amount,
        billing_cycle: 'monthly',
        status: 'payment_confirmed',
        metadata: {
          payment_processed_at: new Date().toISOString(),
          payment_method: 'credit_card',
          amount_paid: body.amount
        }
      }),
    })

    if (!onboardingUpdateResponse.ok) {
      // Payment succeeded but onboarding update failed - need manual intervention
      console.error('Payment succeeded but onboarding update failed')
      return NextResponse.json({
        success: true,
        warning: 'Payment processed but provisioning delayed',
        payment_id: paymentResult.payment_id,
        message: 'Your payment was successful. Our team will complete your setup within 24 hours.',
        support_contact: 'support@dotmac.platform'
      })
    }

    // Step 3: Trigger automated provisioning
    const provisioningResponse = await fetch(`${managementApiUrl}/api/v1/provisioning/auto-provision`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${serviceToken}`,
      },
      body: JSON.stringify({
        onboarding_request_id: body.token,
        plan_type: body.plan_type,
        provisioning_type: 'auto', // or 'manual' for BYO servers
        priority: getPlanPriority(body.plan_type),
        estimated_completion: getEstimatedCompletion(body.plan_type)
      }),
    })

    if (provisioningResponse.ok) {
      const provisioningData = await provisioningResponse.json()
      
      // Step 4: Send enhanced welcome email with automation
      await sendEnhancedWelcomeEmail(body.token, {
        plan_type: body.plan_type,
        payment_id: paymentResult.payment_id,
        provisioning_id: provisioningData.id,
        estimated_completion: provisioningData.estimated_completion
      })

      return NextResponse.json({
        success: true,
        payment_id: paymentResult.payment_id,
        transaction_id: paymentResult.transaction_id,
        provisioning_id: provisioningData.id,
        message: 'Payment successful! Your ISP platform is being provisioned.',
        next_steps: [
          'Check your email for setup instructions',
          'Your platform will be ready in 15-30 minutes',
          'You\'ll receive login credentials once setup is complete'
        ],
        provisioning_status: 'in_progress',
        estimated_completion: provisioningData.estimated_completion,
        redirect_url: `/marketing/success?token=${body.token}&payment_id=${paymentResult.payment_id}`
      })
    } else {
      // Payment succeeded, onboarding updated, but provisioning failed
      return NextResponse.json({
        success: true,
        payment_id: paymentResult.payment_id,
        provisioning_status: 'manual_required',
        message: 'Payment successful! Our team will set up your platform manually.',
        next_steps: [
          'You will receive an email confirmation shortly',
          'Our technical team will provision your platform within 24 hours',
          'Login credentials will be sent via email once ready'
        ],
        support_contact: 'support@dotmac.platform'
      })
    }

  } catch (error) {
    console.error('Payment processing error:', error)
    
    return NextResponse.json({
      success: false,
      error: 'Payment processing failed',
      code: 'INTERNAL_ERROR',
      message: 'Please try again or contact support if the issue persists',
      support_contact: 'support@dotmac.platform'
    }, { status: 500 })
  }
}

async function processPayment(request: PaymentProcessRequest): Promise<PaymentResult> {
  // Demo payment processing - in production would integrate with Stripe/PayPal
  try {
    // Simulate payment processing delay
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    // Generate demo payment ID
    const paymentId = `pay_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    const transactionId = `txn_${Date.now()}`
    
    // Demo: 95% success rate
    const success = Math.random() > 0.05
    
    if (success) {
      return {
        success: true,
        payment_id: paymentId,
        transaction_id: transactionId,
        message: 'Payment processed successfully'
      }
    } else {
      return {
        success: false,
        message: 'Payment declined - please check your card details'
      }
    }
  } catch (error) {
    return {
      success: false,
      message: 'Payment processing service unavailable'
    }
  }
}

function getPlanPriority(planType: string): 'high' | 'medium' | 'low' {
  switch (planType) {
    case 'enterprise':
      return 'high'
    case 'professional':
      return 'medium'
    case 'starter':
    default:
      return 'low'
  }
}

function getEstimatedCompletion(planType: string): string {
  const now = new Date()
  let minutes = 15 // Default for starter
  
  switch (planType) {
    case 'enterprise':
      minutes = 45 // More complex setup
      break
    case 'professional':
      minutes = 30
      break
    case 'starter':
    default:
      minutes = 15
      break
  }
  
  return new Date(now.getTime() + minutes * 60 * 1000).toISOString()
}

async function sendEnhancedWelcomeEmail(onboardingToken: string, details: {
  plan_type: string
  payment_id: string
  provisioning_id: string
  estimated_completion: string
}) {
  try {
    // Get onboarding request details for recipient info
    const managementApiUrl = process.env.MANAGEMENT_API_URL || 'http://localhost:3000'
    const serviceToken = process.env.MANAGEMENT_SERVICE_TOKEN

    const onboardingResponse = await fetch(`${managementApiUrl}/api/v1/onboarding/requests/${onboardingToken}`, {
      headers: {
        'Authorization': `Bearer ${serviceToken}`,
      },
    })

    if (onboardingResponse.ok) {
      const onboardingData = await onboardingResponse.json()
      
      // Use enhanced email automation system
      await fetch('/api/notifications/email-automation', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          trigger: 'payment_success',
          recipient: {
            email: onboardingData.email,
            name: onboardingData.contact_name || onboardingData.name || 'Valued Customer',
            company: onboardingData.company_name
          },
          data: {
            onboarding_request_id: onboardingToken,
            plan_type: details.plan_type,
            payment_id: details.payment_id,
            provisioning_id: details.provisioning_id,
            custom_data: {
              estimated_completion: details.estimated_completion
            }
          },
          priority: 'high'
        }),
      })
    } else {
      // Fallback to original method
      await sendWelcomeEmail(onboardingToken, details)
    }
  } catch (error) {
    console.error('Failed to send enhanced welcome email:', error)
    // Fallback to original method
    try {
      await sendWelcomeEmail(onboardingToken, details)
    } catch (fallbackError) {
      console.error('Fallback email also failed:', fallbackError)
    }
  }
}

async function sendWelcomeEmail(onboardingToken: string, details: {
  plan_type: string
  payment_id: string
  provisioning_id: string
}) {
  try {
    const managementApiUrl = process.env.MANAGEMENT_API_URL || 'http://localhost:3000'
    const serviceToken = process.env.MANAGEMENT_SERVICE_TOKEN

    await fetch(`${managementApiUrl}/api/v1/notifications/email`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${serviceToken}`,
      },
      body: JSON.stringify({
        template: 'welcome_payment_success',
        recipient_source: 'onboarding_request',
        recipient_id: onboardingToken,
        data: {
          plan_type: details.plan_type,
          payment_id: details.payment_id,
          provisioning_id: details.provisioning_id,
          support_url: 'https://docs.dotmac.platform/support',
          status_url: `https://status.dotmac.platform/provisioning/${details.provisioning_id}`
        }
      }),
    })
  } catch (error) {
    console.error('Failed to send welcome email:', error)
    // Don't fail the payment process if email fails
  }
}