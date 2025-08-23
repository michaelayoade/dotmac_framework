/**
 * PayPal Payment Integration Hook
 * Specialized implementation for PayPal payment processing
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { getApiClient } from '../api/client';
import { useAuthStore } from '../stores/authStore';
import { useTenantStore } from '../stores/tenantStore';
import { useStandardErrorHandler } from './useStandardErrorHandler';
import { CurrencyUtils } from '../utils/currencyUtils';

// PayPal SDK types
interface PayPalOrder {
  id: string;
  status: 'CREATED' | 'SAVED' | 'APPROVED' | 'VOIDED' | 'COMPLETED' | 'PAYER_ACTION_REQUIRED';
  intent: 'CAPTURE' | 'AUTHORIZE';
  payer?: {
    name?: {
      given_name: string;
      surname: string;
    };
    email_address?: string;
    payer_id?: string;
  };
  purchase_units: Array<{
    reference_id?: string;
    amount: {
      currency_code: string;
      value: string;
      breakdown?: {
        item_total?: { currency_code: string; value: string };
        shipping?: { currency_code: string; value: string };
        handling?: { currency_code: string; value: string };
        tax_total?: { currency_code: string; value: string };
        discount?: { currency_code: string; value: string };
      };
    };
    description?: string;
    custom_id?: string;
    soft_descriptor?: string;
  }>;
  application_context?: {
    brand_name?: string;
    locale?: string;
    landing_page?: 'LOGIN' | 'BILLING' | 'NO_PREFERENCE';
    shipping_preference?: 'GET_FROM_FILE' | 'NO_SHIPPING' | 'SET_PROVIDED_ADDRESS';
    user_action?: 'CONTINUE' | 'PAY_NOW';
    return_url?: string;
    cancel_url?: string;
  };
}

interface PayPalCapture {
  id: string;
  status: 'COMPLETED' | 'DECLINED' | 'PARTIALLY_REFUNDED' | 'PENDING' | 'REFUNDED';
  amount: {
    currency_code: string;
    value: string;
  };
  final_capture: boolean;
  create_time: string;
  update_time: string;
}

interface PayPalSubscription {
  id: string;
  status: 'APPROVAL_PENDING' | 'APPROVED' | 'ACTIVE' | 'SUSPENDED' | 'CANCELLED' | 'EXPIRED';
  status_update_time: string;
  plan_id: string;
  start_time: string;
  quantity: string;
  subscriber: {
    name?: {
      given_name: string;
      surname: string;
    };
    email_address: string;
  };
  billing_info?: {
    outstanding_balance: {
      currency_code: string;
      value: string;
    };
    cycle_executions: Array<{
      tenure_type: 'TRIAL' | 'REGULAR';
      sequence: number;
      cycles_completed: number;
      cycles_remaining: number;
      total_cycles: number;
    }>;
  };
}

export interface UsePayPalOptions {
  clientId?: string;
  testMode?: boolean;
  currency?: string;
  intent?: 'capture' | 'authorize';
  locale?: string;
  debug?: boolean;
}

export function usePayPalPayments(options: UsePayPalOptions = {}) {
  const {
    clientId,
    testMode = process.env.NODE_ENV === 'development',
    currency = 'USD',
    intent = 'capture',
    locale = 'en_US',
    debug = testMode
  } = options;

  const { user } = useAuthStore();
  const { currentTenant } = useTenantStore();
  const { handleError, withErrorHandling } = useStandardErrorHandler({
    context: 'PayPal Payments',
    enableRetry: true,
    maxRetries: 2
  });

  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentOrder, setCurrentOrder] = useState<PayPalOrder | null>(null);
  const [paypalSDK, setPayPalSDK] = useState<any>(null);
  
  const sdkRef = useRef<any>(null);
  const processingRef = useRef<Set<string>>(new Set());

  // Load PayPal SDK
  useEffect(() => {
    const loadPayPalSDK = async () => {
      try {
        const effectiveClientId = clientId || 
          (testMode 
            ? process.env.NEXT_PUBLIC_PAYPAL_CLIENT_ID_SANDBOX
            : process.env.NEXT_PUBLIC_PAYPAL_CLIENT_ID);

        if (!effectiveClientId) {
          throw new Error('PayPal client ID not configured');
        }

        // Check if PayPal SDK is already loaded
        if (window.paypal) {
          sdkRef.current = window.paypal;
          setPayPalSDK(window.paypal);
          setIsLoading(false);
          return;
        }

        // Create script tag to load PayPal SDK
        const script = document.createElement('script');
        script.src = `https://www.paypal.com/sdk/js?client-id=${effectiveClientId}&currency=${currency}&intent=${intent}&locale=${locale}${debug ? '&debug=true' : ''}`;
        script.async = true;

        script.onload = () => {
          if (window.paypal) {
            sdkRef.current = window.paypal;
            setPayPalSDK(window.paypal);
          }
          setIsLoading(false);
        };

        script.onerror = () => {
          handleError(new Error('Failed to load PayPal SDK'));
          setIsLoading(false);
        };

        document.head.appendChild(script);

        return () => {
          document.head.removeChild(script);
        };
      } catch (error) {
        handleError(error);
        setIsLoading(false);
      }
    };

    loadPayPalSDK();
  }, [clientId, testMode, currency, intent, locale, debug, handleError]);

  // Create PayPal order
  const createOrder = useCallback(async (
    amount: number,
    customerId: string,
    options: {
      description?: string;
      invoiceId?: string;
      customId?: string;
      applicationContext?: Partial<PayPalOrder['application_context']>;
      breakdown?: PayPalOrder['purchase_units'][0]['amount']['breakdown'];
    } = {}
  ): Promise<PayPalOrder | null> => {
    if (!currentTenant?.tenant?.id) {
      handleError(new Error('No tenant context available'));
      return null;
    }

    // Validate amount
    if (amount <= 0) {
      handleError(new Error('Payment amount must be greater than zero'));
      return null;
    }

    if (amount > 10000) { // $10,000 limit for PayPal
      handleError(new Error('Payment amount exceeds PayPal maximum limit'));
      return null;
    }

    // Prevent duplicate processing
    const operationKey = `${customerId}-${amount}-${Date.now()}`;
    if (processingRef.current.has(operationKey)) {
      handleError(new Error('Duplicate payment attempt detected'));
      return null;
    }

    return withErrorHandling(async () => {
      processingRef.current.add(operationKey);

      try {
        const apiClient = getApiClient();
        
        const orderData = {
          intent: intent.toUpperCase(),
          purchase_units: [{
            reference_id: options.invoiceId,
            amount: {
              currency_code: currency,
              value: amount.toFixed(2),
              breakdown: options.breakdown
            },
            description: options.description || `Payment for ${currentTenant.tenant.name}`,
            custom_id: options.customId || customerId
          }],
          application_context: {
            brand_name: currentTenant.tenant.name,
            locale,
            landing_page: 'NO_PREFERENCE',
            shipping_preference: 'NO_SHIPPING',
            user_action: 'PAY_NOW',
            ...options.applicationContext
          }
        };

        const response = await apiClient.request('/api/v1/payments/paypal/orders', {
          method: 'POST',
          body: {
            ...orderData,
            customerId,
            tenantId: currentTenant.tenant.id,
            metadata: {
              userId: user?.id,
              tenantId: currentTenant.tenant.id
            }
          }
        });

        const order = response.data.order;
        setCurrentOrder(order);
        
        return order;
      } finally {
        processingRef.current.delete(operationKey);
      }
    });
  }, [currentTenant?.tenant, currency, intent, locale, user?.id, handleError, withErrorHandling]);

  // Capture PayPal order
  const captureOrder = useCallback(async (orderId: string): Promise<PayPalCapture | null> => {
    return withErrorHandling(async () => {
      setIsProcessing(true);

      try {
        const apiClient = getApiClient();
        
        const response = await apiClient.request(`/api/v1/payments/paypal/orders/${orderId}/capture`, {
          method: 'POST',
          body: {
            tenantId: currentTenant?.tenant?.id
          }
        });

        const capture = response.data.capture;
        
        // Update order status
        if (currentOrder && currentOrder.id === orderId) {
          setCurrentOrder({
            ...currentOrder,
            status: 'COMPLETED'
          });
        }

        return capture;
      } finally {
        setIsProcessing(false);
      }
    });
  }, [currentTenant?.tenant?.id, currentOrder, withErrorHandling]);

  // Authorize PayPal order
  const authorizeOrder = useCallback(async (orderId: string): Promise<any | null> => {
    return withErrorHandling(async () => {
      setIsProcessing(true);

      try {
        const apiClient = getApiClient();
        
        const response = await apiClient.request(`/api/v1/payments/paypal/orders/${orderId}/authorize`, {
          method: 'POST',
          body: {
            tenantId: currentTenant?.tenant?.id
          }
        });

        return response.data.authorization;
      } finally {
        setIsProcessing(false);
      }
    });
  }, [currentTenant?.tenant?.id, withErrorHandling]);

  // Create PayPal subscription
  const createSubscription = useCallback(async (
    planId: string,
    customerId: string,
    options: {
      startTime?: string;
      quantity?: string;
      applicationContext?: {
        brandName?: string;
        locale?: string;
        shippingPreference?: 'GET_FROM_FILE' | 'NO_SHIPPING' | 'SET_PROVIDED_ADDRESS';
        userAction?: 'SUBSCRIBE_NOW' | 'CONTINUE';
        paymentMethod?: {
          payerSelected?: 'PAYPAL';
          payeePreferred?: 'IMMEDIATE_PAYMENT_REQUIRED' | 'UNRESTRICTED';
        };
        returnUrl?: string;
        cancelUrl?: string;
      };
    } = {}
  ): Promise<PayPalSubscription | null> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const subscriptionData = {
        plan_id: planId,
        start_time: options.startTime,
        quantity: options.quantity || '1',
        subscriber: {
          name: {
            given_name: user?.firstName || 'Customer',
            surname: user?.lastName || ''
          },
          email_address: user?.email || ''
        },
        application_context: {
          brand_name: currentTenant?.tenant?.name,
          locale,
          shipping_preference: 'NO_SHIPPING',
          user_action: 'SUBSCRIBE_NOW',
          ...options.applicationContext
        }
      };

      const response = await apiClient.request('/api/v1/payments/paypal/subscriptions', {
        method: 'POST',
        body: {
          ...subscriptionData,
          customerId,
          tenantId: currentTenant?.tenant?.id
        }
      });

      return response.data.subscription;
    });
  }, [user, currentTenant?.tenant, locale, withErrorHandling]);

  // Cancel PayPal subscription
  const cancelSubscription = useCallback(async (
    subscriptionId: string,
    reason?: string
  ): Promise<boolean> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      await apiClient.request(`/api/v1/payments/paypal/subscriptions/${subscriptionId}/cancel`, {
        method: 'POST',
        body: {
          reason: reason || 'Customer requested cancellation',
          tenantId: currentTenant?.tenant?.id
        }
      });

      return true;
    }) || false;
  }, [currentTenant?.tenant?.id, withErrorHandling]);

  // Get subscription details
  const getSubscription = useCallback(async (subscriptionId: string): Promise<PayPalSubscription | null> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request(`/api/v1/payments/paypal/subscriptions/${subscriptionId}`);
      
      return response.data.subscription;
    });
  }, [withErrorHandling]);

  // Create refund
  const createRefund = useCallback(async (
    captureId: string,
    amount?: number,
    note?: string
  ): Promise<boolean> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      await apiClient.request('/api/v1/payments/paypal/refunds', {
        method: 'POST',
        body: {
          captureId,
          amount: amount ? {
            currency_code: currency,
            value: amount.toFixed(2)
          } : undefined,
          note_to_payer: note,
          tenantId: currentTenant?.tenant?.id
        }
      });
      
      return true;
    }) || false;
  }, [currency, currentTenant?.tenant?.id, withErrorHandling]);

  // Render PayPal buttons
  const renderPayPalButtons = useCallback((containerId: string, orderOptions: {
    amount: number;
    customerId: string;
    description?: string;
    onApprove?: (data: any, actions: any) => Promise<void>;
    onError?: (error: any) => void;
    onCancel?: (data: any) => void;
  }) => {
    if (!paypalSDK || !document.getElementById(containerId)) {
      return;
    }

    paypalSDK.Buttons({
      createOrder: async () => {
        const order = await createOrder(
          orderOptions.amount,
          orderOptions.customerId,
          { description: orderOptions.description }
        );
        return order?.id;
      },
      
      onApprove: async (data: any, actions: any) => {
        try {
          const capture = await captureOrder(data.orderID);
          if (orderOptions.onApprove) {
            await orderOptions.onApprove(data, { ...actions, capture });
          }
        } catch (error) {
          if (orderOptions.onError) {
            orderOptions.onError(error);
          } else {
            handleError(error);
          }
        }
      },
      
      onError: (error: any) => {
        if (orderOptions.onError) {
          orderOptions.onError(error);
        } else {
          handleError(error);
        }
      },
      
      onCancel: orderOptions.onCancel,
      
      style: {
        layout: 'vertical',
        color: 'blue',
        shape: 'rect',
        label: 'paypal'
      }
    }).render(`#${containerId}`);
  }, [paypalSDK, createOrder, captureOrder, handleError]);

  // Format amount for display
  const formatAmount = useCallback((amount: number, currencyCode = currency): string => {
    return CurrencyUtils.format(amount, currencyCode as any);
  }, [currency]);

  return {
    // SDK
    paypalSDK,

    // State
    isLoading,
    isProcessing,
    currentOrder,

    // Core operations
    createOrder,
    captureOrder,
    authorizeOrder,
    createSubscription,
    cancelSubscription,
    getSubscription,
    createRefund,

    // UI helpers
    renderPayPalButtons,
    
    // Utilities
    formatAmount,
    
    // Computed values
    isReady: !isLoading && !!paypalSDK,
    canProcess: !isLoading && !isProcessing && !!paypalSDK,
    orderStatus: currentOrder?.status,
    
    // Configuration
    currency,
    intent,
    testMode
  };
}

// Hook for PayPal subscription management
export function usePayPalSubscriptions() {
  const paypalPayments = usePayPalPayments();
  const { withErrorHandling } = useStandardErrorHandler({ context: 'PayPal Subscriptions' });
  const { currentTenant } = useTenantStore();

  const createBillingPlan = useCallback(async (planData: {
    productId: string;
    name: string;
    description?: string;
    billingCycles: Array<{
      frequencyInterval: string;
      frequencyIntervalCount: number;
      tenureType: 'TRIAL' | 'REGULAR';
      sequence: number;
      totalCycles: number;
      pricingScheme: {
        fixedPrice: {
          currencyCode: string;
          value: string;
        };
      };
    }>;
    paymentPreferences: {
      autoBillOutstanding: boolean;
      setupFee?: {
        currencyCode: string;
        value: string;
      };
      setupFeeFailureAction: 'CONTINUE' | 'CANCEL';
      paymentFailureThreshold: number;
    };
  }) => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request('/api/v1/payments/paypal/billing-plans', {
        method: 'POST',
        body: {
          ...planData,
          tenantId: currentTenant?.tenant?.id
        }
      });

      return response.data.plan;
    });
  }, [currentTenant?.tenant?.id, withErrorHandling]);

  return {
    ...paypalPayments,
    createBillingPlan
  };
}

// Extend window interface for PayPal SDK
declare global {
  interface Window {
    paypal?: any;
  }
}

export type { PayPalOrder, PayPalCapture, PayPalSubscription };