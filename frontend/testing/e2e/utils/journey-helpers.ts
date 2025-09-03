/**
 * Shared utilities for user journey testing
 * DRY helpers to eliminate code duplication
 */

export class JourneyHelper {
  constructor(public page: any) {}

  async waitForLoadingComplete() {
    // Wait for loading spinners to disappear
    await this.page.waitForSelector('[data-testid="loading-spinner"]', {
      state: 'hidden',
      timeout: 10000,
    });
  }

  async verifyPageTitle(expectedTitle: string) {
    await expect(this.page).toHaveTitle(new RegExp(expectedTitle, 'i'));
  }

  async takeScreenshotOnFailure(testName: string) {
    await this.page.screenshot({
      path: `test-results/${testName}-failure.png`,
      fullPage: true,
    });
  }

  async verifyApiResponse(endpoint: string, expectedStatus = 200) {
    const response = await this.page.waitForResponse(endpoint);
    expect(response.status()).toBe(expectedStatus);
    return response;
  }

  async fillFormField(testId: string, value: string) {
    await this.page.fill(`[data-testid="${testId}"]`, value);
    // Verify the value was set
    expect(await this.page.inputValue(`[data-testid="${testId}"]`)).toBe(value);
  }

  async selectOption(testId: string, value: string) {
    await this.page.selectOption(`[data-testid="${testId}"]`, value);
  }

  async uploadFile(testId: string, filePath: string) {
    await this.page.setInputFiles(`[data-testid="${testId}"]`, filePath);
  }

  async verifyNotification(message: string, type: 'success' | 'error' | 'warning' = 'success') {
    const notification = this.page.getByTestId(`notification-${type}`);
    await expect(notification).toBeVisible();
    await expect(notification).toContainText(message);
  }
}

export class NetworkHelper {
  constructor(public page: any) {}

  async mockApiCall(endpoint: string, response: any) {
    await this.page.route(endpoint, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(response),
      });
    });
  }

  async simulateSlowNetwork() {
    // Simulate slow 3G
    const client = await this.page.context().newCDPSession(this.page);
    await client.send('Network.enable');
    await client.send('Network.emulateNetworkConditions', {
      offline: false,
      downloadThroughput: (1.5 * 1024 * 1024) / 8, // 1.5 Mbps
      uploadThroughput: (750 * 1024) / 8, // 750 Kbps
      latency: 300, // 300ms
    });
  }

  async simulateOffline() {
    await this.page.context().setOffline(true);
  }

  async restoreNetwork() {
    await this.page.context().setOffline(false);
  }
}

export const testData = {
  customer: {
    validData: {
      email: 'test.customer@example.com',
      firstName: 'John',
      lastName: 'Doe',
      phone: '555-0123',
      address: '123 Test St',
      city: 'Test City',
      zipCode: '12345',
    },
    invalidData: {
      email: 'invalid-email',
      phone: '123',
      zipCode: 'invalid',
    },
  },
  service: {
    plans: [
      { name: 'Basic', speed: '25 Mbps', price: 39.99 },
      { name: 'Premium', speed: '100 Mbps', price: 59.99 },
      { name: 'Enterprise', speed: '1 Gbps', price: 99.99 },
    ],
  },
};
