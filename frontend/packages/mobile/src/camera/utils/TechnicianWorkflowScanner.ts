import { BarcodeResult, BarcodeFormat } from '../types';

export type WorkflowType =
  | 'equipment_serial'
  | 'work_order'
  | 'location_qr'
  | 'inventory_check'
  | 'customer_account'
  | 'maintenance_tag';

export interface WorkflowScanResult {
  type: WorkflowType;
  data: string;
  parsedData: any;
  isValid: boolean;
  confidence: number;
  metadata?: {
    timestamp: number;
    location?: GeolocationPosition;
    workOrder?: string;
    technician?: string;
  };
}

export interface ValidationRule {
  pattern: RegExp;
  validator?: (data: string) => boolean;
  parser?: (data: string) => any;
  minLength?: number;
  maxLength?: number;
  requiredFormat?: BarcodeFormat[];
}

export class TechnicianWorkflowScanner {
  private static validationRules: Record<WorkflowType, ValidationRule> = {
    equipment_serial: {
      pattern: /^[A-Z0-9]{8,20}$/,
      minLength: 8,
      maxLength: 20,
      requiredFormat: ['CODE_128', 'CODE_39', 'QR_CODE'],
      parser: (data: string) => ({
        serialNumber: data.trim().toUpperCase(),
        manufacturer: TechnicianWorkflowScanner.extractManufacturer(data),
        model: TechnicianWorkflowScanner.extractModel(data)
      })
    },

    work_order: {
      pattern: /^WO[0-9]{6,12}$/,
      minLength: 8,
      maxLength: 14,
      requiredFormat: ['QR_CODE', 'CODE_128'],
      parser: (data: string) => ({
        workOrderId: data,
        number: data.substring(2),
        prefix: 'WO'
      })
    },

    location_qr: {
      pattern: /^LOC:[A-Z0-9-]+:[A-Z0-9-]+$/,
      requiredFormat: ['QR_CODE'],
      parser: (data: string) => {
        const parts = data.split(':');
        return {
          type: 'location',
          building: parts[1],
          room: parts[2],
          fullCode: data
        };
      }
    },

    inventory_check: {
      pattern: /^INV[0-9]{8}$/,
      minLength: 11,
      maxLength: 11,
      requiredFormat: ['CODE_128', 'EAN_13'],
      parser: (data: string) => ({
        inventoryId: data,
        itemNumber: data.substring(3)
      })
    },

    customer_account: {
      pattern: /^CUST[0-9]{6,10}$/,
      minLength: 10,
      maxLength: 14,
      requiredFormat: ['QR_CODE', 'CODE_128'],
      parser: (data: string) => ({
        customerId: data,
        accountNumber: data.substring(4)
      })
    },

    maintenance_tag: {
      pattern: /^MAINT:[0-9]{4}-[0-9]{2}-[0-9]{2}:[A-Z0-9]+$/,
      requiredFormat: ['QR_CODE'],
      parser: (data: string) => {
        const parts = data.split(':');
        return {
          type: 'maintenance',
          date: parts[1],
          equipmentId: parts[2],
          fullTag: data
        };
      }
    }
  };

  static analyzeBarcode(result: BarcodeResult): WorkflowScanResult[] {
    const analyses: WorkflowScanResult[] = [];

    // Try to match against each workflow type
    for (const [workflowType, rule] of Object.entries(this.validationRules)) {
      const analysis = this.validateAgainstRule(
        result,
        workflowType as WorkflowType,
        rule
      );

      if (analysis.confidence > 0.3) { // Only include reasonably confident matches
        analyses.push(analysis);
      }
    }

    // Sort by confidence (highest first)
    return analyses.sort((a, b) => b.confidence - a.confidence);
  }

