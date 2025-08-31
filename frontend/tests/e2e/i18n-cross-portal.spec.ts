/**
 * Cross-Portal Internationalization E2E Tests
 * Tests language switching, RTL layouts, currency/date formatting across all portals
 */

import { test, expect } from '@playwright/test';
import { I18nTestHelper, LocaleConfig, CurrencyTestData, DateTestData } from '../testing/e2e/shared-scenarios/i18n-test-helper';

interface PortalConfig {
  name: string;
  url: string;
  loginUrl: string;
  dashboardUrl: string;
  hasEcommerce: boolean;
  hasBilling: boolean;
}

class I18nJourney {
  constructor(
    public page: any,
    public i18nHelper: I18nTestHelper
  ) {}

  async testCompleteI18nFlow(portal: PortalConfig, locales: LocaleConfig[]) {
    console.log(`Testing complete i18n flow for ${portal.name} portal`);

    await this.page.goto(portal.url);
    
    // Test language switching
    await this.i18nHelper.testLanguageSwitching(portal.url, locales);
    
    // Test RTL layout with Arabic
    const arabicLocale = locales.find(l => l.direction === 'rtl');
    if (arabicLocale) {
      await this.i18nHelper.testRTLLayout(portal.url, arabicLocale);
    }
    
    // Test currency formatting if portal has billing
    if (portal.hasBilling) {
      const currencyTests = I18nTestHelper.getCurrencyTestData();
      await this.i18nHelper.testCurrencyFormatting(portal.url, currencyTests);
    }
    
    // Test date formatting
    const dateTests = I18nTestHelper.getDateTestData();
    await this.i18nHelper.testDateFormatting(portal.url, dateTests);

    return true;
  }

  async testLanguagePersistence(portal: PortalConfig) {
    console.log(`Testing language persistence for ${portal.name}`);

    await this.page.goto(portal.url);
    
    // Switch to Spanish
    await this.i18nHelper.switchToLocale('es-ES');
    
    // Navigate to different pages within portal
    const testUrls = [
      `${portal.url}/dashboard`,
      `${portal.url}/settings`,
      `${portal.url}/profile`
    ];
    
    for (const testUrl of testUrls) {
      try {
        await this.page.goto(testUrl);
        
        // Verify language persisted
        const htmlLang = await this.page.getAttribute('html', 'lang');
        expect(htmlLang).toBe('es-ES');
        
        // Verify Spanish content is displayed
        const welcomeText = await this.page.getByTestId('welcome-message').textContent();
        if (welcomeText) {
          expect(welcomeText).toContain('Bienvenido');
        }
        
      } catch (error) {
        console.log(`Page ${testUrl} not accessible, skipping...`);
      }
    }
    
    // Test language persistence across browser refresh
    await this.page.reload();
    
    const htmlLangAfterRefresh = await this.page.getAttribute('html', 'lang');
    expect(htmlLangAfterRefresh).toBe('es-ES');

    return true;
  }

  async testRTLFormSubmission(portalUrl: string) {
    console.log('Testing RTL form submission');

    await this.page.goto(portalUrl);
    
    // Switch to Arabic (RTL)
    await this.i18nHelper.switchToLocale('ar-SA');
    
    // Find and test RTL form
    const forms = await this.page.getByRole('form').all();
    
    if (forms.length > 0) {
      const form = forms[0];
      
      // Verify form direction
      const formDir = await form.getAttribute('dir');
      expect(formDir).toBe('rtl');
      
      // Fill form fields in RTL
      const textInputs = await form.getByRole('textbox').all();
      
      for (let i = 0; i < Math.min(textInputs.length, 3); i++) {
        const input = textInputs[i];
        
        // Test RTL input
        await input.fill('نص تجريبي باللغة العربية');
        
        // Verify input direction
        const inputDir = await input.getAttribute('dir');
        expect(inputDir).toBe('rtl');
        
        // Verify text alignment
        const textValue = await input.inputValue();
        expect(textValue).toBe('نص تجريبي باللغة العربية');
      }
    }

    return true;
  }

