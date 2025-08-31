import { Page, expect } from '@playwright/test';

export interface LocaleConfig {
  code: string; // e.g., 'en-US'
  direction: 'ltr' | 'rtl';
}

export interface CurrencyTestData {
  locale: string;
  currency: string;
  amount: number;
}

export interface DateTestData {
  locale: string;
  date: string; // ISO date string
}

export class I18nTestHelper {
  constructor(private page: Page) {}

  static getCurrencyTestData(): CurrencyTestData[] {
    return [
      { locale: 'en-US', currency: 'USD', amount: 1234.56 },
      { locale: 'es-ES', currency: 'EUR', amount: 1234.56 },
      { locale: 'fr-FR', currency: 'EUR', amount: 1234.56 },
      { locale: 'de-DE', currency: 'EUR', amount: 1234.56 },
      { locale: 'ar-SA', currency: 'SAR', amount: 1234.56 },
    ];
  }

  static getDateTestData(): DateTestData[] {
    return [
      { locale: 'en-US', date: '2025-01-15T10:30:00Z' },
      { locale: 'es-ES', date: '2025-01-15T10:30:00Z' },
      { locale: 'fr-FR', date: '2025-01-15T10:30:00Z' },
      { locale: 'de-DE', date: '2025-01-15T10:30:00Z' },
      { locale: 'ar-SA', date: '2025-01-15T10:30:00Z' },
    ];
  }

  async testLanguageSwitching(baseUrl: string, locales: LocaleConfig[]) {
    await this.page.goto(baseUrl);
    for (const loc of locales) {
      await this.switchToLocale(loc.code);
      const langAttr = await this.page.getAttribute('html', 'lang');
      expect(langAttr).toBe(loc.code);
      const dirAttr = await this.page.getAttribute('html', 'dir');
      expect(dirAttr).toBe(loc.direction);
    }
  }

  async testRTLLayout(baseUrl: string, locale: LocaleConfig) {
    await this.page.goto(baseUrl);
    await this.switchToLocale(locale.code);
    const dirAttr = await this.page.getAttribute('html', 'dir');
    expect(dirAttr).toBe('rtl');
  }

  async testCurrencyFormatting(baseUrl: string, data: CurrencyTestData[]) {
    await this.page.goto(baseUrl);
    for (const t of data) {
      await this.switchToLocale(t.locale);
      const result = await this.page.evaluate((d) => new Intl.NumberFormat(d.locale, { style: 'currency', currency: d.currency }).format(d.amount), t);
      expect(result).toBeTruthy();
    }
  }

  async testDateFormatting(baseUrl: string, data: DateTestData[]) {
    await this.page.goto(baseUrl);
    for (const t of data) {
      await this.switchToLocale(t.locale);
      const result = await this.page.evaluate((d) => new Intl.DateTimeFormat(d.locale, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(d.date)), t);
      expect(result).toBeTruthy();
    }
  }

  async switchToLocale(locale: string) {
    await this.page.evaluate((l) => {
      document.documentElement.lang = l;
      document.documentElement.dir = l === 'ar-SA' ? 'rtl' : 'ltr';
    }, locale);
  }
}

