import { test, expect } from '@playwright/test';

test.describe('Commissions Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login and navigate to commissions
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'channel-manager@dotmac.com');
    await page.fill('[data-testid="password-input"]', 'test-password-123');
    await page.click('[data-testid="login-button"]');
    await expect(page).toHaveURL('/dashboard');
    
    await page.goto('/commissions');
    await expect(page.locator('[data-testid="commissions-page"]')).toBeVisible();
  });

  test('should display commissions list', async ({ page }) => {
    // Check for commissions table
    await expect(page.locator('[data-testid="commissions-table"]')).toBeVisible();
    
    // Check for table headers
    await expect(page.locator('th:has-text("Payment #")')).toBeVisible();
    await expect(page.locator('th:has-text("Partner")')).toBeVisible();
    await expect(page.locator('th:has-text("Period")')).toBeVisible();
    await expect(page.locator('th:has-text("Amount")')).toBeVisible();
    await expect(page.locator('th:has-text("Status")')).toBeVisible();
    
    // Check for at least one commission row
    await expect(page.locator('[data-testid="commission-row"]').first()).toBeVisible();
  });

  test('should filter commissions by status', async ({ page }) => {
    // Click status filter
    await page.click('[data-testid="status-filter"]');
    await page.click('[data-testid="status-calculated"]');
    
    await page.waitForLoadState('networkidle');
    
    // All visible commissions should be calculated
    const statusBadges = page.locator('[data-testid="commission-status"]');
    const count = await statusBadges.count();
    
    for (let i = 0; i < count; i++) {
      await expect(statusBadges.nth(i)).toContainText('CALCULATED');
    }
  });

  test('should filter commissions by date range', async ({ page }) => {
    // Open date range picker
    await page.click('[data-testid="date-range-filter"]');
    
    // Select last month
    await page.click('[data-testid="last-month"]');
    
    await page.waitForLoadState('networkidle');
    
    // Should have filtered results
    const commissionRows = page.locator('[data-testid="commission-row"]');
    await expect(commissionRows).toHaveCountGreaterThan(0);
  });

  test('should view commission details', async ({ page }) => {
    // Click on first commission
    await page.click('[data-testid="commission-row"]');
    
    // Should navigate to commission detail
    await expect(page).toHaveURL(/\/commissions\/[^\/]+$/);
    
    // Check detail elements
    await expect(page.locator('[data-testid="commission-details"]')).toBeVisible();
    await expect(page.locator('[data-testid="commission-partner-info"]')).toBeVisible();
    await expect(page.locator('[data-testid="commission-period-info"]')).toBeVisible();
    await expect(page.locator('[data-testid="commission-amount-breakdown"]')).toBeVisible();
  });

  test('should approve single commission', async ({ page }) => {
    // Find a calculated commission
    const calculatedCommission = page.locator('[data-testid="commission-row"]:has([data-testid="commission-status"]:has-text("CALCULATED"))').first();
    
    if (await calculatedCommission.count() > 0) {
      await calculatedCommission.click();
      
      // Click approve button
      await page.click('[data-testid="approve-commission-button"]');
      
      // Add approval notes if required
      if (await page.locator('[data-testid="approval-notes"]').isVisible()) {
        await page.fill('[data-testid="approval-notes"]', 'Approved for payment');
        await page.click('[data-testid="confirm-approval"]');
      }
      
      // Should show success message
      await expect(page.locator('text=Commission approved successfully')).toBeVisible();
      
      // Status should update
      await expect(page.locator('[data-testid="commission-status"]')).toContainText('APPROVED');
    }
  });

  test('should bulk approve commissions', async ({ page }) => {
    // Select multiple calculated commissions
    const checkboxes = page.locator('[data-testid="commission-checkbox"]');
    const firstThree = checkboxes.first().locator('..', { hasText: 'CALCULATED' }).locator('[data-testid="commission-checkbox"]').first();
    
    if (await firstThree.count() > 0) {
      // Select commissions
      await firstThree.check();
      
      // More commissions if available
      const secondCheckbox = checkboxes.nth(1);
      if (await secondCheckbox.isVisible()) {
        await secondCheckbox.check();
      }
      
      // Click bulk approve
      await page.click('[data-testid="bulk-approve-button"]');
      
      // Confirm bulk approval
      await page.fill('[data-testid="bulk-approval-notes"]', 'Bulk approved for Q1');
      await page.click('[data-testid="confirm-bulk-approval"]');
      
      // Should show success message
      await expect(page.locator('text=Commissions approved successfully')).toBeVisible();
    }
  });

  test('should process approved commission', async ({ page }) => {
    // Find an approved commission
    const approvedCommission = page.locator('[data-testid="commission-row"]:has([data-testid="commission-status"]:has-text("APPROVED"))').first();
    
    if (await approvedCommission.count() > 0) {
      await approvedCommission.click();
      
      // Click process payment button
      await page.click('[data-testid="process-payment-button"]');
      
      // Confirm processing
      await page.click('[data-testid="confirm-processing"]');
      
      // Should show success message
      await expect(page.locator('text=Commission processed successfully')).toBeVisible();
      
      // Status should update
      await expect(page.locator('[data-testid="commission-status"]')).toContainText('PAID');
    }
  });

  test('should dispute commission', async ({ page }) => {
    // Find a commission to dispute
    const commissionRow = page.locator('[data-testid="commission-row"]').first();
    await commissionRow.click();
    
    // Click dispute button
    await page.click('[data-testid="dispute-commission-button"]');
    
    // Fill dispute reason
    await page.fill('[data-testid="dispute-reason"]', 'Sales data discrepancy - customer refunded');
    
    // Submit dispute
    await page.click('[data-testid="submit-dispute"]');
    
    // Should show success message
    await expect(page.locator('text=Commission dispute submitted')).toBeVisible();
    
    // Status should update
    await expect(page.locator('[data-testid="commission-status"]')).toContainText('DISPUTED');
  });

  test('should view commission summary', async ({ page }) => {
    // Click on summary tab or button
    await page.click('[data-testid="commission-summary-tab"]');
    
    // Check summary elements
    await expect(page.locator('[data-testid="total-commissions"]')).toBeVisible();
    await expect(page.locator('[data-testid="pending-amount"]')).toBeVisible();
    await expect(page.locator('[data-testid="paid-amount"]')).toBeVisible();
    await expect(page.locator('[data-testid="commission-chart"]')).toBeVisible();
  });

  test('should search commissions by partner', async ({ page }) => {
    // Use search functionality
    const searchTerm = 'Tech Solutions';
    await page.fill('[data-testid="commissions-search"]', searchTerm);
    await page.press('[data-testid="commissions-search"]', 'Enter');
    
    await page.waitForLoadState('networkidle');
    
    // Results should contain the search term
    const partnerNames = page.locator('[data-testid="commission-partner-name"]');
    const count = await partnerNames.count();
    
    if (count > 0) {
      for (let i = 0; i < count; i++) {
        const text = await partnerNames.nth(i).textContent();
        expect(text?.toLowerCase()).toContain(searchTerm.toLowerCase());
      }
    }
  });

  test('should export commissions data', async ({ page }) => {
    // Click export button
    const downloadPromise = page.waitForEvent('download');
    await page.click('[data-testid="export-commissions-button"]');
    
    // Wait for download
    const download = await downloadPromise;
    
    // Check download properties
    expect(download.suggestedFilename()).toMatch(/commissions.*\.csv$/);
    
    // Verify download
    const path = await download.path();
    expect(path).toBeTruthy();
  });

  test('should handle commission amount formatting', async ({ page }) => {
    // Check that amounts are properly formatted
    const amountCells = page.locator('[data-testid="commission-amount"]');
    const count = await amountCells.count();
    
    for (let i = 0; i < count; i++) {
      const text = await amountCells.nth(i).textContent();
      // Should be formatted as currency
      expect(text).toMatch(/^\$[\d,]+(\.\d{2})?$/);
    }
  });

  test('should show commission calculation details', async ({ page }) => {
    // Click on first commission
    await page.click('[data-testid="commission-row"]');
    
    // Check calculation breakdown
    await expect(page.locator('[data-testid="gross-amount"]')).toBeVisible();
    await expect(page.locator('[data-testid="deductions-list"]')).toBeVisible();
    await expect(page.locator('[data-testid="net-amount"]')).toBeVisible();
    
    // Check deduction details
    const deductions = page.locator('[data-testid="deduction-item"]');
    const deductionCount = await deductions.count();
    
    if (deductionCount > 0) {
      // Each deduction should have type, description, and amount
      await expect(deductions.first().locator('[data-testid="deduction-type"]')).toBeVisible();
      await expect(deductions.first().locator('[data-testid="deduction-description"]')).toBeVisible();
      await expect(deductions.first().locator('[data-testid="deduction-amount"]')).toBeVisible();
    }
  });
});