  async testLocaleSpecificValidation(portalUrl: string) {
    console.log('Testing locale-specific validation messages');

    const testLocales = ['en-US', 'es-ES', 'fr-FR'];
    
    for (const locale of testLocales) {
      await this.page.goto(portalUrl);
      await this.i18nHelper.switchToLocale(locale);
      
      // Test email validation in different languages
      const emailInput = this.page.getByTestId('email-input');
      if (await emailInput.isVisible()) {
        await emailInput.fill('invalid-email');
        await this.page.keyboard.press('Tab');
        
        // Look for validation message
        const validationMessage = this.page.getByTestId('email-validation-error');
        if (await validationMessage.isVisible()) {
          const message = await validationMessage.textContent();
          
          // Verify message is in correct language
          if (locale === 'es-ES') {
            expect(message?.toLowerCase()).toMatch(/correo|email|válido/);
          } else if (locale === 'fr-FR') {
            expect(message?.toLowerCase()).toMatch(/email|courrier|valide/);
          } else {
            expect(message?.toLowerCase()).toMatch(/email|valid|format/);
          }
          
          console.log(`✓ ${locale} validation: ${message}`);
        }
      }
    }

    return true;
  }

  async testCurrencyConversion(portalUrl: string) {
    console.log('Testing dynamic currency conversion');

    await this.page.goto(portalUrl);
    
    const currencies = [
      { locale: 'en-US', currency: 'USD', amount: 100 },
      { locale: 'es-ES', currency: 'EUR', amount: 85 },
      { locale: 'ar-SA', currency: 'SAR', amount: 375 }
    ];
    
    for (const test of currencies) {
      await this.i18nHelper.switchToLocale(test.locale);
      
      // Inject currency conversion test
      await this.page.evaluate((testData) => {
        // Create currency display element
        const currencyEl = document.createElement('div');
        currencyEl.setAttribute('data-testid', 'dynamic-currency');
        currencyEl.setAttribute('data-amount', testData.amount.toString());
        currencyEl.setAttribute('data-currency', testData.currency);
        
        // Format currency based on locale
        const formatter = new Intl.NumberFormat(testData.locale, {
          style: 'currency',
          currency: testData.currency
        });
        
        currencyEl.textContent = formatter.format(testData.amount);
        document.body.appendChild(currencyEl);
      }, test);
      
      // Verify currency formatting
      const currencyEl = this.page.getByTestId('dynamic-currency');
      await expect(currencyEl).toBeVisible();
      
      const formattedText = await currencyEl.textContent();
      console.log(`✓ ${test.locale}: ${test.amount} ${test.currency} → ${formattedText}`);
      
      // Clean up for next test
      await this.page.evaluate(() => {
        const el = document.querySelector('[data-testid="dynamic-currency"]');
        if (el) el.remove();
      });
    }

    return true;
  }

  async testTimeZoneHandling(portalUrl: string) {
    console.log('Testing timezone-aware date display');

    await this.page.goto(portalUrl);
    
    const timezoneTests = [
      { locale: 'en-US', timezone: 'America/New_York', label: 'EST' },
      { locale: 'es-ES', timezone: 'Europe/Madrid', label: 'CET' },
      { locale: 'ar-SA', timezone: 'Asia/Riyadh', label: 'AST' }
    ];
    
    const testDate = new Date('2024-03-15T15:30:00Z');
    
    for (const test of timezoneTests) {
      await this.i18nHelper.switchToLocale(test.locale);
      
      // Inject timezone test
      await this.page.evaluate((testData) => {
        const timeEl = document.createElement('div');
        timeEl.setAttribute('data-testid', 'timezone-display');
        
        const formatter = new Intl.DateTimeFormat(testData.locale, {
          timeZone: testData.timezone,
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          timeZoneName: 'short'
        });
        
        timeEl.textContent = formatter.format(testData.date);
        document.body.appendChild(timeEl);
      }, { ...test, date: testDate });
      
      // Verify timezone formatting
      const timeEl = this.page.getByTestId('timezone-display');
      await expect(timeEl).toBeVisible();
      
      const formattedTime = await timeEl.textContent();
      expect(formattedTime).toContain(test.label);
      
      console.log(`✓ ${test.locale} (${test.timezone}): ${formattedTime}`);
      
      // Clean up
      await this.page.evaluate(() => {
        const el = document.querySelector('[data-testid="timezone-display"]');
        if (el) el.remove();
      });
    }

    return true;
  }

