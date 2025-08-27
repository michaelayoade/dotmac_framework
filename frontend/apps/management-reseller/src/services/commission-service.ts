/**
 * Commission Service
 * Implements payment approval and export functionality using existing infrastructure
 */

import { API } from '@/lib/api/endpoints';
import { InputSanitizer } from '@/lib/security/input-sanitizer';
import { SecurityError } from '@/lib/security/types';

export interface CommissionPayment {
  id: string;
  payment_number: string;
  partner_id: string;
  partner_name: string;
  partner_tier: string;
  period_start: string;
  period_end: string;
  gross_commission: number;
  deductions: Array<{
    type: string;
    description: string;
    amount: number;
  }>;
  net_commission: number;
  payment_date?: string;
  payment_method: string;
  status: 'CALCULATED' | 'APPROVED' | 'PAID' | 'FAILED' | 'CANCELLED';
  created_at: string;
  sales_count: number;
  approval_notes?: string;
}

export interface ApprovalRequest {
  payment_ids: string[];
  approval_notes?: string;
  approved_by: string;
}

export interface ExportOptions {
  format: 'CSV' | 'XLSX' | 'PDF';
  payment_ids: string[];
  include_details: boolean;
  date_range?: {
    start: string;
    end: string;
  };
}

export class CommissionService {
  /**
   * Approve commission payments
   * Leverages the existing billing service infrastructure
   */
  static async approvePayments(request: ApprovalRequest): Promise<{ success: boolean; data?: any; error?: string }> {
    try {
      // Sanitize input
      const sanitizedRequest = {
        payment_ids: request.payment_ids.map(id => InputSanitizer.validate_safe_input(id, 'payment_id')),
        approval_notes: request.approval_notes ? InputSanitizer.sanitize_html(request.approval_notes) : undefined,
        approved_by: InputSanitizer.validate_safe_input(request.approved_by, 'approved_by')
      };

      // Validate payment IDs format (should be UUIDs or similar)
      const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
      for (const id of sanitizedRequest.payment_ids) {
        if (!uuidRegex.test(id)) {
          throw new SecurityError('payment_id', `Invalid payment ID format: ${id}`);
        }
      }

      // Call the management platform API for commission approval
      const response = await API.commissions.approve(sanitizedRequest);
      
      if (response.status === 'success') {
        // Send notification using existing notification service
        await this.notifyApprovalSuccess(sanitizedRequest.payment_ids.length);
        return { success: true, data: response.data as any };
      }

      return { success: false, error: response.message || 'Approval failed' };

    } catch (error) {
      console.error('Commission approval error:', error);
      
      if (error instanceof SecurityError) {
        return { success: false, error: error.reason };
      }
      
      return { success: false, error: 'Failed to approve commission payments' };
    }
  }

  /**
   * Process approved payments for payout
   */
  static async processPayments(paymentIds: string[]): Promise<{ success: boolean; data?: any; error?: string }> {
    try {
      const sanitizedIds = paymentIds.map(id => InputSanitizer.validate_safe_input(id, 'payment_id'));
      
      const response = await API.commissions.process({
        payment_ids: sanitizedIds,
        processing_date: new Date().toISOString()
      });

      if (response.status === 'success') {
        await this.notifyProcessingSuccess(sanitizedIds.length);
        return { success: true, data: response.data as any };
      }

      return { success: false, error: response.message || 'Processing failed' };

    } catch (error) {
      console.error('Payment processing error:', error);
      return { success: false, error: 'Failed to process payments' };
    }
  }

  /**
   * Export commission data in various formats
   * Leverages existing export plugin system
   */
  static async exportCommissions(options: ExportOptions): Promise<{ success: boolean; downloadUrl?: string; error?: string }> {
    try {
      // Sanitize export options
      const sanitizedOptions = {
        format: options.format,
        payment_ids: options.payment_ids.map(id => InputSanitizer.validate_safe_input(id, 'payment_id')),
        include_details: Boolean(options.include_details),
        date_range: options.date_range ? {
          start: InputSanitizer.validate_safe_input(options.date_range.start, 'date_start'),
          end: InputSanitizer.validate_safe_input(options.date_range.end, 'date_end')
        } : undefined
      };

      // Validate export format
      const allowedFormats = ['CSV', 'XLSX', 'PDF'];
      if (!allowedFormats.includes(sanitizedOptions.format)) {
        throw new SecurityError('export_format', 'Invalid export format');
      }

      // Use the plugin system for export functionality
      const exportResponse = await this.executeExportPlugin(sanitizedOptions);
      
      if (exportResponse.success) {
        return { 
          success: true, 
          downloadUrl: exportResponse.downloadUrl 
        };
      }

      return { success: false, error: exportResponse.error || 'Export failed' };

    } catch (error) {
      console.error('Commission export error:', error);
      
      if (error instanceof SecurityError) {
        return { success: false, error: error.reason };
      }
      
      return { success: false, error: 'Failed to export commission data' };
    }
  }

