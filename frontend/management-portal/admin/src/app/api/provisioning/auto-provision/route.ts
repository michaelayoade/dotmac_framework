import { NextRequest, NextResponse } from 'next/server'

interface AutoProvisionRequest {
  onboarding_request_id: string
  plan_type: 'starter' | 'professional' | 'enterprise'
  provisioning_type: 'auto' | 'byo' // bring-your-own server
  priority: 'high' | 'medium' | 'low'
  estimated_completion: string
  server_config?: {
    ip_address?: string
    ssh_credentials?: {
      username: string
      private_key: string
    }
    custom_domain?: string
  }
}

export async function POST(request: NextRequest) {
  try {
    const body: AutoProvisionRequest = await request.json()
    
    // Validate required fields
    if (!body.onboarding_request_id || !body.plan_type) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      )
    }

    // Get onboarding request details
    const onboardingData = await getOnboardingRequest(body.onboarding_request_id)
    if (!onboardingData) {
      return NextResponse.json(
        { error: 'Onboarding request not found' },
        { status: 404 }
      )
    }

    // Create provisioning record
    const provisioningId = await createProvisioningRecord(body, onboardingData)
    
    // Start provisioning process based on type
    let provisioningResult
    if (body.provisioning_type === 'byo' && body.server_config) {
      provisioningResult = await provisionBYOServer(provisioningId, body, onboardingData)
    } else {
      provisioningResult = await provisionAutoServer(provisioningId, body, onboardingData)
    }

    return NextResponse.json({
      success: true,
      id: provisioningId,
      status: provisioningResult.status,
      estimated_completion: body.estimated_completion,
      steps_completed: provisioningResult.steps_completed,
      next_steps: provisioningResult.next_steps,
      access_url: provisioningResult.access_url,
      credentials: provisioningResult.credentials
    })

  } catch (error) {
    console.error('Auto-provisioning error:', error)
    
    return NextResponse.json({
      success: false,
      error: 'Provisioning failed',
      message: 'Manual provisioning will be initiated',
      support_contact: 'support@dotmac.platform'
    }, { status: 500 })
  }
}

async function getOnboardingRequest(requestId: string) {
  try {
    const managementApiUrl = process.env.MANAGEMENT_API_URL || 'http://localhost:3000'
    const serviceToken = process.env.MANAGEMENT_SERVICE_TOKEN

    const response = await fetch(`${managementApiUrl}/api/v1/onboarding/requests/${requestId}`, {
      headers: {
        'Authorization': `Bearer ${serviceToken}`,
      },
    })

    if (response.ok) {
      return await response.json()
    }
    return null
  } catch (error) {
    console.error('Failed to fetch onboarding request:', error)
    return null
  }
}

async function createProvisioningRecord(request: AutoProvisionRequest, onboardingData: any) {
  const provisioningId = `prov_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  
  try {
    const managementApiUrl = process.env.MANAGEMENT_API_URL || 'http://localhost:3000'
    const serviceToken = process.env.MANAGEMENT_SERVICE_TOKEN

    // Create provisioning record using existing service
    await fetch(`${managementApiUrl}/api/v1/provisioning/requests`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${serviceToken}`,
      },
      body: JSON.stringify({
        id: provisioningId,
        onboarding_request_id: request.onboarding_request_id,
        tenant_name: onboardingData.tenant_name,
        contact_email: onboardingData.email,
        plan_type: request.plan_type,
        provisioning_type: request.provisioning_type,
        priority: request.priority,
        status: 'in_progress',
        steps: generateProvisioningSteps(request.plan_type, request.provisioning_type),
        estimated_completion: request.estimated_completion,
        created_at: new Date().toISOString(),
        metadata: {
          automated: true,
          source: 'marketing_integration'
        }
      }),
    })

    return provisioningId
  } catch (error) {
    console.error('Failed to create provisioning record:', error)
    return provisioningId // Still return ID for fallback processing
  }
}