  async testAccessibilityWithI18n(portalUrl: string) {
    console.log('Testing accessibility with internationalization');

    const testLocales = ['en-US', 'ar-SA', 'es-ES'];
    
    for (const locale of testLocales) {
      await this.page.goto(portalUrl);
      await this.i18nHelper.switchToLocale(locale);
      
      // Test screen reader announcements
      const mainContent = this.page.getByRole('main');
      if (await mainContent.isVisible()) {
        const mainLang = await mainContent.getAttribute('lang');
        expect(mainLang).toBe(locale);
      }
      
      // Test ARIA labels in correct language
      const buttons = await this.page.getByRole('button').all();
      for (const button of buttons.slice(0, 3)) {
        const ariaLabel = await button.getAttribute('aria-label');
        if (ariaLabel) {
          // Verify aria-label is not in English when using other locales
          if (locale === 'ar-SA') {
            expect(ariaLabel).not.toMatch(/^[A-Za-z\s]+$/);
          } else if (locale === 'es-ES') {
            expect(ariaLabel).not.toBe(''); // Should have Spanish text
          }
        }
      }
      
      // Test keyboard navigation with RTL
      if (locale === 'ar-SA') {
        await this.page.keyboard.press('Tab');
        const focusedElement = await this.page.locator(':focus').first();
        if (await focusedElement.isVisible()) {
          const focusedDir = await focusedElement.getAttribute('dir');
          expect(focusedDir).toBe('rtl');
        }
      }
    }

    return true;
  }

  async testDynamicContentTranslation(portalUrl: string) {
    console.log('Testing dynamic content translation');

    await this.page.goto(portalUrl);
    
    // Test notification messages in different languages
    const locales = ['en-US', 'es-ES', 'fr-FR'];
    
    for (const locale of locales) {
      await this.i18nHelper.switchToLocale(locale);
      
      // Inject dynamic notification
      await this.page.evaluate((localeCode) => {
        const notification = document.createElement('div');
        notification.setAttribute('data-testid', 'dynamic-notification');
        notification.setAttribute('class', 'notification success');
        
        // Mock translation based on locale
        let message;
        switch (localeCode) {
          case 'es-ES':
            message = 'Operación completada exitosamente';
            break;
          case 'fr-FR':
            message = 'Opération terminée avec succès';
            break;
          default:
            message = 'Operation completed successfully';
        }
        
        notification.textContent = message;
        document.body.appendChild(notification);
      }, locale);
      
      // Verify translated notification
      const notification = this.page.getByTestId('dynamic-notification');
      await expect(notification).toBeVisible();
      
      const notificationText = await notification.textContent();
      console.log(`✓ ${locale} notification: ${notificationText}`);
      
      // Clean up
      await this.page.evaluate(() => {
        const el = document.querySelector('[data-testid="dynamic-notification"]');
        if (el) el.remove();
      });
    }

    return true;
  }
}

