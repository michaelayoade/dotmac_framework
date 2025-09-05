import { NextRequest, NextResponse } from 'next/server'

interface ServerValidationRequest {
  ip_address: string
  ssh_credentials: {
    username: string
    private_key: string
    port?: number
  }
  custom_domain?: string
  plan_type: 'starter' | 'professional' | 'enterprise'
}

interface ValidationResult {
  valid: boolean
  score: number // 0-100, higher is better
  errors: string[]
  warnings: string[]
  recommendations: string[]
  system_info?: {
    os: string
    arch: string
    memory_gb: number
    storage_gb: number
    cpu_cores: number
    docker_version?: string
    network_speed?: string
  }
  estimated_setup_time?: string
}

export async function POST(request: NextRequest) {
  try {
    const body: ServerValidationRequest = await request.json()
    
    // Validate required fields
    if (!body.ip_address || !body.ssh_credentials?.username || !body.ssh_credentials?.private_key) {
      return NextResponse.json({
        valid: false,
        score: 0,
        errors: ['Missing required fields: ip_address, ssh_credentials.username, ssh_credentials.private_key'],
        warnings: [],
        recommendations: []
      }, { status: 400 })
    }

    const validationResult = await performServerValidation(body)
    
    return NextResponse.json(validationResult)

  } catch (error) {
    console.error('Server validation error:', error)
    
    return NextResponse.json({
      valid: false,
      score: 0,
      errors: ['Server validation service temporarily unavailable'],
      warnings: [],
      recommendations: ['Please try again in a few minutes or contact support'],
      estimated_setup_time: '2-4 hours (manual setup)'
    }, { status: 500 })
  }
}

async function performServerValidation(config: ServerValidationRequest): Promise<ValidationResult> {
  const errors: string[] = []
  const warnings: string[] = []
  const recommendations: string[] = []
  let score = 100
  let systemInfo: ValidationResult['system_info']

  // Basic format validation
  const ipValidation = validateIPAddress(config.ip_address)
  if (!ipValidation.valid) {
    errors.push(ipValidation.error!)
    score -= 25
  }

  // SSH credentials validation
  const sshValidation = validateSSHCredentials(config.ssh_credentials)
  if (!sshValidation.valid) {
    errors.push(...sshValidation.errors)
    score -= 30
  }

  // Domain validation (if provided)
  if (config.custom_domain) {
    const domainValidation = validateDomain(config.custom_domain)
    if (!domainValidation.valid) {
      warnings.push(domainValidation.warning!)
      score -= 10
    }
  }

  // Simulate SSH connection and system checks
  try {
    await new Promise(resolve => setTimeout(resolve, 3000)) // Simulate connection time
    
    // Simulate system information gathering
    systemInfo = await simulateSystemInfo(config)
    
    // Validate system requirements based on plan
    const sysReqValidation = validateSystemRequirements(systemInfo, config.plan_type)
    errors.push(...sysReqValidation.errors)
    warnings.push(...sysReqValidation.warnings)
    recommendations.push(...sysReqValidation.recommendations)
    score -= sysReqValidation.penalty

    // Network connectivity tests
    const networkValidation = await validateNetworkConnectivity(config.ip_address)
    if (!networkValidation.valid) {
      warnings.push(...networkValidation.warnings)
      score -= 15
    }

    // Docker availability check
    const dockerValidation = validateDockerSetup(systemInfo)
    if (!dockerValidation.valid) {
      if (dockerValidation.critical) {
        errors.push(dockerValidation.error!)
        score -= 25
      } else {
        warnings.push(dockerValidation.warning!)
        recommendations.push('Docker will be installed during setup')
        score -= 5
      }
    }

  } catch (connectionError) {
    errors.push('Unable to establish SSH connection to server')
    recommendations.push('Check that SSH service is running and credentials are correct')
    score -= 40
  }

  // Final scoring and validation
  const isValid = errors.length === 0 && score >= 60

  // Generate setup time estimate
  const estimatedTime = calculateSetupTime(score, config.plan_type, systemInfo)

  return {
    valid: isValid,
    score: Math.max(0, score),
    errors,
    warnings,
    recommendations,
    system_info: systemInfo,
    estimated_setup_time: estimatedTime
  }
}

