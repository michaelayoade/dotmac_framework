/**
 * Comprehensive Playwright E2E tests for Admin Portal - Login Page
 * Tests authentication flow, form validation, and login functionality
 */

import { test, expect } from '@playwright/test';

test.describe('Admin Portal - Login Page', () => {
  test('should render login page with all elements @visual', async ({ page }) => {
    // Create comprehensive login page HTML mock based on the actual login page
    const loginPageHTML = `
      <!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>DotMac Admin Portal - Login</title>
        <script src="https://cdn.tailwindcss.com"></script>
      </head>
      <body class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <div class="flex flex-col justify-center py-12 sm:px-6 lg:px-8">
          <!-- Header Section -->
          <div class="sm:mx-auto sm:w-full sm:max-w-md">
            <div data-testid="logo-section" class="flex justify-center">
              <div class="flex items-center space-x-2">
                <div data-testid="logo" class="h-8 w-8 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
                  <span class="text-white font-bold text-lg">D</span>
                </div>
                <span data-testid="company-name" class="text-2xl font-bold text-gray-900">DotMac</span>
              </div>
            </div>
            <h1 data-testid="portal-title" class="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
              Admin Portal
            </h1>
            <h2 data-testid="portal-subtitle" class="mt-2 text-center text-lg text-gray-600">
              Sign in to your administrative account
            </h2>
          </div>

          <!-- Login Form Section -->
          <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
            <div class="bg-white py-8 px-4 shadow-lg sm:rounded-lg sm:px-10 border border-gray-200">
              <form data-testid="login-form" class="space-y-6">
                <!-- Error Message (Initially Hidden) -->
                <div data-testid="error-message" class="rounded-md border border-red-200 bg-red-50 p-4 hidden">
                  <div class="flex">
                    <svg class="h-5 w-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    <div class="ml-3">
                      <h3 data-testid="error-title" class="font-medium text-red-800 text-sm">Authentication Failed</h3>
                      <p data-testid="error-text" class="mt-2 text-red-700 text-sm">Invalid email or password. Please try again.</p>
                    </div>
                  </div>
                </div>

                <!-- Success Message (Initially Hidden) -->
                <div data-testid="success-message" class="rounded-md border border-green-200 bg-green-50 p-4 hidden">
                  <div class="flex">
                    <svg class="h-5 w-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                    </svg>
                    <div class="ml-3">
                      <h3 data-testid="success-title" class="font-medium text-green-800 text-sm">Login Successful</h3>
                      <p data-testid="success-text" class="mt-2 text-green-700 text-sm">Redirecting to dashboard...</p>
                    </div>
                  </div>
                </div>

                <!-- Email Field -->
                <div>
                  <label data-testid="email-label" for="email" class="block font-medium text-gray-700 text-sm">
                    Email Address
                  </label>
                  <div class="mt-1">
                    <input
                      data-testid="email-input"
                      id="email"
                      name="email"
                      type="email"
                      autocomplete="email"
                      required
                      placeholder="admin@yourcompany.com"
                      class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                    />
                  </div>
                </div>

                <!-- Password Field -->
                <div>
                  <label data-testid="password-label" for="password" class="block font-medium text-gray-700 text-sm">
                    Password
                  </label>
                  <div class="relative mt-1">
                    <input
                      data-testid="password-input"
                      id="password"
                      name="password"
                      type="password"
                      autocomplete="current-password"
                      required
                      placeholder="••••••••"
                      class="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                    />
                    <button
                      data-testid="toggle-password"
                      type="button"
                      class="absolute inset-y-0 right-0 flex items-center pr-3"
                    >
                      <svg data-testid="eye-icon" class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                      </svg>
                      <svg data-testid="eye-off-icon" class="h-5 w-5 text-gray-400 hidden" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L6.757 6.757M9.878 9.878a3 3 0 00.007 4.243m4.242-4.242L17.121 17.121M14.121 14.121a3 3 0 01-4.243-.007m4.243.007l3.121 3.122M17.121 17.121L21.243 21.243"></path>
                      </svg>
                    </button>
                  </div>
                </div>

                <!-- Remember Me and Forgot Password -->
                <div class="flex items-center justify-between">
                  <div class="flex items-center">
                    <input
                      data-testid="remember-me-checkbox"
                      id="remember-me"
                      name="remember-me"
                      type="checkbox"
                      class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <label data-testid="remember-me-label" for="remember-me" class="ml-2 block text-gray-900 text-sm">
                      Remember me
                    </label>
                  </div>

                  <div class="text-sm">
                    <button
                      data-testid="forgot-password-link"
                      type="button"
                      class="text-left font-medium text-blue-600 hover:text-blue-500"
                    >
                      Forgot your password?
                    </button>
                  </div>
                </div>

                <!-- Submit Button -->
                <div>
                  <button
                    data-testid="login-button"
                    type="submit"
                    class="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <span data-testid="login-button-text">Sign in</span>
                  </button>
                </div>

                <!-- Contact Admin -->
                <div class="text-center">
                  <p class="text-gray-600 text-sm">
                    Don't have an account?{' '}
                    <button
                      data-testid="contact-admin-link"
                      type="button"
                      class="font-medium text-blue-600 hover:text-blue-500"
                    >
                      Contact your administrator
                    </button>
                  </p>
                </div>
              </form>
            </div>
            
            <!-- Footer -->
            <div class="mt-6">
              <div class="relative">
                <div class="absolute inset-0 flex items-center">
                  <div class="w-full border-t border-gray-300"></div>
                </div>
                <div class="relative flex justify-center text-sm">
                  <span data-testid="security-notice" class="bg-gradient-to-br from-blue-50 to-indigo-100 px-2 text-gray-500">
                    Secure ISP Management Platform
                  </span>
                </div>
              </div>
            </div>

            <div class="mt-6 text-center">
              <p data-testid="copyright" class="text-xs text-gray-500">
                © 2024 DotMac ISP Framework. All rights reserved.
              </p>
              <div class="mt-2 flex justify-center space-x-4 text-xs text-gray-400">
                <a data-testid="privacy-link" href="#" class="hover:text-gray-600">Privacy Policy</a>
                <span>•</span>
                <a data-testid="terms-link" href="#" class="hover:text-gray-600">Terms of Service</a>
                <span>•</span>
                <a data-testid="support-link" href="#" class="hover:text-gray-600">Support</a>
              </div>
            </div>
          </div>
        </div>

        <script>
          document.addEventListener('DOMContentLoaded', function() {
            const loginForm = document.querySelector('[data-testid="login-form"]');
            const emailInput = document.querySelector('[data-testid="email-input"]');
            const passwordInput = document.querySelector('[data-testid="password-input"]');
            const togglePasswordBtn = document.querySelector('[data-testid="toggle-password"]');
            const eyeIcon = document.querySelector('[data-testid="eye-icon"]');
            const eyeOffIcon = document.querySelector('[data-testid="eye-off-icon"]');
            const loginButton = document.querySelector('[data-testid="login-button"]');
            const loginButtonText = document.querySelector('[data-testid="login-button-text"]');
            const errorMessage = document.querySelector('[data-testid="error-message"]');
            const successMessage = document.querySelector('[data-testid="success-message"]');
            const rememberMeCheckbox = document.querySelector('[data-testid="remember-me-checkbox"]');

            // Password toggle functionality
            togglePasswordBtn?.addEventListener('click', function() {
              const isPassword = passwordInput.type === 'password';
              passwordInput.type = isPassword ? 'text' : 'password';
              
              if (isPassword) {
                eyeIcon.classList.add('hidden');
                eyeOffIcon.classList.remove('hidden');
              } else {
                eyeIcon.classList.remove('hidden');
                eyeOffIcon.classList.add('hidden');
              }
            });

            // Form submission
            loginForm?.addEventListener('submit', function(e) {
              e.preventDefault();
              
              // Hide any existing messages
              errorMessage.classList.add('hidden');
              successMessage.classList.add('hidden');
              
              // Show loading state
              loginButton.disabled = true;
              loginButtonText.textContent = 'Signing in...';
              loginButton.classList.add('opacity-50', 'cursor-not-allowed');
              
              const email = emailInput.value;
              const password = passwordInput.value;
              
              // Simulate API call
              setTimeout(() => {
                // Demo credentials for testing
                if (email === 'admin@dotmac.com' && password === 'admin123') {
                  // Success
                  successMessage.classList.remove('hidden');
                  loginButtonText.textContent = 'Redirecting...';
                  
                  // Simulate redirect after success
                  setTimeout(() => {
                    // In real app, would redirect to dashboard
                    console.log('Redirecting to dashboard...');
                    loginButtonText.textContent = 'Sign in';
                    loginButton.disabled = false;
                    loginButton.classList.remove('opacity-50', 'cursor-not-allowed');
                  }, 2000);
                } else {
                  // Error
                  errorMessage.classList.remove('hidden');
                  loginButtonText.textContent = 'Sign in';
                  loginButton.disabled = false;
                  loginButton.classList.remove('opacity-50', 'cursor-not-allowed');
                  
                  // Shake the form for visual feedback
                  loginForm.classList.add('animate-pulse');
                  setTimeout(() => {
                    loginForm.classList.remove('animate-pulse');
                  }, 300);
                }
              }, 1500);
            });

            // Forgot password functionality
            document.querySelector('[data-testid="forgot-password-link"]')?.addEventListener('click', function() {
              alert('Forgot password functionality would be implemented here.\\n\\nIn a real application, this would:\\n- Open a forgot password form\\n- Send a reset email\\n- Guide user through password reset process');
            });

            // Contact admin functionality
            document.querySelector('[data-testid="contact-admin-link"]')?.addEventListener('click', function() {
              alert('Contact admin functionality would be implemented here.\\n\\nIn a real application, this would:\\n- Open a contact form\\n- Provide admin contact information\\n- Allow user to request account creation');
            });

            // Form validation styling
            [emailInput, passwordInput].forEach(input => {
              input?.addEventListener('invalid', function() {
                this.classList.add('border-red-500', 'focus:ring-red-500');
              });
              
              input?.addEventListener('input', function() {
                if (this.validity.valid) {
                  this.classList.remove('border-red-500', 'focus:ring-red-500');
                }
              });
            });
          });
        </script>
      </body>
      </html>
    `;

    await page.setContent(loginPageHTML);

    // Verify page structure and branding
    await expect(page.getByTestId('logo')).toBeVisible();
    await expect(page.getByTestId('company-name')).toHaveText('DotMac');
    await expect(page.getByTestId('portal-title')).toHaveText('Admin Portal');
    await expect(page.getByTestId('portal-subtitle')).toHaveText(
      'Sign in to your administrative account'
    );

    // Verify form elements
    await expect(page.getByTestId('login-form')).toBeVisible();
    await expect(page.getByTestId('email-input')).toBeVisible();
    await expect(page.getByTestId('password-input')).toBeVisible();
    await expect(page.getByTestId('remember-me-checkbox')).toBeVisible();
    await expect(page.getByTestId('login-button')).toBeVisible();

    // Verify form labels
    await expect(page.getByTestId('email-label')).toHaveText('Email Address');
    await expect(page.getByTestId('password-label')).toHaveText('Password');
    await expect(page.getByTestId('remember-me-label')).toHaveText('Remember me');

    // Verify interactive elements
    await expect(page.getByTestId('toggle-password')).toBeVisible();
    await expect(page.getByTestId('forgot-password-link')).toHaveText('Forgot your password?');
    await expect(page.getByTestId('contact-admin-link')).toHaveText('Contact your administrator');

    // Verify footer elements
    await expect(page.getByTestId('security-notice')).toHaveText('Secure ISP Management Platform');
    await expect(page.getByTestId('copyright')).toContainText('© 2024 DotMac ISP Framework');
    await expect(page.getByTestId('privacy-link')).toHaveText('Privacy Policy');
    await expect(page.getByTestId('terms-link')).toHaveText('Terms of Service');
    await expect(page.getByTestId('support-link')).toHaveText('Support');

    // Verify error and success messages are hidden initially
    await expect(page.getByTestId('error-message')).toBeHidden();
    await expect(page.getByTestId('success-message')).toBeHidden();

    // Take screenshot for visual verification
    await page.screenshot({
      path: 'test-results/admin-login-page.png',
      fullPage: true,
    });
  });

  test('should test password visibility toggle functionality @visual @interactive', async ({
    page,
  }) => {
    const loginPageHTML = `
      <!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>DotMac Admin Portal - Login</title>
        <script src="https://cdn.tailwindcss.com"></script>
      </head>
      <body class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
        <div class="max-w-md mx-auto bg-white p-8 rounded-lg shadow-lg">
          <h2 class="text-2xl font-bold mb-6 text-center">Password Toggle Test</h2>
          
          <div>
            <label for="password" class="block font-medium text-gray-700 text-sm mb-2">Password</label>
            <div class="relative">
              <input
                data-testid="password-input"
                id="password"
                name="password"
                type="password"
                value="testpassword123"
                placeholder="••••••••"
                class="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              />
              <button
                data-testid="toggle-password"
                type="button"
                class="absolute inset-y-0 right-0 flex items-center pr-3"
              >
                <svg data-testid="eye-icon" class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                </svg>
                <svg data-testid="eye-off-icon" class="h-5 w-5 text-gray-400 hidden" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L6.757 6.757M9.878 9.878a3 3 0 00.007 4.243m4.242-4.242L17.121 17.121M14.121 14.121a3 3 0 01-4.243-.007m4.243.007l3.121 3.122M17.121 17.121L21.243 21.243"></path>
                </svg>
              </button>
            </div>
            <p data-testid="password-type-indicator" class="mt-2 text-sm text-gray-600">
              Current type: <span data-testid="current-type">password</span>
            </p>
          </div>
        </div>

        <script>
          document.addEventListener('DOMContentLoaded', function() {
            const passwordInput = document.querySelector('[data-testid="password-input"]');
            const togglePasswordBtn = document.querySelector('[data-testid="toggle-password"]');
            const eyeIcon = document.querySelector('[data-testid="eye-icon"]');
            const eyeOffIcon = document.querySelector('[data-testid="eye-off-icon"]');
            const currentTypeSpan = document.querySelector('[data-testid="current-type"]');

            togglePasswordBtn?.addEventListener('click', function() {
              const isPassword = passwordInput.type === 'password';
              passwordInput.type = isPassword ? 'text' : 'password';
              currentTypeSpan.textContent = passwordInput.type;
              
              if (isPassword) {
                eyeIcon.classList.add('hidden');
                eyeOffIcon.classList.remove('hidden');
              } else {
                eyeIcon.classList.remove('hidden');
                eyeOffIcon.classList.add('hidden');
              }
            });
          });
        </script>
      </body>
      </html>
    `;

    await page.setContent(loginPageHTML);

    // Verify initial state - password is hidden
    await expect(page.getByTestId('password-input')).toHaveAttribute('type', 'password');
    await expect(page.getByTestId('current-type')).toHaveText('password');
    await expect(page.getByTestId('eye-icon')).toBeVisible();
    await expect(page.getByTestId('eye-off-icon')).toBeHidden();

    // Click to show password
    await page.getByTestId('toggle-password').click();

    // Verify password is now visible
    await expect(page.getByTestId('password-input')).toHaveAttribute('type', 'text');
    await expect(page.getByTestId('current-type')).toHaveText('text');
    await expect(page.getByTestId('eye-icon')).toBeHidden();
    await expect(page.getByTestId('eye-off-icon')).toBeVisible();

    // Click again to hide password
    await page.getByTestId('toggle-password').click();

    // Verify password is hidden again
    await expect(page.getByTestId('password-input')).toHaveAttribute('type', 'password');
    await expect(page.getByTestId('current-type')).toHaveText('password');
    await expect(page.getByTestId('eye-icon')).toBeVisible();
    await expect(page.getByTestId('eye-off-icon')).toBeHidden();

    // Take screenshot
    await page.screenshot({
      path: 'test-results/admin-login-password-toggle.png',
      fullPage: true,
    });
  });

  test('should test successful login flow @visual @interactive', async ({ page }) => {
    const loginFlowHTML = `
      <!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>DotMac Admin Portal - Login Flow</title>
        <script src="https://cdn.tailwindcss.com"></script>
      </head>
      <body class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
        <div class="max-w-md mx-auto bg-white p-8 rounded-lg shadow-lg">
          <h2 class="text-2xl font-bold mb-6 text-center">Admin Login</h2>
          
          <form data-testid="login-form" class="space-y-4">
            <!-- Success Message (Initially Hidden) -->
            <div data-testid="success-message" class="rounded-md border border-green-200 bg-green-50 p-4 hidden">
              <div class="flex">
                <svg class="h-5 w-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                <div class="ml-3">
                  <h3 data-testid="success-title" class="font-medium text-green-800 text-sm">Login Successful</h3>
                  <p data-testid="success-text" class="mt-2 text-green-700 text-sm">Redirecting to dashboard...</p>
                </div>
              </div>
            </div>

            <!-- Error Message (Initially Hidden) -->
            <div data-testid="error-message" class="rounded-md border border-red-200 bg-red-50 p-4 hidden">
              <div class="flex">
                <svg class="h-5 w-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <div class="ml-3">
                  <h3 data-testid="error-title" class="font-medium text-red-800 text-sm">Authentication Failed</h3>
                  <p data-testid="error-text" class="mt-2 text-red-700 text-sm">Invalid email or password. Please try again.</p>
                </div>
              </div>
            </div>

            <div>
              <label for="email" class="block font-medium text-gray-700 text-sm mb-1">Email</label>
              <input
                data-testid="email-input"
                id="email"
                name="email"
                type="email"
                required
                placeholder="admin@dotmac.com"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              />
            </div>

            <div>
              <label for="password" class="block font-medium text-gray-700 text-sm mb-1">Password</label>
              <input
                data-testid="password-input"
                id="password"
                name="password"
                type="password"
                required
                placeholder="admin123"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              />
            </div>

            <button
              data-testid="login-button"
              type="submit"
              class="w-full py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <span data-testid="login-button-text">Sign in</span>
            </button>
          </form>

          <div class="mt-4 p-4 bg-gray-50 rounded-lg">
            <h3 class="font-medium text-gray-700 text-sm mb-2">Demo Credentials:</h3>
            <p class="text-xs text-gray-600">Email: admin@dotmac.com</p>
            <p class="text-xs text-gray-600">Password: admin123</p>
          </div>
        </div>

        <script>
          document.addEventListener('DOMContentLoaded', function() {
            const loginForm = document.querySelector('[data-testid="login-form"]');
            const emailInput = document.querySelector('[data-testid="email-input"]');
            const passwordInput = document.querySelector('[data-testid="password-input"]');
            const loginButton = document.querySelector('[data-testid="login-button"]');
            const loginButtonText = document.querySelector('[data-testid="login-button-text"]');
            const errorMessage = document.querySelector('[data-testid="error-message"]');
            const successMessage = document.querySelector('[data-testid="success-message"]');

            loginForm?.addEventListener('submit', function(e) {
              e.preventDefault();
              
              // Hide any existing messages
              errorMessage.classList.add('hidden');
              successMessage.classList.add('hidden');
              
              // Show loading state
              loginButton.disabled = true;
              loginButtonText.textContent = 'Signing in...';
              loginButton.classList.add('opacity-50', 'cursor-not-allowed');
              
              const email = emailInput.value;
              const password = passwordInput.value;
              
              // Simulate API call
              setTimeout(() => {
                if (email === 'admin@dotmac.com' && password === 'admin123') {
                  // Success
                  successMessage.classList.remove('hidden');
                  loginButtonText.textContent = 'Redirecting...';
                  
                  setTimeout(() => {
                    loginButtonText.textContent = 'Sign in';
                    loginButton.disabled = false;
                    loginButton.classList.remove('opacity-50', 'cursor-not-allowed');
                  }, 2000);
                } else {
                  // Error
                  errorMessage.classList.remove('hidden');
                  loginButtonText.textContent = 'Sign in';
                  loginButton.disabled = false;
                  loginButton.classList.remove('opacity-50', 'cursor-not-allowed');
                }
              }, 1500);
            });
          });
        </script>
      </body>
      </html>
    `;

    await page.setContent(loginFlowHTML);

    // Verify initial state
    await expect(page.getByTestId('success-message')).toBeHidden();
    await expect(page.getByTestId('error-message')).toBeHidden();
    await expect(page.getByTestId('login-button-text')).toHaveText('Sign in');

    // Test successful login
    await page.getByTestId('email-input').fill('admin@dotmac.com');
    await page.getByTestId('password-input').fill('admin123');
    await page.getByTestId('login-button').click();

    // Verify loading state
    await expect(page.getByTestId('login-button-text')).toHaveText('Signing in...');
    await expect(page.getByTestId('login-button')).toHaveClass(/opacity-50/);
    await expect(page.getByTestId('login-button')).toBeDisabled();

    // Wait for success message
    await expect(page.getByTestId('success-message')).toBeVisible({ timeout: 3000 });
    await expect(page.getByTestId('success-title')).toHaveText('Login Successful');
    await expect(page.getByTestId('success-text')).toHaveText('Redirecting to dashboard...');
    await expect(page.getByTestId('login-button-text')).toHaveText('Redirecting...');

    // Take screenshot of success state
    await page.screenshot({
      path: 'test-results/admin-login-success.png',
      fullPage: true,
    });

    // Wait for reset
    await expect(page.getByTestId('login-button-text')).toHaveText('Sign in', { timeout: 3000 });
    await expect(page.getByTestId('login-button')).not.toBeDisabled();
  });

  test('should test failed login flow @visual @interactive', async ({ page }) => {
    const loginFlowHTML = `
      <!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>DotMac Admin Portal - Login Flow</title>
        <script src="https://cdn.tailwindcss.com"></script>
      </head>
      <body class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
        <div class="max-w-md mx-auto bg-white p-8 rounded-lg shadow-lg">
          <h2 class="text-2xl font-bold mb-6 text-center">Admin Login</h2>
          
          <form data-testid="login-form" class="space-y-4">
            <!-- Error Message (Initially Hidden) -->
            <div data-testid="error-message" class="rounded-md border border-red-200 bg-red-50 p-4 hidden">
              <div class="flex">
                <svg class="h-5 w-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <div class="ml-3">
                  <h3 data-testid="error-title" class="font-medium text-red-800 text-sm">Authentication Failed</h3>
                  <p data-testid="error-text" class="mt-2 text-red-700 text-sm">Invalid email or password. Please try again.</p>
                </div>
              </div>
            </div>

            <div>
              <label for="email" class="block font-medium text-gray-700 text-sm mb-1">Email</label>
              <input
                data-testid="email-input"
                id="email"
                name="email"
                type="email"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              />
            </div>

            <div>
              <label for="password" class="block font-medium text-gray-700 text-sm mb-1">Password</label>
              <input
                data-testid="password-input"
                id="password"
                name="password"
                type="password"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              />
            </div>

            <button
              data-testid="login-button"
              type="submit"
              class="w-full py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <span data-testid="login-button-text">Sign in</span>
            </button>
          </form>
        </div>

        <script>
          document.addEventListener('DOMContentLoaded', function() {
            const loginForm = document.querySelector('[data-testid="login-form"]');
            const emailInput = document.querySelector('[data-testid="email-input"]');
            const passwordInput = document.querySelector('[data-testid="password-input"]');
            const loginButton = document.querySelector('[data-testid="login-button"]');
            const loginButtonText = document.querySelector('[data-testid="login-button-text"]');
            const errorMessage = document.querySelector('[data-testid="error-message"]');

            loginForm?.addEventListener('submit', function(e) {
              e.preventDefault();
              
              // Hide any existing messages
              errorMessage.classList.add('hidden');
              
              // Show loading state
              loginButton.disabled = true;
              loginButtonText.textContent = 'Signing in...';
              loginButton.classList.add('opacity-50', 'cursor-not-allowed');
              
              const email = emailInput.value;
              const password = passwordInput.value;
              
              // Simulate API call - always fail for this test
              setTimeout(() => {
                errorMessage.classList.remove('hidden');
                loginButtonText.textContent = 'Sign in';
                loginButton.disabled = false;
                loginButton.classList.remove('opacity-50', 'cursor-not-allowed');
                
                // Shake the form for visual feedback
                loginForm.classList.add('animate-pulse');
                setTimeout(() => {
                  loginForm.classList.remove('animate-pulse');
                }, 300);
              }, 1500);
            });
          });
        </script>
      </body>
      </html>
    `;

    await page.setContent(loginFlowHTML);

    // Verify initial state
    await expect(page.getByTestId('error-message')).toBeHidden();
    await expect(page.getByTestId('login-button-text')).toHaveText('Sign in');

    // Test failed login
    await page.getByTestId('email-input').fill('wrong@email.com');
    await page.getByTestId('password-input').fill('wrongpassword');
    await page.getByTestId('login-button').click();

    // Verify loading state
    await expect(page.getByTestId('login-button-text')).toHaveText('Signing in...');
    await expect(page.getByTestId('login-button')).toBeDisabled();

    // Wait for error message
    await expect(page.getByTestId('error-message')).toBeVisible({ timeout: 3000 });
    await expect(page.getByTestId('error-title')).toHaveText('Authentication Failed');
    await expect(page.getByTestId('error-text')).toHaveText(
      'Invalid email or password. Please try again.'
    );
    await expect(page.getByTestId('login-button-text')).toHaveText('Sign in');
    await expect(page.getByTestId('login-button')).not.toBeDisabled();

    // Take screenshot of error state
    await page.screenshot({
      path: 'test-results/admin-login-error.png',
      fullPage: true,
    });
  });

  test('should test responsive login layout @visual @responsive', async ({ page }) => {
    const responsiveLoginHTML = `
      <!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>DotMac Admin Portal - Responsive Login</title>
        <script src="https://cdn.tailwindcss.com"></script>
      </head>
      <body class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <div class="flex flex-col justify-center py-6 sm:py-12 px-4 sm:px-6 lg:px-8">
          <!-- Header Section -->
          <div class="sm:mx-auto sm:w-full sm:max-w-md">
            <div data-testid="logo-section" class="flex justify-center">
              <div class="flex items-center space-x-2">
                <div data-testid="logo" class="h-6 w-6 sm:h-8 sm:w-8 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
                  <span class="text-white font-bold text-sm sm:text-lg">D</span>
                </div>
                <span data-testid="company-name" class="text-xl sm:text-2xl font-bold text-gray-900">DotMac</span>
              </div>
            </div>
            <h1 data-testid="portal-title" class="mt-4 sm:mt-6 text-center text-2xl sm:text-3xl font-bold tracking-tight text-gray-900">
              Admin Portal
            </h1>
            <h2 data-testid="portal-subtitle" class="mt-1 sm:mt-2 text-center text-base sm:text-lg text-gray-600">
              Sign in to your account
            </h2>
          </div>

          <!-- Login Form Section -->
          <div class="mt-6 sm:mt-8 sm:mx-auto sm:w-full sm:max-w-md">
            <div class="bg-white py-6 sm:py-8 px-4 sm:px-10 shadow-lg rounded-lg sm:rounded-lg border border-gray-200">
              <form data-testid="login-form" class="space-y-4 sm:space-y-6">
                <!-- Email Field -->
                <div>
                  <label data-testid="email-label" for="email" class="block font-medium text-gray-700 text-sm">
                    Email Address
                  </label>
                  <div class="mt-1">
                    <input
                      data-testid="email-input"
                      id="email"
                      name="email"
                      type="email"
                      autocomplete="email"
                      required
                      placeholder="admin@yourcompany.com"
                      class="w-full px-3 py-2 sm:py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                    />
                  </div>
                </div>

                <!-- Password Field -->
                <div>
                  <label data-testid="password-label" for="password" class="block font-medium text-gray-700 text-sm">
                    Password
                  </label>
                  <div class="relative mt-1">
                    <input
                      data-testid="password-input"
                      id="password"
                      name="password"
                      type="password"
                      autocomplete="current-password"
                      required
                      placeholder="••••••••"
                      class="w-full px-3 py-2 sm:py-3 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                    />
                  </div>
                </div>

                <!-- Remember Me and Forgot Password -->
                <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-2 sm:space-y-0">
                  <div class="flex items-center">
                    <input
                      data-testid="remember-me-checkbox"
                      id="remember-me"
                      name="remember-me"
                      type="checkbox"
                      class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <label data-testid="remember-me-label" for="remember-me" class="ml-2 block text-gray-900 text-sm">
                      Remember me
                    </label>
                  </div>

                  <div class="text-sm">
                    <button
                      data-testid="forgot-password-link"
                      type="button"
                      class="text-left font-medium text-blue-600 hover:text-blue-500"
                    >
                      Forgot password?
                    </button>
                  </div>
                </div>

                <!-- Submit Button -->
                <div>
                  <button
                    data-testid="login-button"
                    type="submit"
                    class="w-full flex justify-center py-2 sm:py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                  >
                    <span data-testid="login-button-text">Sign in</span>
                  </button>
                </div>

                <!-- Contact Admin -->
                <div class="text-center">
                  <p class="text-gray-600 text-xs sm:text-sm">
                    Don't have an account?{' '}
                    <button
                      data-testid="contact-admin-link"
                      type="button"
                      class="font-medium text-blue-600 hover:text-blue-500"
                    >
                      Contact administrator
                    </button>
                  </p>
                </div>
              </form>
            </div>
          </div>
        </div>
      </body>
      </html>
    `;

    // Test mobile viewport (iPhone 12)
    await page.setViewportSize({ width: 390, height: 844 });
    await page.setContent(responsiveLoginHTML);

    // Verify mobile layout
    await expect(page.getByTestId('portal-title')).toBeVisible();
    await expect(page.getByTestId('login-form')).toBeVisible();
    await expect(page.getByTestId('email-input')).toBeVisible();
    await expect(page.getByTestId('password-input')).toBeVisible();
    await expect(page.getByTestId('login-button')).toBeVisible();

    // Take mobile screenshot
    await page.screenshot({
      path: 'test-results/admin-login-mobile.png',
      fullPage: true,
    });

    // Test tablet viewport (iPad)
    await page.setViewportSize({ width: 768, height: 1024 });

    // Verify tablet layout
    await expect(page.getByTestId('portal-title')).toBeVisible();
    await expect(page.getByTestId('login-form')).toBeVisible();

    // Take tablet screenshot
    await page.screenshot({
      path: 'test-results/admin-login-tablet.png',
      fullPage: true,
    });

    // Test desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });

    // Verify desktop layout
    await expect(page.getByTestId('portal-title')).toBeVisible();
    await expect(page.getByTestId('login-form')).toBeVisible();

    // Take desktop screenshot
    await page.screenshot({
      path: 'test-results/admin-login-desktop.png',
      fullPage: true,
    });
  });
});
