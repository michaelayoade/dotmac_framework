/**
 * Shared Business Logic Types
 * Common types used across all ISP business operations
 */

export interface DateRange {
  startDate: Date;
  endDate: Date;
}

export interface Money {
  amount: number;
  currency: string;
}

export interface UsageData {
  customerId: string;
  period: DateRange;
  downloadBytes: number;
  uploadBytes: number;
  totalBytes: number;
  peakBandwidthMbps: number;
  averageBandwidthMbps: number;
  dataAllowanceBytes?: number;
  overage?: {
    bytes: number;
    chargePerGB: number;
  };
}

export interface PricingPlan {
  id: string;
  name: string;
  type: 'residential' | 'business' | 'enterprise';
  basePrice: Money;
  features: PlanFeature[];
  limits: PlanLimits;
  tiers?: PricingTier[];
}

export interface PlanFeature {
  id: string;
  name: string;
  description: string;
  included: boolean;
  additionalCost?: Money;
}

export interface PlanLimits {
  dataAllowanceGB?: number; // unlimited if undefined
  bandwidthMbps: number;
  staticIPs?: number;
  supportLevel: 'basic' | 'standard' | 'priority' | '24x7';
  slaUptimePercent?: number;
}

export interface PricingTier {
  threshold: number; // usage threshold
  unitPrice: Money; // price per unit above threshold
  unit: 'GB' | 'TB' | 'Mbps';
}

export interface Commission {
  id: string;
  partnerId: string;
  customerId: string;
  serviceId: string;
  revenue: Money;
  commissionRate: number; // percentage (0.1 = 10%)
  commissionAmount: Money;
  period: DateRange;
  status: 'pending' | 'calculated' | 'paid' | 'disputed';
  calculatedAt: Date;
  paidAt?: Date;
  metadata: {
    planType: string;
    customerType: 'new' | 'upgrade' | 'renewal';
    paymentMethod: string;
  };
}

export interface PlatformRevenue {
  tenantId: string;
  period: DateRange;
  customerRevenue: Money;
  subscriptionRevenue: Money;
  usageRevenue: Money;
  totalRevenue: Money;
  costs: {
    infrastructure: Money;
    support: Money;
    marketing: Money;
    commissions: Money;
    total: Money;
  };
  netRevenue: Money;
  metrics: {
    totalCustomers: number;
    newCustomers: number;
    churnedCustomers: number;
    averageRevenuePerCustomer: Money;
    customerLifetimeValue: Money;
  };
}

export interface ServicePlan {
  id: string;
  name: string;
  description: string;
  category: 'residential' | 'business' | 'enterprise';
  pricing: PricingPlan;
  technical: {
    downloadSpeedMbps: number;
    uploadSpeedMbps: number;
    dataAllowanceGB?: number;
    staticIPs: number;
    equipmentIncluded: string[];
    installationFee?: Money;
  };
  availability: {
    regions: string[];
    serviceTypes: ('fiber' | 'cable' | 'dsl' | 'wireless' | 'satellite')[];
    requiresEquipment: boolean;
    requiresInstallation: boolean;
  };
  contractTerms: {
    minimumTermMonths: number;
    earlyTerminationFee?: Money;
    priceGuaranteeMonths: number;
  };
  support: {
    level: 'basic' | 'standard' | 'priority' | '24x7';
    slaUptimePercent: number;
    responseTimeHours: number;
  };
}

export interface UpgradeImpact {
  currentPlan: ServicePlan;
  targetPlan: ServicePlan;
  changes: {
    speedIncrease: {
      downloadMbps: number;
      uploadMbps: number;
    };
    dataAllowanceChange?: number; // GB change (positive = increase)
    featureChanges: {
      added: PlanFeature[];
      removed: PlanFeature[];
      modified: PlanFeature[];
    };
  };
  pricing: {
    currentMonthlyPrice: Money;
    newMonthlyPrice: Money;
    monthlyDifference: Money;
    proratedCharge?: Money;
    installationFee?: Money;
    equipmentFee?: Money;
    totalUpfrontCost: Money;
  };
  timeline: {
    effectiveDate: Date;
    estimatedActivationDate: Date;
    requiresInstallation: boolean;
    estimatedInstallationDays: number;
  };
}

export interface EligibilityResult {
  eligible: boolean;
  reasons: string[];
  requirements?: {
    creditCheck: boolean;
    equipmentUpgrade: boolean;
    serviceVisit: boolean;
    contractExtension: boolean;
  };
  restrictions?: {
    minimumContractMonths: number;
    earlyTerminationPenalty: Money;
    geographicLimitations: string[];
  };
}

export interface DiagnosticsResult {
  customerId: string;
  testRunAt: Date;
  overallStatus: 'healthy' | 'degraded' | 'failed';
  tests: {
    connectivity: TestResult;
    speed: SpeedTestResult;
    latency: LatencyTestResult;
    packetLoss: PacketLossTestResult;
    dns: DNSTestResult;
    equipment: EquipmentTestResult;
  };
  recommendations: Recommendation[];
  estimatedResolutionTime?: number; // minutes
  requiresTechnicianVisit: boolean;
}

export interface TestResult {
  status: 'pass' | 'warning' | 'fail';
  message: string;
  details?: Record<string, any>;
}

export interface SpeedTestResult extends TestResult {
  downloadSpeedMbps: number;
  uploadSpeedMbps: number;
  expectedDownloadMbps: number;
  expectedUploadMbps: number;
  speedEfficiencyPercent: number;
}

export interface LatencyTestResult extends TestResult {
  latencyMs: number;
  jitterMs: number;
  targetLatencyMs: number;
}