  private static validateAgainstRule(
    result: BarcodeResult,
    workflowType: WorkflowType,
    rule: ValidationRule
  ): WorkflowScanResult {
    let confidence = 0;
    let isValid = false;
    let parsedData: any = null;

    const data = result.data.trim();

    // Check format requirements
    if (rule.requiredFormat && !rule.requiredFormat.includes(result.format)) {
      confidence -= 0.3;
    } else if (rule.requiredFormat?.includes(result.format)) {
      confidence += 0.2;
    }

    // Check length requirements
    if (rule.minLength && data.length < rule.minLength) {
      confidence -= 0.4;
    } else if (rule.maxLength && data.length > rule.maxLength) {
      confidence -= 0.4;
    } else if (rule.minLength && rule.maxLength &&
               data.length >= rule.minLength && data.length <= rule.maxLength) {
      confidence += 0.3;
    }

    // Check pattern match
    if (rule.pattern.test(data)) {
      confidence += 0.5;
      isValid = true;

      // Parse data if parser is available
      if (rule.parser) {
        try {
          parsedData = rule.parser(data);
          confidence += 0.1;
        } catch (error) {
          console.warn('Failed to parse data:', error);
          confidence -= 0.2;
        }
      }
    }

    // Additional validation
    if (rule.validator) {
      try {
        if (rule.validator(data)) {
          confidence += 0.2;
        } else {
          confidence -= 0.3;
          isValid = false;
        }
      } catch (error) {
        confidence -= 0.2;
      }
    }

    // Quality bonus from original barcode result
    confidence += (result.quality - 0.5) * 0.2;

    // Clamp confidence between 0 and 1
    confidence = Math.max(0, Math.min(1, confidence));

    return {
      type: workflowType,
      data: result.data,
      parsedData: parsedData || { raw: data },
      isValid,
      confidence,
      metadata: {
        timestamp: result.timestamp,
        // Additional metadata can be added here
      }
    };
  }

  static createWorkOrderQR(workOrderId: string, customerInfo?: any): string {
    const qrData = {
      type: 'work_order',
      id: workOrderId,
      timestamp: Date.now(),
      customer: customerInfo
    };
    return JSON.stringify(qrData);
  }

  static createLocationQR(building: string, room: string): string {
    return `LOC:${building.toUpperCase()}:${room.toUpperCase()}`;
  }

  static createMaintenanceTag(date: string, equipmentId: string): string {
    return `MAINT:${date}:${equipmentId.toUpperCase()}`;
  }

  static getBestMatch(analyses: WorkflowScanResult[]): WorkflowScanResult | null {
    if (analyses.length === 0) return null;
    return analyses[0]; // Already sorted by confidence
  }

  static filterByWorkflow(
    analyses: WorkflowScanResult[],
    workflowTypes: WorkflowType[]
  ): WorkflowScanResult[] {
    return analyses.filter(analysis => workflowTypes.includes(analysis.type));
  }

  static getWorkflowInstructions(workflowType: WorkflowType): string {
    const instructions: Record<WorkflowType, string> = {
      equipment_serial: 'Scan the equipment serial number barcode or QR code',
      work_order: 'Scan the work order QR code or barcode starting with "WO"',
      location_qr: 'Scan the location QR code to verify your current position',
      inventory_check: 'Scan inventory items to verify stock levels',
      customer_account: 'Scan customer account barcode for service verification',
      maintenance_tag: 'Scan maintenance tag to record service completion'
    };

    return instructions[workflowType] || 'Scan the barcode or QR code';
  }

  static getExpectedFormats(workflowType: WorkflowType): BarcodeFormat[] {
    const rule = this.validationRules[workflowType];
    return rule.requiredFormat || ['QR_CODE', 'CODE_128', 'CODE_39'];
  }

  private static extractManufacturer(serialNumber: string): string | undefined {
    // Common manufacturer prefixes
    const prefixes: Record<string, string> = {
      'CISCO': 'Cisco Systems',
      'HPE': 'Hewlett Packard Enterprise',
      'DELL': 'Dell Technologies',
      'UBNT': 'Ubiquiti Networks',
      'ARUBA': 'Aruba Networks',
      'JUNIPER': 'Juniper Networks',
      'NETGEAR': 'Netgear',
      'LINKSYS': 'Linksys'
    };

    for (const [prefix, manufacturer] of Object.entries(prefixes)) {
      if (serialNumber.toUpperCase().startsWith(prefix)) {
        return manufacturer;
      }
    }

    return undefined;
  }

  private static extractModel(serialNumber: string): string | undefined {
    // Model extraction patterns could be more sophisticated
    // This is a simplified example
    const modelPatterns = [
      /[A-Z]{2,4}[0-9]{3,4}[A-Z]?/, // Common pattern like WS2960X
      /[0-9]{4}[A-Z]{2}/, // Pattern like 2960XR
    ];

    for (const pattern of modelPatterns) {
      const match = serialNumber.match(pattern);
      if (match) {
        return match[0];
      }
    }

    return undefined;
  }

  // Workflow-specific validation helpers
  static validateWorkOrder(workOrderId: string): boolean {
    return /^WO[0-9]{6,12}$/.test(workOrderId);
  }

  static validateSerialNumber(serialNumber: string): boolean {
    return /^[A-Z0-9]{8,20}$/.test(serialNumber) &&
           !serialNumber.includes('0000') && // Avoid obvious test serials
           serialNumber.length >= 8;
  }

  static validateCustomerId(customerId: string): boolean {
    return /^CUST[0-9]{6,10}$/.test(customerId);
  }
}
