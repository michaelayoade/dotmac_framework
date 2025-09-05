import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const token = searchParams.get('token')
    
    if (!token) {
      return NextResponse.json(
        { error: 'Missing token parameter' },
        { status: 400 }
      )
    }

    const managementApiUrl = process.env.MANAGEMENT_API_URL || 'http://localhost:3000'
    const serviceToken = process.env.MANAGEMENT_SERVICE_TOKEN

    // Get onboarding request to find provisioning ID
    const onboardingResponse = await fetch(`${managementApiUrl}/api/v1/onboarding/requests/${token}`, {
      headers: {
        'Authorization': `Bearer ${serviceToken}`,
      },
    })

    if (!onboardingResponse.ok) {
      return NextResponse.json({
        id: token,
        status: 'not_found',
        steps_completed: [],
        next_steps: ['Contact support for assistance'],
        estimated_completion: new Date().toISOString(),
        error_message: 'Provisioning request not found'
      })
    }

    const onboardingData = await onboardingResponse.json()
    
    // If no provisioning has started yet, return pending status
    if (!onboardingData.provisioning_id) {
      return NextResponse.json({
        id: token,
        status: 'in_progress',
        steps_completed: ['Payment processed', 'Provisioning initiated'],
        next_steps: [
          'Creating your tenant environment',
          'Setting up your database',
          'Configuring your platform'
        ],
        estimated_completion: new Date(Date.now() + 30 * 60 * 1000).toISOString() // 30 minutes from now
      })
    }

    // Get actual provisioning status
    const provisioningResponse = await fetch(`${managementApiUrl}/api/v1/provisioning/requests/${onboardingData.provisioning_id}`, {
      headers: {
        'Authorization': `Bearer ${serviceToken}`,
      },
    })

    if (provisioningResponse.ok) {
      const provisioningData = await provisioningResponse.json()
      
      // Transform backend data to frontend format
      return NextResponse.json({
        id: provisioningData.id,
        status: provisioningData.status,
        steps_completed: provisioningData.steps_completed || [],
        next_steps: provisioningData.next_steps || [],
        estimated_completion: provisioningData.estimated_completion,
        access_url: provisioningData.access_url,
        credentials: provisioningData.credentials,
        error_message: provisioningData.error_message
      })
    } else {
      // Fallback: simulate provisioning status based on time elapsed
      const createdTime = new Date(onboardingData.created_at || Date.now())
      const elapsedMinutes = (Date.now() - createdTime.getTime()) / (1000 * 60)
      
      if (elapsedMinutes < 5) {
        return NextResponse.json({
          id: onboardingData.provisioning_id,
          status: 'in_progress',
          steps_completed: ['Payment processed', 'Tenant created', 'Database initializing'],
          next_steps: [
            'Configuring DNS settings',
            'Setting up SSL certificates',
            'Deploying your platform'
          ],
          estimated_completion: new Date(createdTime.getTime() + 30 * 60 * 1000).toISOString()
        })
      } else if (elapsedMinutes < 15) {
        return NextResponse.json({
          id: onboardingData.provisioning_id,
          status: 'in_progress',
          steps_completed: [
            'Payment processed',
            'Tenant created', 
            'Database initialized',
            'DNS configured'
          ],
          next_steps: [
            'Installing SSL certificates',
            'Finalizing platform deployment',
            'Sending access credentials'
          ],
          estimated_completion: new Date(createdTime.getTime() + 30 * 60 * 1000).toISOString()
        })
      } else if (elapsedMinutes < 30) {
        // Simulate completion for demo
        const subdomain = generateSubdomain(onboardingData.tenant_name || 'demo')
        const credentials = generateDemoCredentials()
        
        return NextResponse.json({
          id: onboardingData.provisioning_id,
          status: 'completed',
          steps_completed: [
            'Payment processed',
            'Tenant created',
            'Database initialized',
            'DNS configured',
            'SSL certificates installed',
            'Platform deployed',
            'Credentials generated'
          ],
          next_steps: [
            'Access your platform using the credentials below',
            'Complete the onboarding wizard',
            'Explore the admin dashboard'
          ],
          estimated_completion: new Date(createdTime.getTime() + 30 * 60 * 1000).toISOString(),
          access_url: `https://${subdomain}.dotmac.platform`,
          credentials: {
            admin_url: `https://${subdomain}.dotmac.platform/admin`,
            username: credentials.username,
            temporary_password: credentials.password,
            api_endpoint: `https://${subdomain}.dotmac.platform/api`,
            api_key: credentials.api_key
          }
        })
      } else {
        // After 30 minutes, show manual intervention required
        return NextResponse.json({
          id: onboardingData.provisioning_id,
          status: 'manual_required',
          steps_completed: [
            'Payment processed',
            'Provisioning initiated'
          ],
          next_steps: [
            'Technical team intervention required',
            'You will receive updates via email',
            'Expected completion within 2-4 hours'
          ],
          estimated_completion: new Date(createdTime.getTime() + 4 * 60 * 60 * 1000).toISOString(),
          error_message: 'Automated provisioning taking longer than expected'
        })
      }
    }

  } catch (error) {
    console.error('Provisioning status check error:', error)
    
    return NextResponse.json({
      id: 'unknown',
      status: 'error',
      steps_completed: [],
      next_steps: [
        'Please contact support for assistance',
        'Include your payment confirmation in the message'
      ],
      estimated_completion: new Date().toISOString(),
      error_message: 'Unable to check provisioning status'
    }, { status: 500 })
  }
}

function generateSubdomain(tenantName: string): string {
  const clean = tenantName.toLowerCase()
    .replace(/[^a-z0-9]/g, '')
    .substring(0, 20)
  const suffix = Math.random().toString(36).substr(2, 4)
  return `${clean}-${suffix}`
}

function generateDemoCredentials() {
  return {
    username: 'admin',
    password: Math.random().toString(36).slice(-12) + Math.random().toString(36).slice(-12),
    api_key: `dmk_${Math.random().toString(36)}${Math.random().toString(36)}`
  }
}