  /**
   * Execute export using the existing plugin system
   */
  private static async executeExportPlugin(options: any): Promise<{ success: boolean; downloadUrl?: string; error?: string }> {
    try {
      // Leverage the existing plugin system from management platform
      const response = await fetch('/api/plugins/export/commissions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          plugin_name: 'commission_export',
          plugin_config: {
            export_type: 'commission_data',
            output_format: options.format.toLowerCase(),
            filters: {
              payment_ids: options.payment_ids,
              include_details: options.include_details,
              date_range: options.date_range
            }
          }
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        return { success: false, error: errorData.error || 'Export plugin failed' };
      }

      const result = await response.json();
      return {
        success: true,
        downloadUrl: result.download_url
      };

    } catch (error) {
      console.error('Export plugin execution error:', error);
      return { success: false, error: 'Export service unavailable' };
    }
  }

  /**
   * Send notification for successful approval
   */
  private static async notifyApprovalSuccess(count: number): Promise<void> {
    try {
      await fetch('/api/notifications/send', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          type: 'commission_approval',
          title: 'Commission Payments Approved',
          message: `Successfully approved ${count} commission payment${count > 1 ? 's' : ''}`,
          priority: 'normal',
          channels: ['system_log', 'dashboard_notification']
        })
      });
    } catch (error) {
      console.error('Failed to send approval notification:', error);
    }
  }

  /**
   * Send notification for successful processing
   */
  private static async notifyProcessingSuccess(count: number): Promise<void> {
    try {
      await fetch('/api/notifications/send', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          type: 'payment_processing',
          title: 'Payments Processed',
          message: `Successfully processed ${count} payment${count > 1 ? 's' : ''} for payout`,
          priority: 'high',
          channels: ['system_log', 'dashboard_notification', 'email_admin']
        })
      });
    } catch (error) {
      console.error('Failed to send processing notification:', error);
    }
  }

  /**
   * Get commission payment details with security validation
   */
  static async getPaymentDetails(paymentId: string): Promise<{ success: boolean; data?: CommissionPayment; error?: string }> {
    try {
      const sanitizedId = InputSanitizer.validate_safe_input(paymentId, 'payment_id');
      
      const response = await API.commissions.getById(sanitizedId);
      
      if (response.status === 'success') {
        return { success: true, data: response.data as any };
      }

      return { success: false, error: response.message || 'Payment not found' };

    } catch (error) {
      console.error('Get payment details error:', error);
      
      if (error instanceof SecurityError) {
        return { success: false, error: error.reason };
      }
      
      return { success: false, error: 'Failed to retrieve payment details' };
    }
  }

  /**
   * Validate bulk action permissions
   */
  static async validateBulkAction(
    action: 'approve' | 'process' | 'export',
    paymentIds: string[],
    userRole: string
  ): Promise<{ canPerform: boolean; reason?: string }> {
    try {
      // Check role permissions
      const rolePermissions = {
        'approve': ['master_admin', 'channel_manager'],
        'process': ['master_admin', 'channel_manager'],
        'export': ['master_admin', 'channel_manager', 'operations_manager']
      };

      if (!rolePermissions[action].includes(userRole)) {
        return { canPerform: false, reason: 'Insufficient permissions for this action' };
      }

      // Validate payment IDs
      const sanitizedIds = paymentIds.map(id => InputSanitizer.validate_safe_input(id, 'payment_id'));
      
      // Check if payments are in correct status for the action
      const validationResponse = await API.commissions.validateBulkAction({
        action,
        payment_ids: sanitizedIds
      });

      return validationResponse;

    } catch (error) {
      console.error('Bulk action validation error:', error);
      return { canPerform: false, reason: 'Validation failed' };
    }
  }
}