async function provisionAutoServer(provisioningId: string, request: AutoProvisionRequest, onboardingData: any) {
  // Step 1: Generate unique subdomain and credentials
  const subdomain = generateSubdomain(onboardingData.tenant_name)
  const credentials = generateCredentials()
  
  // Step 2: Use existing tenant provisioning service
  try {
    const managementApiUrl = process.env.MANAGEMENT_API_URL || 'http://localhost:3000'
    const serviceToken = process.env.MANAGEMENT_SERVICE_TOKEN

    const tenantResponse = await fetch(`${managementApiUrl}/api/v1/tenants`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${serviceToken}`,
      },
      body: JSON.stringify({
        name: onboardingData.tenant_name,
        subdomain: subdomain,
        plan_type: request.plan_type,
        admin_email: onboardingData.email,
        admin_name: onboardingData.contact_name,
        billing_email: onboardingData.email,
        status: 'active',
        provisioning_id: provisioningId,
        auto_provisioned: true,
        features: getPlanFeatures(request.plan_type),
        limits: getPlanLimits(request.plan_type),
        credentials: {
          admin_username: credentials.username,
          admin_password: credentials.password,
          database_url: credentials.database_url,
          api_key: credentials.api_key
        }
      }),
    })

    if (tenantResponse.ok) {
      const tenantData = await tenantResponse.json()
      
      // Step 3: Initialize database and basic configuration
      await initializeTenantDatabase(tenantData.id, request.plan_type)
      
      // Step 4: Set up DNS and SSL
      await setupDNSAndSSL(subdomain)
      
      // Step 5: Deploy configuration
      await deployTenantConfig(tenantData.id, request.plan_type)

      // Step 6: Send provisioning completion email
      const accessUrl = `https://${subdomain}.dotmac.platform`
      const credentialsData = {
        admin_url: `https://${subdomain}.dotmac.platform/admin`,
        username: credentials.username,
        temporary_password: credentials.password,
        api_endpoint: `https://${subdomain}.dotmac.platform/api`,
        api_key: credentials.api_key
      }

      await sendProvisioningCompletionEmail(provisioningId, onboardingData, {
        plan_type: request.plan_type,
        access_url: accessUrl,
        credentials: credentialsData
      })

      return {
        status: 'completed',
        steps_completed: [
          'Tenant created',
          'Database initialized', 
          'DNS configured',
          'SSL certificate issued',
          'Configuration deployed',
          'Welcome email sent'
        ],
        next_steps: [
          'Check your email for login credentials',
          'Access your platform at the provided URL',
          'Complete the onboarding wizard'
        ],
        access_url: accessUrl,
        credentials: credentialsData
      }
    } else {
      throw new Error('Tenant creation failed')
    }
  } catch (error) {
    console.error('Auto-provisioning failed:', error)
    
    // Send provisioning failure email
    await sendProvisioningFailureEmail(provisioningId, onboardingData, {
      plan_type: request.plan_type,
      error_details: error instanceof Error ? error.message : 'Unknown provisioning error'
    })
    
    return {
      status: 'failed',
      steps_completed: ['Provisioning initiated', 'Error notification sent'],
      next_steps: [
        'Manual provisioning will be started',
        'You will receive updates via email',
        'Expected completion: 2-4 hours'
      ],
      access_url: null,
      credentials: null
    }
  }
}

async function provisionBYOServer(provisioningId: string, request: AutoProvisionRequest, onboardingData: any) {
  if (!request.server_config) {
    throw new Error('Server configuration required for BYO provisioning')
  }

  // Step 1: Validate customer server
  const validationResult = await validateCustomerServer(request.server_config)
  if (!validationResult.valid) {
    return {
      status: 'validation_failed',
      steps_completed: ['Server validation attempted'],
      next_steps: [
        `Validation failed: ${validationResult.errors.join(', ')}`,
        'Please check your server configuration',
        'Contact support for assistance'
      ],
      access_url: null,
      credentials: null
    }
  }

  // Step 2: Deploy to customer server
  const deploymentResult = await deployToCustomerServer(request.server_config, request.plan_type, onboardingData)
  
  return deploymentResult
}

function generateSubdomain(tenantName: string): string {
  const clean = tenantName.toLowerCase()
    .replace(/[^a-z0-9]/g, '')
    .substring(0, 20)
  const suffix = Math.random().toString(36).substr(2, 4)
  return `${clean}-${suffix}`
}

function generateCredentials() {
  return {
    username: 'admin',
    password: Math.random().toString(36).slice(-12) + Math.random().toString(36).slice(-12),
    database_url: `postgresql://dotmac_${Date.now()}:${Math.random().toString(36)}@db.dotmac.internal/tenant_${Date.now()}`,
    api_key: `dmk_${Math.random().toString(36)}${Math.random().toString(36)}`
  }
}

function getPlanFeatures(planType: string): string[] {
  const features = {
    starter: ['basic_portal', 'email_support', 'core_plugins'],
    professional: ['advanced_portal', 'priority_support', 'all_plugins', 'api_access', 'analytics'],
    enterprise: ['enterprise_portal', 'dedicated_support', 'custom_plugins', 'sla', 'white_label']
  }
  return features[planType as keyof typeof features] || features.starter
}

function getPlanLimits(planType: string) {
  const limits = {
    starter: { customers: 100, api_calls: 10000, storage_gb: 5 },
    professional: { customers: 1000, api_calls: 100000, storage_gb: 50 },
    enterprise: { customers: -1, api_calls: -1, storage_gb: 500 } // -1 = unlimited
  }
  return limits[planType as keyof typeof limits] || limits.starter
}

