'use server';

import { revalidatePath } from 'next/cache';
import { cookies } from 'next/headers';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function getAuthHeaders() {
  const token = cookies().get('auth-token');
  return {
    Authorization: `Bearer ${token?.value}`,
    'Content-Type': 'application/json',
  };
}

export async function getInvoices() {
  try {
    const response = await fetch(`${API_URL}/api/customer/invoices`, {
      headers: await getAuthHeaders(),
      next: {
        revalidate: 300, // Cache for 5 minutes
        tags: ['invoices'],
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch invoices');
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching invoices:', error);
    throw error;
  }
}

export async function getPaymentMethods() {
  try {
    const response = await fetch(`${API_URL}/api/customer/payment-methods`, {
      headers: await getAuthHeaders(),
      next: {
        revalidate: 300,
        tags: ['payment-methods'],
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch payment methods');
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching payment methods:', error);
    throw error;
  }
}

export async function makePaymentAction(formData: FormData) {
  const paymentData = {
    invoiceId: formData.get('invoiceId'),
    amount: parseFloat(formData.get('amount') as string),
    paymentMethodId: formData.get('paymentMethodId'),
  };

  try {
    const response = await fetch(`${API_URL}/api/customer/payments`, {
      method: 'POST',
      headers: await getAuthHeaders(),
      body: JSON.stringify(paymentData),
    });

    if (!response.ok) {
      const error = await response.json();
      return {
        success: false,
        error: error.message || 'Payment failed',
      };
    }

    const data = await response.json();

    // Revalidate invoices and payment history
    revalidatePath('/billing');

    return {
      success: true,
      payment: data,
    };
  } catch (error) {
    console.error('Error processing payment:', error);
    return {
      success: false,
      error: 'An error occurred while processing payment',
    };
  }
}

export async function addPaymentMethodAction(formData: FormData) {
  const methodData = {
    type: formData.get('type'),
    cardNumber: formData.get('cardNumber'),
    expiryMonth: formData.get('expiryMonth'),
    expiryYear: formData.get('expiryYear'),
    cvv: formData.get('cvv'),
    isDefault: formData.get('isDefault') === 'true',
  };

  try {
    const response = await fetch(`${API_URL}/api/customer/payment-methods`, {
      method: 'POST',
      headers: await getAuthHeaders(),
      body: JSON.stringify(methodData),
    });

    if (!response.ok) {
      const error = await response.json();
      return {
        success: false,
        error: error.message || 'Failed to add payment method',
      };
    }

    const data = await response.json();

    // Revalidate payment methods
    revalidatePath('/billing');

    return {
      success: true,
      paymentMethod: data,
    };
  } catch (error) {
    console.error('Error adding payment method:', error);
    return {
      success: false,
      error: 'An error occurred while adding payment method',
    };
  }
}

export async function downloadInvoiceAction(invoiceId: string) {
  try {
    const response = await fetch(`${API_URL}/api/customer/invoices/${invoiceId}/download`, {
      headers: await getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to download invoice');
    }

    const blob = await response.blob();
    return {
      success: true,
      blob,
    };
  } catch (error) {
    console.error('Error downloading invoice:', error);
    return {
      success: false,
      error: 'Failed to download invoice',
    };
  }
}