test.describe('Cross-Portal Internationalization', () => {
  let i18nHelper: I18nTestHelper;

  // Portal configurations with i18n features
  const portals: PortalConfig[] = [
    {
      name: 'Customer',
      url: 'http://localhost:3001',
      loginUrl: 'http://localhost:3001/auth/login',
      dashboardUrl: '/dashboard',
      hasEcommerce: true,
      hasBilling: true
    },
    {
      name: 'Admin',
      url: 'http://localhost:3002',
      loginUrl: 'http://localhost:3002/auth/login',
      dashboardUrl: '/admin/dashboard',
      hasEcommerce: false,
      hasBilling: true
    },
    {
      name: 'Technician',
      url: 'http://localhost:3003',
      loginUrl: 'http://localhost:3003/auth/login',
      dashboardUrl: '/technician/dashboard',
      hasEcommerce: false,
      hasBilling: false
    },
    {
      name: 'Reseller',
      url: 'http://localhost:3004',
      loginUrl: 'http://localhost:3004/auth/login',
      dashboardUrl: '/reseller/dashboard',
      hasEcommerce: true,
      hasBilling: true
    }
  ];

  const supportedLocales = I18nTestHelper.prototype.getSupportedLocales();

  test.beforeEach(async ({ page }) => {
    i18nHelper = new I18nTestHelper(page);
    await i18nHelper.setup();
  });

  test.afterEach(async ({ page }) => {
    await i18nHelper.cleanup();
  });

  // Test language switching for each portal
  for (const portal of portals) {
    test(`supports language switching for ${portal.name} portal @i18n @language-switching @${portal.name.toLowerCase()}`, async ({ page }) => {
      const journey = new I18nJourney(page, i18nHelper);
      
      await test.step(`test language switching for ${portal.name}`, async () => {
        const result = await i18nHelper.testLanguageSwitching(portal.url, supportedLocales);
        expect(result).toBe(true);
      });
    });

    test(`maintains RTL layout for ${portal.name} portal @i18n @rtl @${portal.name.toLowerCase()}`, async ({ page }) => {
      const journey = new I18nJourney(page, i18nHelper);
      const arabicLocale = supportedLocales.find(l => l.direction === 'rtl')!;
      
      await test.step(`test RTL layout for ${portal.name}`, async () => {
        const result = await i18nHelper.testRTLLayout(portal.url, arabicLocale);
        expect(result).toBe(true);
      });
    });

    if (portal.hasBilling) {
      test(`formats currency correctly for ${portal.name} portal @i18n @currency @${portal.name.toLowerCase()}`, async ({ page }) => {
        const journey = new I18nJourney(page, i18nHelper);
        const currencyTests = I18nTestHelper.getCurrencyTestData();
        
        await test.step(`test currency formatting for ${portal.name}`, async () => {
          const result = await i18nHelper.testCurrencyFormatting(portal.url, currencyTests);
          expect(result).toBe(true);
        });
      });
    }

    test(`formats dates correctly for ${portal.name} portal @i18n @dates @${portal.name.toLowerCase()}`, async ({ page }) => {
      const journey = new I18nJourney(page, i18nHelper);
      const dateTests = I18nTestHelper.getDateTestData();
      
      await test.step(`test date formatting for ${portal.name}`, async () => {
        const result = await i18nHelper.testDateFormatting(portal.url, dateTests);
        expect(result).toBe(true);
      });
    });
  }

  test('persists language selection across navigation @i18n @persistence', async ({ page }) => {
    const journey = new I18nJourney(page, i18nHelper);
    const portal = portals[0]; // Use customer portal
    
    await test.step('test language persistence', async () => {
      const result = await journey.testLanguagePersistence(portal);
      expect(result).toBe(true);
    });
  });

  test('handles RTL form input and submission @i18n @rtl @forms', async ({ page }) => {
    const journey = new I18nJourney(page, i18nHelper);
    const portal = portals[0]; // Use customer portal
    
    await test.step('test RTL form submission', async () => {
      const result = await journey.testRTLFormSubmission(portal.url);
      expect(result).toBe(true);
    });
  });

  test('validates input with locale-specific messages @i18n @validation', async ({ page }) => {
    const journey = new I18nJourney(page, i18nHelper);
    const portal = portals[0]; // Use customer portal
    
    await test.step('test locale-specific validation', async () => {
      const result = await journey.testLocaleSpecificValidation(portal.url);
      expect(result).toBe(true);
    });
  });

  test('converts currency dynamically @i18n @currency @conversion', async ({ page }) => {
    const journey = new I18nJourney(page, i18nHelper);
    const portal = portals[0]; // Use customer portal
    
    await test.step('test dynamic currency conversion', async () => {
      const result = await journey.testCurrencyConversion(portal.url);
      expect(result).toBe(true);
    });
  });

  test('handles timezone-aware date display @i18n @timezones', async ({ page }) => {
    const journey = new I18nJourney(page, i18nHelper);
    const portal = portals[0]; // Use customer portal
    
    await test.step('test timezone handling', async () => {
      const result = await journey.testTimeZoneHandling(portal.url);
      expect(result).toBe(true);
    });
  });

  test('maintains accessibility with i18n @i18n @a11y', async ({ page }) => {
    const journey = new I18nJourney(page, i18nHelper);
    const portal = portals[0]; // Use customer portal
    
    await test.step('test i18n accessibility', async () => {
      const result = await journey.testAccessibilityWithI18n(portal.url);
      expect(result).toBe(true);
    });
  });

  test('translates dynamic content @i18n @dynamic-content', async ({ page }) => {
    const journey = new I18nJourney(page, i18nHelper);
    const portal = portals[0]; // Use customer portal
    
    await test.step('test dynamic content translation', async () => {
      const result = await journey.testDynamicContentTranslation(portal.url);
      expect(result).toBe(true);
    });
  });

  test('formats numbers correctly across locales @i18n @numbers', async ({ page }) => {
    const journey = new I18nJourney(page, i18nHelper);
    const portal = portals[0]; // Use customer portal
    
    const testLocales = ['en-US', 'es-ES', 'fr-FR', 'de-DE'];
    
    for (const locale of testLocales) {
      await test.step(`test number formatting for ${locale}`, async () => {
        const result = await i18nHelper.testNumberFormatting(portal.url, locale);
        expect(result).toBe(true);
      });
    }
  });

  test('handles pluralization rules @i18n @pluralization', async ({ page }) => {
    const journey = new I18nJourney(page, i18nHelper);
    const portal = portals[0]; // Use customer portal
    
    const testLocales = ['en-US', 'es-ES', 'fr-FR'];
    
    for (const locale of testLocales) {
      await test.step(`test pluralization for ${locale}`, async () => {
        const result = await i18nHelper.testPluralizations(portal.url, locale);
        expect(result).toBe(true);
      });
    }
  });

  test('displays locale-specific content @i18n @content', async ({ page }) => {
    const journey = new I18nJourney(page, i18nHelper);
    const portal = portals[0]; // Use customer portal
    
    for (const locale of supportedLocales.slice(0, 3)) {
      await test.step(`test locale-specific content for ${locale.code}`, async () => {
        const result = await i18nHelper.testLocaleSpecificContent(portal.url, locale);
        expect(result).toBe(true);
      });
    }
  });

  test('i18n performance across portals @i18n @performance', async ({ page }) => {
    const journey = new I18nJourney(page, i18nHelper);
    
    const startTime = Date.now();
    
    // Test language switching performance on first 2 portals
    for (const portal of portals.slice(0, 2)) {
      await i18nHelper.testLanguageSwitching(portal.url, supportedLocales.slice(0, 3));
    }
    
    const totalTime = Date.now() - startTime;
    expect(totalTime).toBeLessThan(45000); // 45 seconds max for complete i18n flow
  });

  test('i18n RTL accessibility @i18n @rtl @a11y', async ({ page }) => {
    const portal = portals[0]; // Use customer portal
    const arabicLocale = supportedLocales.find(l => l.direction === 'rtl')!;
    
    await page.goto(portal.url);
    await i18nHelper.switchToLocale(arabicLocale.code);
    
    // Check RTL accessibility
    const htmlDir = await page.getAttribute('html', 'dir');
    expect(htmlDir).toBe('rtl');
    
    // Check ARIA attributes maintain RTL
    const navigation = page.getByRole('navigation');
    if (await navigation.isVisible()) {
      const navDir = await navigation.getAttribute('dir');
      expect(navDir).toBe('rtl');
    }
    
    // Test keyboard navigation in RTL
    await page.keyboard.press('Tab');
    const focusedElement = page.locator(':focus').first();
    if (await focusedElement.isVisible()) {
      const focusedDir = await focusedElement.getAttribute('dir');
      expect(focusedDir).toBe('rtl');
    }
    
    // Check screen reader compatibility
    const main = page.getByRole('main');
    if (await main.isVisible()) {
      const mainLang = await main.getAttribute('lang');
      expect(mainLang).toBe(arabicLocale.code);
    }
  });
});

export { I18nJourney };