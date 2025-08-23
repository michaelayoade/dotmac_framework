/**
 * Stripe Payment Integration Hook
 * Specialized implementation for Stripe payment processing
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { loadStripe, type Stripe, type StripeElements } from '@stripe/stripe-js';
import { getApiClient } from '../api/client';
import { useAuthStore } from '../stores/authStore';
import { useTenantStore } from '../stores/tenantStore';
import { useStandardErrorHandler } from './useStandardErrorHandler';
import { CurrencyUtils } from '../utils/currencyUtils';

export interface StripePaymentMethod {
  id: string;
  type: 'card';
  card: {
    brand: string;
    last4: string;
    expMonth: number;
    expYear: number;
    funding: 'credit' | 'debit' | 'prepaid' | 'unknown';
  };
  billingDetails: {
    address?: {
      line1?: string;
      line2?: string;
      city?: string;
      state?: string;
      postalCode?: string;
      country?: string;
    };
    email?: string;
    name?: string;
    phone?: string;
  };
}

export interface StripePaymentIntent {
  id: string;
  clientSecret: string;
  amount: number;
  currency: string;
  status: 'requires_payment_method' | 'requires_confirmation' | 'requires_action' | 'processing' | 'requires_capture' | 'canceled' | 'succeeded';
  paymentMethod?: StripePaymentMethod;
  lastPaymentError?: {
    code: string;
    message: string;
    type: string;
  };
  setupFutureUsage?: 'on_session' | 'off_session';
  captureMethod: 'automatic' | 'manual';
  confirmationMethod: 'automatic' | 'manual';
}

export interface UseStripeOptions {
  publishableKey?: string;
  testMode?: boolean;
  appearance?: {
    theme?: 'stripe' | 'night';
    variables?: Record<string, string>;
  };
  locale?: string;
}

export function useStripePayments(options: UseStripeOptions = {}) {
  const {
    publishableKey,
    testMode = process.env.NODE_ENV === 'development',
    appearance = { theme: 'stripe' },
    locale = 'en'
  } = options;

  const { user } = useAuthStore();
  const { currentTenant } = useTenantStore();
  const { handleError, withErrorHandling } = useStandardErrorHandler({
    context: 'Stripe Payments',
    enableRetry: true,
    maxRetries: 2
  });

  const [stripe, setStripe] = useState<Stripe | null>(null);
  const [elements, setElements] = useState<StripeElements | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [paymentIntent, setPaymentIntent] = useState<StripePaymentIntent | null>(null);
  
  const stripeRef = useRef<Stripe | null>(null);
  const elementsRef = useRef<StripeElements | null>(null);

  // Initialize Stripe
  useEffect(() => {
    const initializeStripe = async () => {
      try {
        const key = publishableKey || 
          (testMode 
            ? process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY_TEST
            : process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY);

        if (!key) {
          throw new Error('Stripe publishable key not configured');
        }

        const stripeInstance = await loadStripe(key, {
          locale: locale as any,
          apiVersion: '2023-10-16'
        });

        if (!stripeInstance) {
          throw new Error('Failed to load Stripe');
        }

        stripeRef.current = stripeInstance;
        setStripe(stripeInstance);
      } catch (error) {
        handleError(error);
      } finally {
        setIsLoading(false);
      }
    };

    initializeStripe();
  }, [publishableKey, testMode, locale, handleError]);

  // Create Stripe Elements when Stripe is ready and we have a payment intent
  useEffect(() => {
    if (stripe && paymentIntent && !elements) {
      const elementsInstance = stripe.elements({
        clientSecret: paymentIntent.clientSecret,
        appearance,
        locale: locale as any
      });

      elementsRef.current = elementsInstance;
      setElements(elementsInstance);
    }
  }, [stripe, paymentIntent, elements, appearance, locale]);

  // Create payment intent
  const createPaymentIntent = useCallback(async (
    amount: number,
    currency = 'usd',
    customerId: string,
    options: {
      description?: string;
      setupFutureUsage?: 'on_session' | 'off_session';
      captureMethod?: 'automatic' | 'manual';
      paymentMethodTypes?: string[];
      metadata?: Record<string, string>;
    } = {}
  ): Promise<StripePaymentIntent | null> => {
    if (!currentTenant?.tenant?.id) {
      handleError(new Error('No tenant context available'));
      return null;
    }

    // Validate amount
    if (amount <= 0) {
      handleError(new Error('Payment amount must be greater than zero'));
      return null;
    }

    if (amount > 999999) { // $9,999.99 limit
      handleError(new Error('Payment amount exceeds maximum limit'));
      return null;
    }

    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request('/api/v1/payments/stripe/intents', {
        method: 'POST',
        body: {
          amount: Math.round(amount * 100), // Convert to cents
          currency: currency.toLowerCase(),
          customerId,
          tenantId: currentTenant.tenant.id,
          description: options.description || `Payment for ${currentTenant.tenant.name}`,
          setupFutureUsage: options.setupFutureUsage,
          captureMethod: options.captureMethod || 'automatic',
          paymentMethodTypes: options.paymentMethodTypes || ['card'],
          metadata: {
            tenantId: currentTenant.tenant.id,
            userId: user?.id || 'unknown',
            ...options.metadata
          }
        }
      });

      const intent = response.data.paymentIntent;
      setPaymentIntent(intent);
      
      return intent;
    });
  }, [currentTenant?.tenant?.id, user?.id, handleError, withErrorHandling]);

  // Confirm payment
  const confirmPayment = useCallback(async (
    paymentMethodData?: any,
    options: {
      returnUrl?: string;
      savePaymentMethod?: boolean;
    } = {}
  ): Promise<{ paymentIntent?: StripePaymentIntent; error?: any }> => {
    if (!stripe || !paymentIntent) {
      const error = new Error('Stripe not initialized or no payment intent');
      handleError(error);
      return { error };
    }

    return withErrorHandling(async () => {
      setIsProcessing(true);

      try {
        let result;

        if (paymentMethodData) {
          // Confirm with new payment method
          result = await stripe.confirmPayment({
            elements: elements!,
            confirmParams: {
              return_url: options.returnUrl || window.location.href,
              save_payment_method: options.savePaymentMethod
            }
          });
        } else if (elements) {
          // Confirm with elements (payment element)
          result = await stripe.confirmPayment({
            elements,
            confirmParams: {
              return_url: options.returnUrl || window.location.href
            }
          });
        } else {
          throw new Error('No payment method or elements available');
        }

        if (result.error) {
          return { error: result.error };
        }

        if (result.paymentIntent) {
          const updatedIntent = {
            ...paymentIntent,
            status: result.paymentIntent.status as any,
            paymentMethod: result.paymentIntent.payment_method as any
          };
          setPaymentIntent(updatedIntent);
          return { paymentIntent: updatedIntent };
        }

        return { paymentIntent };
      } finally {
        setIsProcessing(false);
      }
    }) || { error: new Error('Payment confirmation failed') };
  }, [stripe, elements, paymentIntent, handleError, withErrorHandling]);

  // Handle card setup for future payments
  const setupPaymentMethod = useCallback(async (
    customerId: string,
    options: {
      usage?: 'on_session' | 'off_session';
      returnUrl?: string;
    } = {}
  ): Promise<{ setupIntent?: any; error?: any }> => {
    if (!stripe) {
      const error = new Error('Stripe not initialized');
      handleError(error);
      return { error };
    }

    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      // Create setup intent on backend
      const response = await apiClient.request('/api/v1/payments/stripe/setup-intents', {
        method: 'POST',
        body: {
          customerId,
          usage: options.usage || 'off_session',
          tenantId: currentTenant?.tenant?.id
        }
      });

      const { clientSecret } = response.data;

      // Confirm setup intent
      const result = await stripe.confirmCardSetup(clientSecret, {
        payment_method: {
          card: elements?.getElement('card')!,
          billing_details: {
            name: user?.name
          }
        }
      });

      if (result.error) {
        return { error: result.error };
      }

      return { setupIntent: result.setupIntent };
    }) || { error: new Error('Setup failed') };
  }, [stripe, elements, currentTenant?.tenant?.id, user?.name, handleError, withErrorHandling]);

  // Get customer's saved payment methods
  const getPaymentMethods = useCallback(async (customerId: string): Promise<StripePaymentMethod[]> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request(`/api/v1/payments/stripe/customers/${customerId}/payment-methods`);
      
      return response.data.paymentMethods || [];
    }) || [];
  }, [withErrorHandling]);

  // Detach payment method
  const detachPaymentMethod = useCallback(async (paymentMethodId: string): Promise<boolean> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      await apiClient.request(`/api/v1/payments/stripe/payment-methods/${paymentMethodId}/detach`, {
        method: 'POST'
      });
      
      return true;
    }) || false;
  }, [withErrorHandling]);

  // Create refund
  const createRefund = useCallback(async (
    paymentIntentId: string,
    amount?: number,
    reason?: 'duplicate' | 'fraudulent' | 'requested_by_customer'
  ): Promise<boolean> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      await apiClient.request('/api/v1/payments/stripe/refunds', {
        method: 'POST',
        body: {
          paymentIntentId,
          amount: amount ? Math.round(amount * 100) : undefined, // Convert to cents
          reason,
          tenantId: currentTenant?.tenant?.id
        }
      });
      
      return true;
    }) || false;
  }, [currentTenant?.tenant?.id, withErrorHandling]);

  // Format amount for display
  const formatAmount = useCallback((amount: number, currency = 'usd'): string => {
    return CurrencyUtils.format(amount, currency.toUpperCase() as any);
  }, []);

  return {
    // Stripe instances
    stripe,
    elements,

    // State
    isLoading,
    isProcessing,
    paymentIntent,

    // Core operations
    createPaymentIntent,
    confirmPayment,
    setupPaymentMethod,
    getPaymentMethods,
    detachPaymentMethod,
    createRefund,

    // Utilities
    formatAmount,
    
    // Computed values
    isReady: !isLoading && !!stripe,
    canProcess: !isLoading && !isProcessing && !!stripe,
    paymentStatus: paymentIntent?.status,
    lastPaymentError: paymentIntent?.lastPaymentError
  };
}

// Hook for subscription payments with Stripe
export function useStripeSubscriptions(customerId: string) {
  const stripePayments = useStripePayments();
  const { withErrorHandling } = useStandardErrorHandler({ context: 'Stripe Subscriptions' });
  const { currentTenant } = useTenantStore();

  const createSubscription = useCallback(async (
    priceId: string,
    paymentMethodId?: string,
    options: {
      trialEnd?: number;
      prorationBehavior?: 'create_prorations' | 'none';
      metadata?: Record<string, string>;
    } = {}
  ) => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request('/api/v1/payments/stripe/subscriptions', {
        method: 'POST',
        body: {
          customerId,
          priceId,
          paymentMethodId,
          tenantId: currentTenant?.tenant?.id,
          ...options
        }
      });

      return response.data.subscription;
    });
  }, [customerId, currentTenant?.tenant?.id, withErrorHandling]);

  const cancelSubscription = useCallback(async (
    subscriptionId: string,
    options: {
      cancelAtPeriodEnd?: boolean;
      invoiceNow?: boolean;
      prorate?: boolean;
    } = {}
  ) => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      await apiClient.request(`/api/v1/payments/stripe/subscriptions/${subscriptionId}/cancel`, {
        method: 'POST',
        body: {
          tenantId: currentTenant?.tenant?.id,
          ...options
        }
      });

      return true;
    });
  }, [currentTenant?.tenant?.id, withErrorHandling]);

  return {
    ...stripePayments,
    createSubscription,
    cancelSubscription
  };
}

// Export types for use in components
export type { StripePaymentMethod, StripePaymentIntent };