function validateIPAddress(ip: string): { valid: boolean; error?: string } {
  const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/
  
  if (!ipRegex.test(ip)) {
    return { valid: false, error: 'Invalid IP address format' }
  }

  // Check for private/local IPs that might not be accessible
  const privateRanges = [
    /^10\./,
    /^192\.168\./,
    /^172\.(1[6-9]|2[0-9]|3[0-1])\./,
    /^127\./,
    /^169\.254\./
  ]

  const isPrivate = privateRanges.some(range => range.test(ip))
  if (isPrivate) {
    return { valid: false, error: 'Private IP addresses are not accessible for deployment. Please use a public IP.' }
  }

  return { valid: true }
}

function validateSSHCredentials(creds: ServerValidationRequest['ssh_credentials']): { valid: boolean; errors: string[] } {
  const errors: string[] = []

  if (!creds.username || creds.username.length < 1) {
    errors.push('SSH username is required')
  }

  if (!creds.private_key || creds.private_key.length < 100) {
    errors.push('SSH private key appears to be invalid or too short')
  }

  // Basic private key format validation
  if (creds.private_key && !creds.private_key.includes('-----BEGIN') && !creds.private_key.includes('-----END')) {
    errors.push('SSH private key format appears to be invalid')
  }

  if (creds.port && (creds.port < 1 || creds.port > 65535)) {
    errors.push('SSH port must be between 1 and 65535')
  }

  return { valid: errors.length === 0, errors }
}

function validateDomain(domain: string): { valid: boolean; warning?: string } {
  const domainRegex = /^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9](?:\.[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9])*$/
  
  if (!domainRegex.test(domain)) {
    return { valid: false, warning: `Custom domain "${domain}" format appears invalid` }
  }

  return { valid: true }
}

async function simulateSystemInfo(config: ServerValidationRequest): Promise<ValidationResult['system_info']> {
  // Simulate gathering system information via SSH
  const osOptions = ['Ubuntu 22.04', 'Ubuntu 20.04', 'CentOS 8', 'Debian 11', 'Amazon Linux 2']
  const archOptions = ['x86_64', 'aarch64']
  
  return {
    os: osOptions[Math.floor(Math.random() * osOptions.length)],
    arch: archOptions[Math.floor(Math.random() * archOptions.length)],
    memory_gb: Math.floor(Math.random() * 16) + 2, // 2-18 GB
    storage_gb: Math.floor(Math.random() * 200) + 50, // 50-250 GB
    cpu_cores: Math.floor(Math.random() * 8) + 1, // 1-8 cores
    docker_version: Math.random() > 0.3 ? '20.10.17' : undefined,
    network_speed: '1 Gbps'
  }
}