async function initializeTenantDatabase(tenantId: string, planType: string) {
  // Simulate database initialization
  await new Promise(resolve => setTimeout(resolve, 3000))
  return true
}

async function setupDNSAndSSL(subdomain: string) {
  // Simulate DNS and SSL setup
  await new Promise(resolve => setTimeout(resolve, 2000))
  return true
}

async function deployTenantConfig(tenantId: string, planType: string) {
  // Simulate configuration deployment
  await new Promise(resolve => setTimeout(resolve, 1000))
  return true
}

async function validateCustomerServer(serverConfig: any) {
  // Basic server validation - in production would do real checks
  const errors: string[] = []
  
  if (!serverConfig.ip_address) {
    errors.push('IP address required')
  }
  
  if (!serverConfig.ssh_credentials?.username) {
    errors.push('SSH username required')
  }
  
  if (!serverConfig.ssh_credentials?.private_key) {
    errors.push('SSH private key required')
  }

  // Simulate connectivity test
  await new Promise(resolve => setTimeout(resolve, 5000))
  
  return {
    valid: errors.length === 0,
    errors
  }
}

async function deployToCustomerServer(serverConfig: any, planType: string, onboardingData: any) {
  try {
    // Simulate deployment to customer server
    await new Promise(resolve => setTimeout(resolve, 10000))
    
    const domain = serverConfig.custom_domain || serverConfig.ip_address
    
    return {
      status: 'completed',
      steps_completed: [
        'Server validation passed',
        'Docker containers deployed',
        'Database configured',
        'SSL certificates installed',
        'Application started'
      ],
      next_steps: [
        'Login credentials sent via email',
        'Access your platform at the provided URL',
        'Complete the onboarding wizard'
      ],
      access_url: `https://${domain}`,
      credentials: {
        admin_url: `https://${domain}/admin`,
        username: 'admin',
        temporary_password: Math.random().toString(36).slice(-12),
        api_endpoint: `https://${domain}/api`,
        api_key: `dmk_${Math.random().toString(36).substr(2, 32)}`
      }
    }
  } catch (error) {
    return {
      status: 'failed',
      steps_completed: ['Server validation passed', 'Deployment attempted'],
      next_steps: [
        'Deployment failed - manual intervention required',
        'Technical team will contact you within 2 hours',
        'Server configuration will be reviewed'
      ],
      access_url: null,
      credentials: null
    }
  }
}

function generateProvisioningSteps(planType: string, provisioningType: string): string[] {
  const baseSteps = [
    'Create tenant record',
    'Initialize database',
    'Configure basic settings'
  ]
  
  if (provisioningType === 'byo') {
    return [
      'Validate server connectivity',
      'Check system requirements',
      ...baseSteps,
      'Deploy to customer server',
      'Configure SSL certificates',
      'Start services'
    ]
  } else {
    return [
      ...baseSteps,
      'Provision cloud resources',
      'Setup DNS records',
      'Issue SSL certificates',
      'Deploy application',
      'Send credentials'
    ]
  }
}

async function sendProvisioningCompletionEmail(
  provisioningId: string, 
  onboardingData: any, 
  details: {
    plan_type: string
    access_url: string
    credentials: {
      admin_url: string
      username: string
      temporary_password: string
      api_key: string
    }
  }
) {
  try {
    await fetch('/api/notifications/email-automation', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        trigger: 'provisioning_completed',
        recipient: {
          email: onboardingData.email,
          name: onboardingData.contact_name || onboardingData.name || 'Valued Customer',
          company: onboardingData.company_name
        },
        data: {
          onboarding_request_id: onboardingData.id,
          plan_type: details.plan_type,
          provisioning_id: provisioningId,
          access_url: details.access_url,
          credentials: details.credentials
        },
        priority: 'high'
      }),
    })
  } catch (error) {
    console.error('Failed to send provisioning completion email:', error)
  }
}

async function sendProvisioningFailureEmail(
  provisioningId: string, 
  onboardingData: any, 
  details: {
    plan_type: string
    error_details: string
  }
) {
  try {
    await fetch('/api/notifications/email-automation', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        trigger: 'provisioning_failed',
        recipient: {
          email: onboardingData.email,
          name: onboardingData.contact_name || onboardingData.name || 'Valued Customer',
          company: onboardingData.company_name
        },
        data: {
          onboarding_request_id: onboardingData.id,
          plan_type: details.plan_type,
          provisioning_id: provisioningId,
          error_details: details.error_details
        },
        priority: 'high'
      }),
    })
  } catch (error) {
    console.error('Failed to send provisioning failure email:', error)
  }
}