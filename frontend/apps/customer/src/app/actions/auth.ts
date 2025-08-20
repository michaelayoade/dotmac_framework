'use server';

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function loginAction(formData: FormData) {
  const email = formData.get('email') as string;
  const password = formData.get('password') as string;
  
  try {
    const response = await fetch(`${API_URL}/api/auth/customer/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        email, 
        password,
        portal: 'customer'
      }),
    });
    
    if (!response.ok) {
      const error = await response.json();
      return { 
        success: false, 
        error: error.message || 'Invalid credentials' 
      };
    }
    
    const data = await response.json();
    
    // Set secure cookies
    cookies().set('auth-token', data.token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 60 * 60 * 24 * 7, // 7 days
      path: '/',
    });
    
    cookies().set('portal-type', 'customer', {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 60 * 60 * 24 * 7, // 7 days
      path: '/',
    });
    
    // Store user data in cookie (non-sensitive)
    cookies().set('user-data', JSON.stringify({
      id: data.customer.id,
      email: data.customer.email,
      name: data.customer.name,
      accountNumber: data.customer.accountNumber,
    }), {
      httpOnly: false,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 60 * 60 * 24 * 7, // 7 days
      path: '/',
    });
    
    return { 
      success: true, 
      customer: data.customer 
    };
  } catch (error) {
    console.error('Login error:', error);
    return { 
      success: false, 
      error: 'An error occurred during login' 
    };
  }
}

export async function registerAction(formData: FormData) {
  const registrationData = {
    email: formData.get('email'),
    password: formData.get('password'),
    name: formData.get('name'),
    phone: formData.get('phone'),
    address: formData.get('address'),
  };
  
  try {
    const response = await fetch(`${API_URL}/api/auth/customer/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(registrationData),
    });
    
    if (!response.ok) {
      const error = await response.json();
      return { 
        success: false, 
        error: error.message || 'Registration failed' 
      };
    }
    
    const data = await response.json();
    
    // Auto-login after registration
    cookies().set('auth-token', data.token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 60 * 60 * 24 * 7, // 7 days
      path: '/',
    });
    
    cookies().set('portal-type', 'customer', {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 60 * 60 * 24 * 7, // 7 days
      path: '/',
    });
    
    return { 
      success: true, 
      customer: data.customer 
    };
  } catch (error) {
    console.error('Registration error:', error);
    return { 
      success: false, 
      error: 'An error occurred during registration' 
    };
  }
}

export async function logoutAction() {
  // Clear all auth cookies
  cookies().delete('auth-token');
  cookies().delete('portal-type');
  cookies().delete('user-data');
  
  // Redirect to login page
  redirect('/');
}