'use client'

import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { CheckCircle2, AlertCircle, Loader2, Copy, ExternalLink } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'

interface DNSRecord {
  name: string
  type: string
  content: string
  ttl: number
}

interface DomainSetupResponse {
  success: boolean
  message: string
  tenant_id: string
  domain: string
  required_dns_records: DNSRecord[]
  verification_status: string
  next_steps: string[]
}

interface DomainVerificationResponse {
  success: boolean
  message: string
  domain: string
  verification_details: {
    verification_method: string
    records_found: string[]
    records_missing?: string[]
    error?: string
  }
  ssl_ready: boolean
}

interface TenantDomainStatus {
  tenant_id: string
  primary_domain: string
  custom_domains: string[]
  subdomain_health: Record<string, boolean>
  ssl_certificates: any[]
}

export function DomainManagement({ tenantId }: { tenantId: string }) {
  const [domain, setDomain] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [setupResult, setSetupResult] = useState<DomainSetupResponse | null>(null)
  const [verificationResult, setVerificationResult] = useState<DomainVerificationResponse | null>(null)
  const [domainStatus, setDomainStatus] = useState<TenantDomainStatus | null>(null)
  const [activeTab, setActiveTab] = useState('setup')
  
  const { toast } = useToast()

  // Load domain status on component mount
  useEffect(() => {
    loadDomainStatus()
  }, [tenantId])

  const loadDomainStatus = async () => {
    try {
      const response = await fetch(`/api/v1/domains/tenant/${tenantId}/status`)
      if (response.ok) {
        const status = await response.json()
        setDomainStatus(status)
      }
    } catch (error) {
      console.error('Failed to load domain status:', error)
    }
  }

  const handleDomainSetup = async () => {
    if (!domain.trim()) {
      toast({
        title: "Error",
        description: "Please enter a domain name",
        variant: "destructive"
      })
      return
    }

    setIsLoading(true)
    try {
      const response = await fetch('/api/v1/domains/setup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          domain: domain.trim(),
          tenant_id: tenantId
        })
      })

      const result = await response.json()
      
      if (response.ok && result.success) {
        setSetupResult(result)
        setActiveTab('dns-records')
        toast({
          title: "Domain Setup Initiated",
          description: `DNS records generated for ${domain}`,
        })
      } else {
        toast({
          title: "Setup Failed", 
          description: result.message || 'Failed to setup domain',
          variant: "destructive"
        })
      }
    } catch (error) {
      toast({
        title: "Network Error",
        description: "Failed to communicate with the server",
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleDomainVerification = async () => {
    if (!setupResult?.domain) return

    setIsLoading(true)
    try {
      const response = await fetch('/api/v1/domains/verify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          domain: setupResult.domain
        })
      })

      const result = await response.json()
      setVerificationResult(result)
      
      if (result.success) {
        toast({
          title: "Domain Verified!",
          description: `${setupResult.domain} has been verified successfully`,
        })
        setActiveTab('status')
        await loadDomainStatus()
      } else {
        toast({
          title: "Verification Failed",
          description: result.message,
          variant: "destructive"
        })
      }
    } catch (error) {
      toast({
        title: "Verification Error",
        description: "Failed to verify domain",
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast({
      title: "Copied!",
      description: "DNS record copied to clipboard",
    })
  }

  const renderDNSRecords = () => {
    if (!setupResult?.required_dns_records) return null

    return (
      <div className="space-y-4">
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Add these DNS records to your domain `{setupResult.domain}` in your domain registrar's control panel:
          </AlertDescription>
        </Alert>
        
        {setupResult.required_dns_records.map((record, index) => (
          <Card key={index} className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <Badge variant="outline">{record.type}</Badge>
                  <span className="font-mono text-sm">{record.name}</span>
                </div>
                <div className="font-mono text-sm text-gray-600 bg-gray-50 p-2 rounded">
                  {record.content}
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => copyToClipboard(record.content)}
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </Card>
        ))}

        <div className="mt-6">
          <h4 className="font-medium mb-2">Next Steps:</h4>
          <ol className="list-decimal list-inside space-y-1 text-sm text-gray-600">
            {setupResult.next_steps.map((step, index) => (
              <li key={index}>{step}</li>
            ))}
          </ol>
        </div>

        <Button 
          onClick={handleDomainVerification}
          disabled={isLoading}
          className="w-full"
        >
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Verifying...
            </>
          ) : (
            'Verify Domain'
          )}
        </Button>
      </div>
    )
  }

  const renderDomainStatus = () => {
    if (!domainStatus) return <div>Loading domain status...</div>

    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Primary Domain</CardTitle>
            <CardDescription>Your default tenant domain</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <span className="font-mono">{domainStatus.primary_domain}</span>
              <a 
                href={`https://${domainStatus.primary_domain}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center text-sm text-blue-600 hover:text-blue-800"
              >
                Visit <ExternalLink className="ml-1 h-3 w-3" />
              </a>
            </div>
          </CardContent>
        </Card>

        {domainStatus.custom_domains.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Custom Domains</CardTitle>
              <CardDescription>Your configured custom domains</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {domainStatus.custom_domains.map((customDomain, index) => (
                  <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                    <span className="font-mono">{customDomain}</span>
                    <a 
                      href={`https://${customDomain}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center text-sm text-blue-600 hover:text-blue-800"
                    >
                      Visit <ExternalLink className="ml-1 h-3 w-3" />
                    </a>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Subdomain Health</CardTitle>
            <CardDescription>DNS resolution status for your subdomains</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {Object.entries(domainStatus.subdomain_health).map(([subdomain, isHealthy]) => (
                <div key={subdomain} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                  <span className="font-mono text-sm">{subdomain}</span>
                  {isHealthy ? (
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-red-600" />
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Domain Management</h1>
        <p className="text-gray-600 mt-2">
          Configure custom domains for your ISP platform
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="setup">Domain Setup</TabsTrigger>
          <TabsTrigger value="dns-records">DNS Configuration</TabsTrigger>
          <TabsTrigger value="status">Status & Health</TabsTrigger>
        </TabsList>

        <TabsContent value="setup" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Add Custom Domain</CardTitle>
              <CardDescription>
                Configure a custom domain to brand your ISP portals (e.g., portal.yourcompany.com)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-4">
                <Input
                  placeholder="portal.yourcompany.com"
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                  disabled={isLoading}
                  className="flex-1"
                />
                <Button 
                  onClick={handleDomainSetup}
                  disabled={isLoading || !domain.trim()}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Setting up...
                    </>
                  ) : (
                    'Setup Domain'
                  )}
                </Button>
              </div>
              
              <div className="text-sm text-gray-600">
                <p>Examples:</p>
                <ul className="list-disc list-inside mt-1 space-y-1">
                  <li><code>portal.acmeisp.com</code> - Customer portal</li>
                  <li><code>admin.acmeisp.com</code> - Admin interface</li>
                  <li><code>billing.acmeisp.com</code> - Billing portal</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="dns-records" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>DNS Configuration</CardTitle>
              <CardDescription>
                Configure these DNS records in your domain registrar's control panel
              </CardDescription>
            </CardHeader>
            <CardContent>
              {renderDNSRecords()}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="status" className="space-y-6">
          {renderDomainStatus()}
        </TabsContent>
      </Tabs>

      {verificationResult && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {verificationResult.success ? (
                <CheckCircle2 className="h-5 w-5 text-green-600" />
              ) : (
                <AlertCircle className="h-5 w-5 text-red-600" />
              )}
              Verification Result
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="mb-4">{verificationResult.message}</p>
            {verificationResult.verification_details && (
              <div className="space-y-2 text-sm">
                <div><strong>Method:</strong> {verificationResult.verification_details.verification_method}</div>
                {verificationResult.verification_details.records_found.length > 0 && (
                  <div>
                    <strong>Records Found:</strong>
                    <ul className="list-disc list-inside ml-4">
                      {verificationResult.verification_details.records_found.map((record, index) => (
                        <li key={index} className="font-mono">{record}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {verificationResult.verification_details.records_missing && (
                  <div>
                    <strong>Missing Records:</strong>
                    <ul className="list-disc list-inside ml-4 text-red-600">
                      {verificationResult.verification_details.records_missing.map((record, index) => (
                        <li key={index} className="font-mono">{record}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default DomainManagement