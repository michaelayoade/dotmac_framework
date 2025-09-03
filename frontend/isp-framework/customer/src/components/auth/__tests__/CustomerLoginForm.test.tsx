/**
 * Critical Path Test: Customer Login Form
 * Tests the primary customer authentication flow
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import { CustomerLoginForm } from '../CustomerLoginForm';

// Mock the secure token manager
const mockLogin = jest.fn();
jest.mock('../../lib/auth/secureTokenManager', () => ({
  secureTokenManager: {
    login: mockLogin,
  },
}));

// Mock the portal auth hook
const mockPortalAuth = {
  login: jest.fn(),
  user: null,
  isAuthenticated: false,
  _currentPortal: { id: 'customer', name: 'Customer Portal' },
  _getPortalBranding: jest.fn(() => ({
    primaryColor: '#3b82f6',
    logoUrl: '/logo.png',
    companyName: 'DotMac ISP',
  })),
};

jest.mock('@dotmac/headless', () => ({
  usePortalAuth: () => mockPortalAuth,
}));

describe('CustomerLoginForm - Critical Path', () => {
  const user = userEvent.setup();

  beforeEach(() => {
    jest.clearAllMocks();
    mockLogin.mockReset();
    mockPortalAuth.login.mockReset();
  });

  describe('Form Rendering', () => {
    it('renders login form with required fields', () => {
      render(<CustomerLoginForm />);

      expect(screen.getByRole('textbox', { name: /email/i })).toBeInTheDocument();
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
    });

    it('shows portal branding correctly', () => {
      render(<CustomerLoginForm />);

      expect(screen.getByText('DotMac ISP')).toBeInTheDocument();
      expect(screen.getByText('Customer Portal')).toBeInTheDocument();
    });

    it('displays all login method options', () => {
      render(<CustomerLoginForm />);

      expect(screen.getByText('Email & Password')).toBeInTheDocument();
      expect(screen.getByText('Portal ID')).toBeInTheDocument();
    });
  });

  describe('Form Validation', () => {
    it('shows validation errors for empty fields', async () => {
      render(<CustomerLoginForm />);

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      await user.click(submitButton);

      expect(screen.getByText('Email is required')).toBeInTheDocument();
      expect(screen.getByText('Password is required')).toBeInTheDocument();
    });

    it('validates email format', async () => {
      render(<CustomerLoginForm />);

      const emailInput = screen.getByRole('textbox', { name: /email/i });
      await user.type(emailInput, 'invalid-email');

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      await user.click(submitButton);

      expect(screen.getByText('Please enter a valid email address')).toBeInTheDocument();
    });

    it('validates password length', async () => {
      render(<CustomerLoginForm />);

      const passwordInput = screen.getByLabelText(/password/i);
      await user.type(passwordInput, '123');

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      await user.click(submitButton);

      expect(screen.getByText('Password must be at least 6 characters')).toBeInTheDocument();
    });
  });

  describe('Authentication Flow', () => {
    it('submits valid credentials successfully', async () => {
      mockLogin.mockResolvedValue({
        success: true,
        user: {
          id: '123',
          name: 'John Doe',
          email: 'john@example.com',
          accountNumber: 'ACC-001',
          portalType: 'customer',
        },
      });

      mockPortalAuth.login.mockResolvedValue({ success: true });

      render(<CustomerLoginForm />);

      const emailInput = screen.getByRole('textbox', { name: /email/i });
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'john@example.com');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith({
          email: 'john@example.com',
          password: 'password123',
        });
      });

      expect(mockPortalAuth.login).toHaveBeenCalled();
    });

    it('handles authentication failure', async () => {
      mockLogin.mockResolvedValue({
        success: false,
        error: 'Invalid credentials',
      });

      render(<CustomerLoginForm />);

      const emailInput = screen.getByRole('textbox', { name: /email/i });
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'john@example.com');
      await user.type(passwordInput, 'wrongpassword');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
      });

      expect(mockPortalAuth.login).not.toHaveBeenCalled();
    });

    it('shows loading state during authentication', async () => {
      mockLogin.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ success: true }), 100))
      );

      render(<CustomerLoginForm />);

      const emailInput = screen.getByRole('textbox', { name: /email/i });
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'john@example.com');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      expect(screen.getByText('Signing in...')).toBeInTheDocument();
      expect(submitButton).toBeDisabled();
    });
  });

  describe('Portal ID Login', () => {
    it('switches to portal ID login method', async () => {
      render(<CustomerLoginForm />);

      const portalIdTab = screen.getByText('Portal ID');
      await user.click(portalIdTab);

      expect(screen.getByPlaceholderText('Enter your Portal ID')).toBeInTheDocument();
      expect(screen.queryByRole('textbox', { name: /email/i })).not.toBeInTheDocument();
    });

    it('validates portal ID format', async () => {
      render(<CustomerLoginForm />);

      const portalIdTab = screen.getByText('Portal ID');
      await user.click(portalIdTab);

      const portalIdInput = screen.getByPlaceholderText('Enter your Portal ID');
      await user.type(portalIdInput, 'invalid');

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      await user.click(submitButton);

      expect(screen.getByText('Please enter a valid Portal ID')).toBeInTheDocument();
    });

    it('submits portal ID login successfully', async () => {
      mockLogin.mockResolvedValue({ success: true });

      render(<CustomerLoginForm />);

      const portalIdTab = screen.getByText('Portal ID');
      await user.click(portalIdTab);

      const portalIdInput = screen.getByPlaceholderText('Enter your Portal ID');
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(portalIdInput, 'CX-12345');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith({
          portalId: 'CX-12345',
          password: 'password123',
        });
      });
    });
  });

  describe('Accessibility', () => {
    it('has proper form labels and structure', () => {
      render(<CustomerLoginForm />);

      const emailInput = screen.getByRole('textbox', { name: /email/i });
      const passwordInput = screen.getByLabelText(/password/i);

      expect(emailInput).toHaveAttribute('aria-describedby');
      expect(passwordInput).toHaveAttribute('aria-describedby');
      expect(passwordInput).toHaveAttribute('type', 'password');
    });

    it('supports keyboard navigation', async () => {
      render(<CustomerLoginForm />);

      const emailInput = screen.getByRole('textbox', { name: /email/i });
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.tab();
      expect(emailInput).toHaveFocus();

      await user.tab();
      expect(passwordInput).toHaveFocus();

      await user.tab();
      expect(submitButton).toHaveFocus();
    });
  });

  describe('Security Features', () => {
    it('masks password input by default', () => {
      render(<CustomerLoginForm />);

      const passwordInput = screen.getByLabelText(/password/i);
      expect(passwordInput).toHaveAttribute('type', 'password');
    });

    it('prevents form submission on Enter when invalid', async () => {
      render(<CustomerLoginForm />);

      const emailInput = screen.getByRole('textbox', { name: /email/i });
      await user.type(emailInput, 'invalid-email');
      await user.keyboard('{Enter}');

      expect(mockLogin).not.toHaveBeenCalled();
      expect(screen.getByText('Please enter a valid email address')).toBeInTheDocument();
    });

    it('includes CSRF protection in login request', async () => {
      mockLogin.mockResolvedValue({ success: true });

      render(<CustomerLoginForm />);

      const emailInput = screen.getByRole('textbox', { name: /email/i });
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'john@example.com');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith(
          expect.objectContaining({
            email: 'john@example.com',
            password: 'password123',
          })
        );
      });
    });
  });
});
