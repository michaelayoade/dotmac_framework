/**
 * Integration tests for SecureCustomerLoginForm component
 * Tests complete user workflows, authentication flow, and security features
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRouter } from 'next/navigation';
import React from 'react';
import { useAuthActions } from '../SecureAuthProvider';
import { SecureCustomerLoginForm } from '../SecureCustomerLoginForm';
import { useStandardErrorHandler } from '@dotmac/headless/hooks/useStandardErrorHandler';

// Next.js router is now globally mocked

// Mock the auth provider
jest.mock('../SecureAuthProvider');
const mockLogin = jest.fn();
const mockUseAuthActions = useAuthActions as jest.Mock;

// Mock platform error handler
const mockHandleError = jest.fn();
jest.mock('@dotmac/headless/hooks/useStandardErrorHandler', () => ({
  useStandardErrorHandler: () => ({
    handleError: mockHandleError,
  }),
}));

describe('SecureCustomerLoginForm Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuthActions.mockReturnValue({
      login: mockLogin,
    });
    mockHandleError.mockClear();
  });

  it('should render login form with all required fields', () => {
    render(<SecureCustomerLoginForm />);

    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/portal id/i)).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: /remember me/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('should display company branding and logo', () => {
    render(<SecureCustomerLoginForm />);

    expect(screen.getByText('DotMac')).toBeInTheDocument();
    expect(screen.getByText('Welcome Back')).toBeInTheDocument();
    expect(screen.getByText('Sign in to your customer portal')).toBeInTheDocument();
  });

  describe('Form Validation', () => {
    it('should require email and password fields', async () => {
      const user = userEvent.setup();
      render(<SecureCustomerLoginForm />);

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      await user.click(submitButton);

      // Form validation should prevent submission
      expect(mockLogin).not.toHaveBeenCalled();
    });

    it('should validate email format', async () => {
      const user = userEvent.setup();
      render(<SecureCustomerLoginForm />);

      const emailInput = screen.getByLabelText(/email address/i);
      await user.type(emailInput, 'invalid-email');

      // HTML5 validation will handle this, but we can test the input type
      expect(emailInput).toHaveAttribute('type', 'email');
    });
  });

  describe('Form Interaction', () => {
    it('should toggle password visibility', async () => {
      const user = userEvent.setup();
      render(<SecureCustomerLoginForm />);

      const passwordInput = screen.getByLabelText(/password/i);
      const toggleButton = screen.getByRole('button', { name: '' }); // Eye icon button

      // Initially password should be hidden
      expect(passwordInput).toHaveAttribute('type', 'password');

      // Click to show password
      await user.click(toggleButton);
      expect(passwordInput).toHaveAttribute('type', 'text');

      // Click to hide password again
      await user.click(toggleButton);
      expect(passwordInput).toHaveAttribute('type', 'password');
    });

    it('should update form state on input changes', async () => {
      const user = userEvent.setup();
      render(<SecureCustomerLoginForm />);

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const portalIdInput = screen.getByLabelText(/portal id/i);

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'SecurePass123!');
      await user.type(portalIdInput, 'test-portal');

      expect(emailInput).toHaveValue('test@example.com');
      expect(passwordInput).toHaveValue('SecurePass123!');
      expect(portalIdInput).toHaveValue('test-portal');
    });

    it('should handle remember me checkbox', async () => {
      const user = userEvent.setup();
      render(<SecureCustomerLoginForm />);

      const rememberMeCheckbox = screen.getByRole('checkbox', { name: /remember me/i });

      expect(rememberMeCheckbox).not.toBeChecked();
      await user.click(rememberMeCheckbox);
      expect(rememberMeCheckbox).toBeChecked();
    });
  });

  describe('Authentication Flow Integration', () => {
    it('should complete successful login workflow', async () => {
      const user = userEvent.setup();
      mockLogin.mockResolvedValue({
        success: true,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          name: 'Test User',
          accountNumber: 'ACC123456',
        },
      });

      render(<SecureCustomerLoginForm />);

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const portalIdInput = screen.getByLabelText(/portal id/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'SecurePass123!');
      await user.type(portalIdInput, 'test-portal');
      await user.click(submitButton);

      expect(mockLogin).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'SecurePass123!',
        portalId: 'test-portal',
      });

      // Should reset attempt count on success

      // Should show success state
      await waitFor(() => {
        expect(screen.getByText('Login Successful!')).toBeInTheDocument();
      });
    });

    it('should show loading state during submission', async () => {
      const user = userEvent.setup();
      let resolveLogin: (value: any) => void;
      mockLogin.mockReturnValue(
        new Promise((resolve) => {
          resolveLogin = resolve;
        })
      );

      render(<SecureCustomerLoginForm />);

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'SecurePass123!');
      await user.click(submitButton);

      expect(screen.getByText(/signing in.../i)).toBeInTheDocument();
      expect(submitButton).toBeDisabled();

      // Resolve the login
      resolveLogin!({ success: true });
      await waitFor(() => {
        expect(screen.queryByText(/signing in.../i)).not.toBeInTheDocument();
      });
    });

    it('should handle authentication failure with user feedback', async () => {
      const user = userEvent.setup();
      mockLogin.mockResolvedValue({
        success: false,
        error: 'Invalid credentials',
      });

      render(<SecureCustomerLoginForm />);

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'wrongpassword');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/invalid email or password/i)).toBeInTheDocument();
      });

      // Should show attempt warning after multiple failures
      await user.click(submitButton);
      await waitFor(() => {
        expect(screen.getByText(/security notice/i)).toBeInTheDocument();
      });
    });

    it('should handle server-side rate limiting via API responses', async () => {
      const user = userEvent.setup();
      mockLogin.mockRejectedValue({
        status: 429,
        message: 'Too many attempts',
      });

      render(<SecureCustomerLoginForm />);

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/too many login attempts/i)).toBeInTheDocument();
      });

      // Should use platform error handler for consistent error processing
      expect(mockHandleError).toHaveBeenCalledWith(
        expect.objectContaining({
          status: 429,
          message: 'Too many attempts',
        }),
        'Login attempt'
      );
    });

    it('should handle network errors gracefully', async () => {
      const user = userEvent.setup();
      mockLogin.mockRejectedValue(new Error('Network error'));

      render(<SecureCustomerLoginForm />);

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'SecurePass123!');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/network error/i)).toBeInTheDocument();
      });

      // Should use platform error handler for network errors
      expect(mockHandleError).toHaveBeenCalledWith(expect.any(Error), 'Login attempt');
    });

    it('should clear errors when user starts typing', async () => {
      const user = userEvent.setup();
      mockLogin.mockResolvedValue({
        success: false,
        error: 'Invalid credentials',
      });

      render(<SecureCustomerLoginForm />);

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      // Submit with wrong credentials
      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'wrongpassword');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
      });

      // Start typing again - error should clear
      await user.type(passwordInput, '!');
      expect(screen.queryByText('Invalid credentials')).not.toBeInTheDocument();
    });
  });

  describe('Success State', () => {
    it('should show success message and redirect after successful login', async () => {
      const user = userEvent.setup();
      mockLogin.mockResolvedValue({ success: true });

      render(<SecureCustomerLoginForm />);

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'SecurePass123!');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Login Successful!')).toBeInTheDocument();
        expect(screen.getByText('Redirecting you to your dashboard...')).toBeInTheDocument();
      });

      // Should redirect after delay
      await waitFor(
        () => {
          expect(mockRouter.push).toHaveBeenCalledWith('/dashboard');
        },
        { timeout: 2000 }
      );
    });
  });

  describe('Navigation Links', () => {
    it('should have forgot password link', () => {
      render(<SecureCustomerLoginForm />);
      const forgotPasswordLink = screen.getByText('Forgot password?');
      expect(forgotPasswordLink).toBeInTheDocument();
    });

    it('should navigate to forgot password page', async () => {
      const user = userEvent.setup();
      render(<SecureCustomerLoginForm />);

      const forgotPasswordLink = screen.getByText('Forgot password?');
      await user.click(forgotPasswordLink);

      expect(mockRouter.push).toHaveBeenCalledWith('/forgot-password');
    });

    it('should have contact us link for new users', async () => {
      const user = userEvent.setup();
      render(<SecureCustomerLoginForm />);

      const contactUsLink = screen.getByText('Contact us to get started');
      await user.click(contactUsLink);

      expect(mockRouter.push).toHaveBeenCalledWith('/contact');
    });
  });

  describe('Accessibility', () => {
    it('should have proper form labels and associations', () => {
      render(<SecureCustomerLoginForm />);

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const portalIdInput = screen.getByLabelText(/portal id/i);

      expect(emailInput).toHaveAttribute('id');
      expect(passwordInput).toHaveAttribute('id');
      expect(portalIdInput).toHaveAttribute('id');
    });

    it('should have proper ARIA attributes for error states', async () => {
      const user = userEvent.setup();
      mockLogin.mockResolvedValue({
        success: false,
        error: 'Invalid credentials',
      });

      render(<SecureCustomerLoginForm />);

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      await user.click(submitButton);

      await waitFor(() => {
        const errorMessage = screen.getByRole('alert');
        expect(errorMessage).toBeInTheDocument();
        expect(errorMessage).toHaveTextContent('Invalid credentials');
      });
    });

    it('should support keyboard navigation', async () => {
      render(<SecureCustomerLoginForm />);

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const portalIdInput = screen.getByLabelText(/portal id/i);
      const rememberMeCheckbox = screen.getByRole('checkbox', { name: /remember me/i });
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      // Tab through form elements
      emailInput.focus();
      expect(document.activeElement).toBe(emailInput);

      fireEvent.keyDown(emailInput, { key: 'Tab' });
      expect(document.activeElement).toBe(portalIdInput);

      fireEvent.keyDown(portalIdInput, { key: 'Tab' });
      expect(document.activeElement).toBe(passwordInput);

      // Continue tabbing through other form elements
      fireEvent.keyDown(passwordInput, { key: 'Tab' });
      fireEvent.keyDown(document.activeElement!, { key: 'Tab' }); // Password toggle button
      expect(document.activeElement).toBe(rememberMeCheckbox);

      fireEvent.keyDown(rememberMeCheckbox, { key: 'Tab' });
      fireEvent.keyDown(document.activeElement!, { key: 'Tab' }); // Forgot password link
      expect(document.activeElement).toBe(submitButton);
    });
  });

  describe('Security Features', () => {
    it('should display security notice', () => {
      render(<SecureCustomerLoginForm />);

      expect(screen.getByText(/secure login/i)).toBeInTheDocument();
      expect(screen.getByText(/your connection is encrypted/i)).toBeInTheDocument();
    });

    it('should have autocomplete attributes for better security', () => {
      render(<SecureCustomerLoginForm />);

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);

      expect(emailInput).toHaveAttribute('autoComplete', 'email');
      expect(passwordInput).toHaveAttribute('autoComplete', 'current-password');
    });

    it('should have proper input types for security', () => {
      render(<SecureCustomerLoginForm />);

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);

      expect(emailInput).toHaveAttribute('type', 'email');
      expect(passwordInput).toHaveAttribute('type', 'password');
    });
  });

  describe('Help and Support', () => {
    it('should display support contact information', () => {
      render(<SecureCustomerLoginForm />);

      expect(screen.getByText(/need help\?/i)).toBeInTheDocument();
      expect(screen.getByText('support@dotmac.com')).toBeInTheDocument();
      expect(screen.getByText('+1 (555) DOT-MAC')).toBeInTheDocument();
    });

    it('should have working support links', () => {
      render(<SecureCustomerLoginForm />);

      const emailLink = screen.getByText('support@dotmac.com');
      const phoneLink = screen.getByText('+1 (555) DOT-MAC');

      expect(emailLink).toHaveAttribute('href', 'mailto:support@dotmac.com');
      expect(phoneLink).toHaveAttribute('href', 'tel:+1-555-DOTMAC');
    });
  });
});
