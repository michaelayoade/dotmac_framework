'use server';

import { cookies } from 'next/headers';
import { revalidatePath } from 'next/cache';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function getAuthHeaders() {
  const token = cookies().get('auth-token');
  return {
    Authorization: `Bearer ${token?.value}`,
    'Content-Type': 'application/json',
  };
}

export async function getCustomers(page = 1, limit = 20) {
  try {
    const response = await fetch(`${API_URL}/api/customers?page=${page}&limit=${limit}`, {
      headers: await getAuthHeaders(),
      next: {
        revalidate: 60, // Cache for 1 minute
        tags: ['customers'],
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch customers');
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching customers:', error);
    throw error;
  }
}

export async function getCustomerById(id: string) {
  try {
    const response = await fetch(`${API_URL}/api/customers/${id}`, {
      headers: await getAuthHeaders(),
      next: {
        revalidate: 60,
        tags: [`customer-${id}`],
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch customer');
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching customer:', error);
    throw error;
  }
}

export async function createCustomerAction(formData: FormData) {
  const customerData = {
    name: formData.get('name'),
    email: formData.get('email'),
    phone: formData.get('phone'),
    address: formData.get('address'),
    plan: formData.get('plan'),
  };

  try {
    const response = await fetch(`${API_URL}/api/customers`, {
      method: 'POST',
      headers: await getAuthHeaders(),
      body: JSON.stringify(customerData),
    });

    if (!response.ok) {
      const error = await response.json();
      return {
        success: false,
        error: error.message || 'Failed to create customer',
      };
    }

    const data = await response.json();

    // Revalidate the customers list
    revalidatePath('/customers');

    return {
      success: true,
      customer: data,
    };
  } catch (error) {
    console.error('Error creating customer:', error);
    return {
      success: false,
      error: 'An error occurred while creating the customer',
    };
  }
}

export async function updateCustomerAction(id: string, formData: FormData) {
  const customerData = {
    name: formData.get('name'),
    email: formData.get('email'),
    phone: formData.get('phone'),
    address: formData.get('address'),
    plan: formData.get('plan'),
  };

  try {
    const response = await fetch(`${API_URL}/api/customers/${id}`, {
      method: 'PUT',
      headers: await getAuthHeaders(),
      body: JSON.stringify(customerData),
    });

    if (!response.ok) {
      const error = await response.json();
      return {
        success: false,
        error: error.message || 'Failed to update customer',
      };
    }

    const data = await response.json();

    // Revalidate both the customer detail and list
    revalidatePath(`/customers/${id}`);
    revalidatePath('/customers');

    return {
      success: true,
      customer: data,
    };
  } catch (error) {
    console.error('Error updating customer:', error);
    return {
      success: false,
      error: 'An error occurred while updating the customer',
    };
  }
}

export async function deleteCustomerAction(id: string) {
  try {
    const response = await fetch(`${API_URL}/api/customers/${id}`, {
      method: 'DELETE',
      headers: await getAuthHeaders(),
    });

    if (!response.ok) {
      const error = await response.json();
      return {
        success: false,
        error: error.message || 'Failed to delete customer',
      };
    }

    // Revalidate the customers list
    revalidatePath('/customers');

    return {
      success: true,
    };
  } catch (error) {
    console.error('Error deleting customer:', error);
    return {
      success: false,
      error: 'An error occurred while deleting the customer',
    };
  }
}

export async function suspendCustomerAction(id: string) {
  try {
    const response = await fetch(`${API_URL}/api/customers/${id}/suspend`, {
      method: 'POST',
      headers: await getAuthHeaders(),
    });

    if (!response.ok) {
      const error = await response.json();
      return {
        success: false,
        error: error.message || 'Failed to suspend customer',
      };
    }

    // Revalidate customer data
    revalidatePath(`/customers/${id}`);
    revalidatePath('/customers');

    return {
      success: true,
    };
  } catch (error) {
    console.error('Error suspending customer:', error);
    return {
      success: false,
      error: 'An error occurred while suspending the customer',
    };
  }
}
