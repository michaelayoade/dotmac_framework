import { test, expect } from '@playwright/test';

test.describe('Partners Management', () => {
  test.beforeEach(async ({ page }) => {
    // Use authenticated state
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'channel-manager@dotmac.com');
    await page.fill('[data-testid="password-input"]', 'test-password-123');
    await page.click('[data-testid="login-button"]');
    await expect(page).toHaveURL('/dashboard');

    // Navigate to partners page
    await page.goto('/partners');
    await expect(page.locator('[data-testid="partners-page"]')).toBeVisible();
  });

  test('should display partners list', async ({ page }) => {
    // Check for partners table
    await expect(page.locator('[data-testid="partners-table"]')).toBeVisible();

    // Check for table headers
    await expect(page.locator('th:has-text("Company")')).toBeVisible();
    await expect(page.locator('th:has-text("Contact")')).toBeVisible();
    await expect(page.locator('th:has-text("Type")')).toBeVisible();
    await expect(page.locator('th:has-text("Tier")')).toBeVisible();
    await expect(page.locator('th:has-text("Status")')).toBeVisible();

    // Check for at least one partner row
    await expect(page.locator('[data-testid="partner-row"]').first()).toBeVisible();
  });

  test('should filter partners by status', async ({ page }) => {
    // Click on status filter
    await page.click('[data-testid="status-filter"]');
    await page.click('[data-testid="status-active"]');

    // Wait for filtered results
    await page.waitForLoadState('networkidle');

    // All visible partners should be active
    const statusBadges = page.locator('[data-testid="partner-status"]');
    const count = await statusBadges.count();

    for (let i = 0; i < count; i++) {
      await expect(statusBadges.nth(i)).toContainText('ACTIVE');
    }
  });

  test('should filter partners by tier', async ({ page }) => {
    // Click on tier filter
    await page.click('[data-testid="tier-filter"]');
    await page.click('[data-testid="tier-gold"]');

    // Wait for filtered results
    await page.waitForLoadState('networkidle');

    // All visible partners should be gold tier
    const tierBadges = page.locator('[data-testid="partner-tier"]');
    const count = await tierBadges.count();

    for (let i = 0; i < count; i++) {
      await expect(tierBadges.nth(i)).toContainText('GOLD');
    }
  });

  test('should search partners by company name', async ({ page }) => {
    // Type in search box
    const searchTerm = 'Tech Solutions';
    await page.fill('[data-testid="partners-search"]', searchTerm);
    await page.press('[data-testid="partners-search"]', 'Enter');

    // Wait for search results
    await page.waitForLoadState('networkidle');

    // Results should contain the search term
    const companyNames = page.locator('[data-testid="partner-company-name"]');
    const count = await companyNames.count();

    for (let i = 0; i < count; i++) {
      const text = await companyNames.nth(i).textContent();
      expect(text?.toLowerCase()).toContain(searchTerm.toLowerCase());
    }
  });

  test('should view partner details', async ({ page }) => {
    // Click on first partner
    await page.click('[data-testid="partner-row"]', { timeout: 10000 });

    // Should navigate to partner detail page
    await expect(page).toHaveURL(/\/partners\/[^\/]+$/);

    // Check for partner detail elements
    await expect(page.locator('[data-testid="partner-details"]')).toBeVisible();
    await expect(page.locator('[data-testid="partner-info-company"]')).toBeVisible();
    await expect(page.locator('[data-testid="partner-info-contact"]')).toBeVisible();
    await expect(page.locator('[data-testid="partner-info-territory"]')).toBeVisible();
  });

  test('should create new partner', async ({ page }) => {
    // Click create partner button
    await page.click('[data-testid="create-partner-button"]');

    // Check for modal or form
    await expect(page.locator('[data-testid="create-partner-modal"]')).toBeVisible();

    // Fill in partner details
    await page.fill('[data-testid="company-name-input"]', 'Test Partner Inc');
    await page.fill('[data-testid="contact-name-input"]', 'John Doe');
    await page.fill('[data-testid="contact-email-input"]', 'john@testpartner.com');
    await page.fill('[data-testid="contact-phone-input"]', '+1234567890');

    // Select partner type
    await page.click('[data-testid="partner-type-select"]');
    await page.click('[data-testid="partner-type-agent"]');

    // Select tier
    await page.click('[data-testid="tier-select"]');
    await page.click('[data-testid="tier-silver"]');

    // Submit form
    await page.click('[data-testid="submit-partner-button"]');

    // Should show success message
    await expect(page.locator('text=Partner created successfully')).toBeVisible();

    // Modal should close
    await expect(page.locator('[data-testid="create-partner-modal"]')).not.toBeVisible();

    // New partner should appear in list
    await expect(page.locator('text=Test Partner Inc')).toBeVisible();
  });

  test('should approve pending partner', async ({ page }) => {
    // Find a pending partner
    const pendingPartner = page
      .locator(
        '[data-testid="partner-row"]:has([data-testid="partner-status"]:has-text("PENDING"))'
      )
      .first();

    if ((await pendingPartner.count()) > 0) {
      // Click on partner to view details
      await pendingPartner.click();

      // Click approve button
      await page.click('[data-testid="approve-partner-button"]');

      // Confirm approval if there's a confirmation dialog
      if (await page.locator('[data-testid="confirm-approval"]').isVisible()) {
        await page.click('[data-testid="confirm-approval"]');
      }

      // Should show success message
      await expect(page.locator('text=Partner approved successfully')).toBeVisible();

      // Status should update to ACTIVE
      await expect(page.locator('[data-testid="partner-status"]')).toContainText('ACTIVE');
    }
  });

  test('should update partner tier', async ({ page }) => {
    // Click on first partner
    await page.click('[data-testid="partner-row"]');

    // Click edit tier button
    await page.click('[data-testid="edit-tier-button"]');

    // Select new tier
    await page.click('[data-testid="tier-select"]');
    await page.click('[data-testid="tier-platinum"]');

    // Save changes
    await page.click('[data-testid="save-tier-button"]');

    // Should show success message
    await expect(page.locator('text=Partner tier updated successfully')).toBeVisible();

    // Tier should be updated
    await expect(page.locator('[data-testid="partner-tier"]')).toContainText('PLATINUM');
  });

  test('should suspend partner', async ({ page }) => {
    // Find an active partner
    const activePartner = page
      .locator('[data-testid="partner-row"]:has([data-testid="partner-status"]:has-text("ACTIVE"))')
      .first();

    if ((await activePartner.count()) > 0) {
      await activePartner.click();

      // Click suspend button
      await page.click('[data-testid="suspend-partner-button"]');

      // Fill in suspension reason
      await page.fill('[data-testid="suspension-reason"]', 'Performance issues');

      // Confirm suspension
      await page.click('[data-testid="confirm-suspension"]');

      // Should show success message
      await expect(page.locator('text=Partner suspended successfully')).toBeVisible();

      // Status should update to SUSPENDED
      await expect(page.locator('[data-testid="partner-status"]')).toContainText('SUSPENDED');
    }
  });

  test('should handle pagination', async ({ page }) => {
    // Check if pagination is visible (only if there are enough partners)
    const pagination = page.locator('[data-testid="pagination"]');

    if (await pagination.isVisible()) {
      // Get current page number
      const currentPage = await page.locator('[data-testid="current-page"]').textContent();

      // Click next page
      await page.click('[data-testid="next-page"]');

      // Wait for new data to load
      await page.waitForLoadState('networkidle');

      // Page number should have changed
      const newPage = await page.locator('[data-testid="current-page"]').textContent();
      expect(newPage).not.toBe(currentPage);
    }
  });

  test('should export partners data', async ({ page }) => {
    // Click export button
    const downloadPromise = page.waitForEvent('download');
    await page.click('[data-testid="export-partners-button"]');

    // Wait for download
    const download = await downloadPromise;

    // Check download properties
    expect(download.suggestedFilename()).toMatch(/partners.*\.csv$/);

    // Verify file was downloaded
    const path = await download.path();
    expect(path).toBeTruthy();
  });
});