export interface PacketLossTestResult extends TestResult {
  packetLossPercent: number;
  targetPacketLossPercent: number;
}

export interface DNSTestResult extends TestResult {
  dnsResolutionTimeMs: number;
  dnsServers: string[];
  failedQueries: string[];
}

export interface EquipmentTestResult extends TestResult {
  equipment: {
    modem: EquipmentStatus;
    router: EquipmentStatus;
    ont?: EquipmentStatus; // for fiber
  };
}

export interface EquipmentStatus {
  model: string;
  firmwareVersion: string;
  status: 'online' | 'offline' | 'degraded';
  signalStrength?: number; // dBm
  temperature?: number; // Celsius
  uptime: number; // hours
  needsFirmwareUpdate: boolean;
}

export interface Recommendation {
  id: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  category: 'equipment' | 'configuration' | 'infrastructure' | 'service';
  title: string;
  description: string;
  estimatedImpact: 'minor' | 'moderate' | 'significant' | 'major';
  estimatedCost?: Money;
  estimatedTimeToResolve: number; // minutes
  requiresTechnician: boolean;
  canBeResolvedRemotely: boolean;
  actionRequired: string;
}

export interface ServiceRequest {
  customerId: string;
  serviceType: 'installation' | 'repair' | 'upgrade' | 'maintenance';
  planId: string;
  requestedDate?: Date;
  priority: 'routine' | 'standard' | 'urgent' | 'emergency';
  address: {
    street: string;
    city: string;
    state: string;
    zip: string;
    unit?: string;
    accessInstructions?: string;
  };
  requirements: {
    equipmentInstallation: string[];
    wiringRequired: boolean;
    specialAccess: boolean;
    customerPresenceRequired: boolean;
  };
  estimatedDuration: number; // minutes
  specialInstructions?: string;
}

export interface WorkOrder {
  id: string;
  customerId: string;
  serviceRequest: ServiceRequest;
  status: 'scheduled' | 'in_progress' | 'completed' | 'cancelled' | 'rescheduled';
  assignedTechnician?: {
    id: string;
    name: string;
    phone: string;
    skills: string[];
    certifications: string[];
  };
  scheduledDate: Date;
  estimatedArrivalWindow: {
    start: Date;
    end: Date;
  };
  actualStartTime?: Date;
  actualCompletionTime?: Date;
  materials: WorkOrderMaterial[];
  labor: WorkOrderLabor[];
  costs: {
    materials: Money;
    labor: Money;
    total: Money;
  };
  customerSignature?: {
    signedAt: Date;
    signatureData: string; // base64 encoded
  };
  notes: string[];
  photosUrls: string[];
}

export interface WorkOrderMaterial {
  itemId: string;
  description: string;
  quantity: number;
  unitCost: Money;
  totalCost: Money;
  serialNumbers?: string[];
}

export interface WorkOrderLabor {
  description: string;
  startTime: Date;
  endTime: Date;
  durationMinutes: number;
  hourlyRate: Money;
  totalCost: Money;
}

export interface ProvisioningResult {
  success: boolean;
  customerId: string;
  serviceId: string;
  provisionedAt: Date;
  activationDetails: {
    ipAddress?: string;
    accountCredentials?: {
      username: string;
      temporaryPassword: string;
      requiresPasswordChange: boolean;
    };
    equipmentInfo?: {
      modemMac: string;
      routerMac?: string;
      serialNumbers: string[];
    };
    networkConfiguration?: {
      vlan: number;
      bandwidth: string;
      staticIPs?: string[];
    };
  };
  testResults: DiagnosticsResult;
  errors?: ProvisioningError[];
}

export interface ProvisioningError {
  code: string;
  message: string;
  severity: 'warning' | 'error' | 'critical';
  resolutionSteps: string[];
  requiresManualIntervention: boolean;
}

export interface ServiceHealthReport {
  customerId: string;
  serviceId: string;
  reportDate: Date;
  overallHealth: 'excellent' | 'good' | 'fair' | 'poor' | 'critical';
  metrics: {
    uptimePercent: number;
    averageSpeedMbps: {
      download: number;
      upload: number;
    };
    averageLatencyMs: number;
    packetLossPercent: number;
    serviceInterruptions: number;
    totalDowntimeMinutes: number;
  };
  performance: {
    speedConsistency: number; // percentage
    peakUsageHours: number[];
    dataUsageGB: number;
    bandwidthUtilizationPercent: number;
  };
  issues: ServiceIssue[];
  recommendations: Recommendation[];
  slaCompliance: {
    uptimeMet: boolean;
    speedMet: boolean;
    supportResponseMet: boolean;
    overall: 'compliant' | 'minor_breach' | 'major_breach';
  };
}

export interface ServiceIssue {
  id: string;
  type: 'outage' | 'speed_degradation' | 'connectivity' | 'equipment' | 'configuration';
  severity: 'low' | 'medium' | 'high' | 'critical';
  occurredAt: Date;
  resolvedAt?: Date;
  durationMinutes: number;
  impact: string;
  rootCause?: string;
  resolution?: string;
}

// Portal-specific context types
export interface PortalContext {
  portalType: 'management-admin' | 'admin' | 'customer' | 'reseller' | 'technician';
  userId: string;
  tenantId?: string;
  permissions: string[];
  preferences?: Record<string, any>;
}

export interface BusinessLogicConfig {
  apiBaseUrl: string;
  timeout: number;
  retryAttempts: number;
  cacheTtl: number;
  features: {
    revenueCalculation: boolean;
    commissionTracking: boolean;
    servicePlanManagement: boolean;
    networkDiagnostics: boolean;
    provisioningAutomation: boolean;
  };
}
