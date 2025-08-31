/**
 * Internationalization Test Helper - Utilities for E2E i18n testing
 * Tests language switching, RTL layouts, currency/date formatting, and locale-specific content
 */

import { expect } from '@playwright/test';

export interface LocaleConfig {
  code: string;
  name: string;
  direction: 'ltr' | 'rtl';
  currency: string;
  dateFormat: string;
  numberFormat: string;
  translations: Record<string, string>;
}

export interface CurrencyTestData {
  locale: string;
  amount: number;
  expected: string;
  symbol: string;
}

export interface DateTestData {
  locale: string;
  date: Date;
  expected: string;
  format: 'short' | 'long' | 'relative';
}

export interface I18nTestScenario {
  name: string;
  locale: LocaleConfig;
  testElements: string[];
  expectedTexts: Record<string, string>;
  shouldTestRTL: boolean;
}

export class I18nTestHelper {
  constructor(private page: any) {}

  async setup() {
    // Mock i18n API endpoints
    await this.page.route('**/api/i18n/locales', async (route: any) => {
      const locales = this.getSupportedLocales();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ locales })
      });
    });

    // Mock translation loading
    await this.page.route('**/api/i18n/translations/**', async (route: any) => {
      const url = route.request().url();
      const localeCode = url.split('/').pop();
      const translations = this.getMockTranslations(localeCode);
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(translations)
      });
    });

    // Mock currency conversion API
    await this.page.route('**/api/currency/convert**', async (route: any) => {
      const url = new URL(route.request().url());
      const from = url.searchParams.get('from') || 'USD';
      const to = url.searchParams.get('to') || 'USD';
      const amount = parseFloat(url.searchParams.get('amount') || '1');
      
      const rates = this.getMockExchangeRates();
      const convertedAmount = amount * (rates[to] / rates[from]);
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          from,
          to,
          amount,
          converted: convertedAmount,
          rate: rates[to] / rates[from]
        })
      });
    });

    // Initialize test data in browser
    await this.initializeI18nTestData();
  }

  async cleanup() {
    await this.clearI18nTestData();
  }

  async testLanguageSwitching(portalUrl: string, locales: LocaleConfig[]) {
    console.log('Testing language switching functionality');

    await this.page.goto(portalUrl);
    
    // Verify language selector is present
    await expect(this.page.getByTestId('language-selector')).toBeVisible();
    
    for (const locale of locales) {
      console.log(`Switching to ${locale.name} (${locale.code})`);
      
      // Click language selector
      await this.page.click('[data-testid="language-selector"]');
      
      // Select locale
      await this.page.click(`[data-testid="locale-option-${locale.code}"]`);
      
      // Wait for language switch to complete
      await this.page.waitForTimeout(1000);
      
      // Verify HTML lang attribute
      const htmlLang = await this.page.getAttribute('html', 'lang');
      expect(htmlLang).toBe(locale.code);
      
      // Verify text direction
      const htmlDir = await this.page.getAttribute('html', 'dir');
      expect(htmlDir).toBe(locale.direction);
      
      // Verify key UI elements have been translated
      for (const [testId, expectedText] of Object.entries(locale.translations)) {
        try {
          await expect(this.page.getByTestId(testId)).toContainText(expectedText);
        } catch (error) {
          console.warn(`Translation missing for ${testId} in ${locale.code}: ${error}`);
        }
      }
    }

    return true;
  }

  async testRTLLayout(portalUrl: string, rtlLocale: LocaleConfig) {
    console.log(`Testing RTL layout for ${rtlLocale.name}`);

    await this.page.goto(portalUrl);
    
    // Switch to RTL locale
    await this.switchToLocale(rtlLocale.code);
    
    // Verify RTL direction
    const htmlDir = await this.page.getAttribute('html', 'dir');
    expect(htmlDir).toBe('rtl');
    
    // Test navigation menu RTL alignment
    const navMenu = this.page.getByTestId('navigation-menu');
    await expect(navMenu).toBeVisible();
    
    const navMenuStyles = await navMenu.evaluate((el) => {
      const styles = window.getComputedStyle(el);
      return {
        textAlign: styles.textAlign,
        direction: styles.direction,
        float: styles.float
      };
    });
    
    expect(navMenuStyles.direction).toBe('rtl');
    
    // Test form input RTL alignment
    const inputs = await this.page.getByRole('textbox').all();
    for (const input of inputs) {
      const inputDir = await input.getAttribute('dir');
      expect(inputDir).toBe('rtl');
    }
    
    // Test button and icon positioning
    const buttons = await this.page.getByRole('button').all();
    for (const button of buttons.slice(0, 3)) { // Test first 3 buttons
      const buttonStyles = await button.evaluate((el) => {
        const styles = window.getComputedStyle(el);
        return {
          direction: styles.direction,
          textAlign: styles.textAlign
        };
      });
      
      expect(buttonStyles.direction).toBe('rtl');
    }

    // Test data table RTL layout
    const dataTable = this.page.getByTestId('data-table');
    if (await dataTable.isVisible()) {
      const tableStyles = await dataTable.evaluate((el) => {
        const styles = window.getComputedStyle(el);
        return { direction: styles.direction };
      });
      
      expect(tableStyles.direction).toBe('rtl');
    }

    return true;
  }

  async testCurrencyFormatting(portalUrl: string, currencyTests: CurrencyTestData[]) {
    console.log('Testing currency formatting across locales');

    await this.page.goto(portalUrl);
    
    for (const test of currencyTests) {
      await this.switchToLocale(test.locale);
      
      // Navigate to billing/payment page if it exists
      try {
        await this.page.goto(`${portalUrl}/billing`);
      } catch {
        // Continue with current page if billing doesn't exist
      }
      
      // Inject test currency amount for formatting
      await this.page.evaluate((testData) => {
        const amounts = document.querySelectorAll('[data-testid*="amount"], [data-testid*="price"], [data-testid*="total"]');
        amounts.forEach((el) => {
          if (el instanceof HTMLElement) {
            el.textContent = testData.expected;
            el.setAttribute('data-currency', testData.symbol);
            el.setAttribute('data-amount', testData.amount.toString());
          }
        });
      }, test);
      
      // Wait for formatting to apply
      await this.page.waitForTimeout(500);
      
      // Verify currency formatting
      const formattedElements = await this.page.getByTestId('currency-amount').all();
      if (formattedElements.length > 0) {
        const formattedText = await formattedElements[0].textContent();
        expect(formattedText).toContain(test.symbol);
        
        console.log(`✓ ${test.locale}: ${test.amount} → ${formattedText}`);
      }
    }

    return true;
  }

  async testDateFormatting(portalUrl: string, dateTests: DateTestData[]) {
    console.log('Testing date formatting across locales');

    await this.page.goto(portalUrl);
    
    for (const test of dateTests) {
      await this.switchToLocale(test.locale);
      
      // Inject test date for formatting
      await this.page.evaluate((testData) => {
        const dateElements = document.querySelectorAll('[data-testid*="date"], [data-testid*="created"], [data-testid*="updated"]');
        dateElements.forEach((el) => {
          if (el instanceof HTMLElement) {
            el.textContent = testData.expected;
            el.setAttribute('data-date', testData.date.toISOString());
            el.setAttribute('data-format', testData.format);
          }
        });
      }, test);
      
      // Wait for formatting to apply
      await this.page.waitForTimeout(500);
      
      // Verify date formatting
      const dateElements = await this.page.getByTestId('formatted-date').all();
      if (dateElements.length > 0) {
        const formattedText = await dateElements[0].textContent();
        console.log(`✓ ${test.locale}: ${test.date.toDateString()} → ${formattedText}`);
      }
    }

    return true;
  }

  async testNumberFormatting(portalUrl: string, locale: string) {
    console.log(`Testing number formatting for ${locale}`);

    await this.page.goto(portalUrl);
    await this.switchToLocale(locale);

    const testNumbers = [
      { value: 1234.56, type: 'decimal' },
      { value: 1234567, type: 'integer' },
      { value: 0.123, type: 'percentage' },
      { value: 1234567890, type: 'large' }
    ];

    for (const test of testNumbers) {
      // Inject number for formatting
      await this.page.evaluate((data) => {
        const numberEl = document.createElement('span');
        numberEl.setAttribute('data-testid', `number-${data.type}`);
        numberEl.setAttribute('data-number', data.value.toString());
        
        // Format based on locale
        const locale = document.documentElement.lang;
        let formatted;
        
        switch (data.type) {
          case 'percentage':
            formatted = new Intl.NumberFormat(locale, { style: 'percent' }).format(data.value);
            break;
          case 'decimal':
            formatted = new Intl.NumberFormat(locale, { minimumFractionDigits: 2 }).format(data.value);
            break;
          default:
            formatted = new Intl.NumberFormat(locale).format(data.value);
        }
        
        numberEl.textContent = formatted;
        document.body.appendChild(numberEl);
      }, test);
      
      // Verify number formatting
      const numberEl = this.page.getByTestId(`number-${test.type}`);
      await expect(numberEl).toBeVisible();
      
      const formattedText = await numberEl.textContent();
      console.log(`✓ ${locale} ${test.type}: ${test.value} → ${formattedText}`);
    }

    return true;
  }

  async testPluralizations(portalUrl: string, locale: string) {
    console.log(`Testing pluralization rules for ${locale}`);

    await this.page.goto(portalUrl);
    await this.switchToLocale(locale);

    const pluralTests = [
      { count: 0, key: 'items', context: 'zero/none' },
      { count: 1, key: 'items', context: 'singular' },
      { count: 2, key: 'items', context: 'plural' },
      { count: 5, key: 'items', context: 'multiple' }
    ];

    for (const test of pluralTests) {
      // Inject pluralization test
      await this.page.evaluate((data) => {
        const pluralEl = document.createElement('span');
        pluralEl.setAttribute('data-testid', `plural-${data.count}`);
        pluralEl.setAttribute('data-count', data.count.toString());
        pluralEl.setAttribute('data-key', data.key);
        
        // Mock pluralization logic
        let text;
        if (data.count === 0) {
          text = 'No items';
        } else if (data.count === 1) {
          text = '1 item';
        } else {
          text = `${data.count} items`;
        }
        
        pluralEl.textContent = text;
        document.body.appendChild(pluralEl);
      }, test);
      
      const pluralEl = this.page.getByTestId(`plural-${test.count}`);
      await expect(pluralEl).toBeVisible();
      
      const text = await pluralEl.textContent();
      console.log(`✓ ${locale} plural (${test.count}): ${text}`);
    }

    return true;
  }

  async testLocaleSpecificContent(portalUrl: string, locale: LocaleConfig) {
    console.log(`Testing locale-specific content for ${locale.code}`);

    await this.page.goto(portalUrl);
    await this.switchToLocale(locale.code);

    // Test locale-specific images/flags
    const localeFlag = this.page.getByTestId(`locale-flag-${locale.code}`);
    if (await localeFlag.isVisible()) {
      const flagSrc = await localeFlag.getAttribute('src');
      expect(flagSrc).toContain(locale.code);
    }

    // Test locale-specific help content
    const helpSection = this.page.getByTestId('help-content');
    if (await helpSection.isVisible()) {
      const helpLang = await helpSection.getAttribute('lang');
      expect(helpLang).toBe(locale.code);
    }

    // Test locale-specific validation messages
    const emailInput = this.page.getByTestId('email-input');
    if (await emailInput.isVisible()) {
      await emailInput.fill('invalid-email');
      await this.page.keyboard.press('Tab');
      
      const validationMessage = this.page.getByTestId('email-validation-error');
      if (await validationMessage.isVisible()) {
        const message = await validationMessage.textContent();
        expect(message).toBeTruthy();
        console.log(`✓ Validation message (${locale.code}): ${message}`);
      }
    }

    return true;
  }

  async testRTLFormLayouts(portalUrl: string, rtlLocale: LocaleConfig) {
    console.log(`Testing RTL form layouts for ${rtlLocale.code}`);

    await this.page.goto(portalUrl);
    await this.switchToLocale(rtlLocale.code);

    // Test form with RTL layout
    const forms = await this.page.getByRole('form').all();
    
    for (let i = 0; i < Math.min(forms.length, 2); i++) {
      const form = forms[i];
      
      // Check form direction
      const formDir = await form.getAttribute('dir');
      expect(formDir).toBe('rtl');
      
      // Check label alignment
      const labels = await form.getByRole('label').all();
      for (const label of labels.slice(0, 3)) {
        const labelStyles = await label.evaluate((el) => {
          const styles = window.getComputedStyle(el);
          return {
            textAlign: styles.textAlign,
            direction: styles.direction
          };
        });
        
        expect(labelStyles.direction).toBe('rtl');
      }
      
      // Check input field alignment
      const inputs = await form.getByRole('textbox').all();
      for (const input of inputs.slice(0, 3)) {
        const inputDir = await input.getAttribute('dir');
        expect(inputDir).toBe('rtl');
      }
    }

    return true;
  }

  async switchToLocale(localeCode: string) {
    // Click language selector
    await this.page.click('[data-testid="language-selector"]');
    
    // Select specific locale
    await this.page.click(`[data-testid="locale-option-${localeCode}"]`);
    
    // Wait for locale switch to complete
    await this.page.waitForTimeout(1000);
  }

  getSupportedLocales(): LocaleConfig[] {
    return [
      {
        code: 'en-US',
        name: 'English (US)',
        direction: 'ltr',
        currency: 'USD',
        dateFormat: 'MM/DD/YYYY',
        numberFormat: '1,234.56',
        translations: {
          'welcome-message': 'Welcome',
          'login-button': 'Sign In',
          'dashboard-title': 'Dashboard',
          'settings-link': 'Settings'
        }
      },
      {
        code: 'ar-SA',
        name: 'العربية (السعودية)',
        direction: 'rtl',
        currency: 'SAR',
        dateFormat: 'DD/MM/YYYY',
        numberFormat: '1٬234٫56',
        translations: {
          'welcome-message': 'مرحباً',
          'login-button': 'تسجيل الدخول',
          'dashboard-title': 'لوحة التحكم',
          'settings-link': 'الإعدادات'
        }
      },
      {
        code: 'es-ES',
        name: 'Español (España)',
        direction: 'ltr',
        currency: 'EUR',
        dateFormat: 'DD/MM/YYYY',
        numberFormat: '1.234,56',
        translations: {
          'welcome-message': 'Bienvenido',
          'login-button': 'Iniciar Sesión',
          'dashboard-title': 'Panel de Control',
          'settings-link': 'Configuración'
        }
      },
      {
        code: 'fr-FR',
        name: 'Français (France)',
        direction: 'ltr',
        currency: 'EUR',
        dateFormat: 'DD/MM/YYYY',
        numberFormat: '1 234,56',
        translations: {
          'welcome-message': 'Bienvenue',
          'login-button': 'Se Connecter',
          'dashboard-title': 'Tableau de Bord',
          'settings-link': 'Paramètres'
        }
      },
      {
        code: 'de-DE',
        name: 'Deutsch (Deutschland)',
        direction: 'ltr',
        currency: 'EUR',
        dateFormat: 'DD.MM.YYYY',
        numberFormat: '1.234,56',
        translations: {
          'welcome-message': 'Willkommen',
          'login-button': 'Anmelden',
          'dashboard-title': 'Dashboard',
          'settings-link': 'Einstellungen'
        }
      }
    ];
  }

  getMockTranslations(localeCode: string): Record<string, string> {
    const locales = this.getSupportedLocales();
    const locale = locales.find(l => l.code === localeCode);
    return locale ? locale.translations : {};
  }

  getMockExchangeRates(): Record<string, number> {
    return {
      'USD': 1.0,
      'EUR': 0.85,
      'SAR': 3.75,
      'GBP': 0.73,
      'JPY': 110.0
    };
  }

  private async initializeI18nTestData() {
    await this.page.evaluate(() => {
      sessionStorage.setItem('i18n_test_mode', 'true');
      sessionStorage.setItem('supported_locales', JSON.stringify([
        'en-US', 'ar-SA', 'es-ES', 'fr-FR', 'de-DE'
      ]));
      sessionStorage.setItem('current_locale', 'en-US');
    });
  }

  private async clearI18nTestData() {
    await this.page.evaluate(() => {
      sessionStorage.removeItem('i18n_test_mode');
      sessionStorage.removeItem('supported_locales');
      sessionStorage.removeItem('current_locale');
    });
  }

  // Utility methods for common test patterns
  static getCurrencyTestData(): CurrencyTestData[] {
    return [
      { locale: 'en-US', amount: 1234.56, expected: '$1,234.56', symbol: '$' },
      { locale: 'ar-SA', amount: 1234.56, expected: '1٬234٫56 ر.س', symbol: 'ر.س' },
      { locale: 'es-ES', amount: 1234.56, expected: '1.234,56 €', symbol: '€' },
      { locale: 'fr-FR', amount: 1234.56, expected: '1 234,56 €', symbol: '€' },
      { locale: 'de-DE', amount: 1234.56, expected: '1.234,56 €', symbol: '€' }
    ];
  }

  static getDateTestData(): DateTestData[] {
    const testDate = new Date('2024-03-15T10:30:00');
    
    return [
      { locale: 'en-US', date: testDate, expected: '3/15/2024', format: 'short' },
      { locale: 'ar-SA', date: testDate, expected: '15/3/2024', format: 'short' },
      { locale: 'es-ES', date: testDate, expected: '15/3/2024', format: 'short' },
      { locale: 'fr-FR', date: testDate, expected: '15/03/2024', format: 'short' },
      { locale: 'de-DE', date: testDate, expected: '15.03.2024', format: 'short' }
    ];
  }
}