function validateSystemRequirements(systemInfo: ValidationResult['system_info'], planType: string): {
  errors: string[]
  warnings: string[]
  recommendations: string[]
  penalty: number
} {
  const errors: string[] = []
  const warnings: string[] = []
  const recommendations: string[] = []
  let penalty = 0

  if (!systemInfo) {
    errors.push('Unable to gather system information')
    return { errors, warnings, recommendations, penalty: 50 }
  }

  const requirements = getPlanRequirements(planType)

  // Memory check
  if (systemInfo.memory_gb < requirements.min_memory_gb) {
    errors.push(`Insufficient memory: ${systemInfo.memory_gb}GB available, ${requirements.min_memory_gb}GB required`)
    penalty += 30
  } else if (systemInfo.memory_gb < requirements.recommended_memory_gb) {
    warnings.push(`Memory below recommended: ${systemInfo.memory_gb}GB available, ${requirements.recommended_memory_gb}GB recommended`)
    recommendations.push('Consider upgrading memory for better performance')
    penalty += 10
  }

  // Storage check
  if (systemInfo.storage_gb < requirements.min_storage_gb) {
    errors.push(`Insufficient storage: ${systemInfo.storage_gb}GB available, ${requirements.min_storage_gb}GB required`)
    penalty += 25
  }

  // CPU check
  if (systemInfo.cpu_cores < requirements.min_cpu_cores) {
    warnings.push(`Low CPU count: ${systemInfo.cpu_cores} cores available, ${requirements.min_cpu_cores} recommended`)
    recommendations.push('Performance may be impacted with fewer CPU cores')
    penalty += 15
  }

  // OS compatibility check
  const supportedOS = ['Ubuntu', 'Debian', 'CentOS', 'Amazon Linux']
  const isSupported = supportedOS.some(os => systemInfo.os.includes(os))
  
  if (!isSupported) {
    warnings.push(`Operating system "${systemInfo.os}" is not officially supported`)
    recommendations.push('Consider using Ubuntu 22.04 LTS for best compatibility')
    penalty += 20
  }

  return { errors, warnings, recommendations, penalty }
}

function getPlanRequirements(planType: string) {
  const requirements = {
    starter: {
      min_memory_gb: 2,
      recommended_memory_gb: 4,
      min_storage_gb: 20,
      min_cpu_cores: 1
    },
    professional: {
      min_memory_gb: 4,
      recommended_memory_gb: 8,
      min_storage_gb: 50,
      min_cpu_cores: 2
    },
    enterprise: {
      min_memory_gb: 8,
      recommended_memory_gb: 16,
      min_storage_gb: 100,
      min_cpu_cores: 4
    }
  }
  
  return requirements[planType as keyof typeof requirements] || requirements.starter
}

async function validateNetworkConnectivity(ip: string): Promise<{ valid: boolean; warnings: string[] }> {
  // Simulate network connectivity tests
  await new Promise(resolve => setTimeout(resolve, 2000))
  
  const warnings: string[] = []
  const tests = [
    { name: 'HTTP (port 80)', success: Math.random() > 0.1 },
    { name: 'HTTPS (port 443)', success: Math.random() > 0.1 },
    { name: 'SSH (port 22)', success: Math.random() > 0.05 },
    { name: 'DNS Resolution', success: Math.random() > 0.05 }
  ]

  tests.forEach(test => {
    if (!test.success) {
      warnings.push(`${test.name} connectivity issue detected`)
    }
  })

  return { valid: warnings.length < 2, warnings }
}

function validateDockerSetup(systemInfo: ValidationResult['system_info']): {
  valid: boolean
  critical: boolean
  error?: string
  warning?: string
} {
  if (!systemInfo?.docker_version) {
    return {
      valid: false,
      critical: false,
      warning: 'Docker not detected - will be installed during setup'
    }
  }

  // Check Docker version compatibility
  const version = systemInfo.docker_version
  const majorVersion = parseInt(version.split('.')[0])
  
  if (majorVersion < 20) {
    return {
      valid: false,
      critical: true,
      error: `Docker version ${version} is too old. Version 20+ required.`
    }
  }

  return { valid: true, critical: false }
}

function calculateSetupTime(score: number, planType: string, systemInfo?: ValidationResult['system_info']): string {
  let baseMinutes = 30 // Base setup time

  // Adjust based on plan complexity
  switch (planType) {
    case 'enterprise':
      baseMinutes = 60
      break
    case 'professional':
      baseMinutes = 45
      break
    case 'starter':
    default:
      baseMinutes = 30
      break
  }

  // Adjust based on score
  if (score < 70) {
    baseMinutes += 30 // Additional time for issues
  }
  
  // Adjust based on system requirements
  if (systemInfo && !systemInfo.docker_version) {
    baseMinutes += 15 // Docker installation time
  }

  const hours = Math.floor(baseMinutes / 60)
  const minutes = baseMinutes % 60

  if (hours > 0) {
    return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`
  } else {
    return `${minutes}m`
  }
}