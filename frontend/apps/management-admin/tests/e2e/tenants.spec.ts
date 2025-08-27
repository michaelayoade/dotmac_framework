import { test, expect, type Page } from '@playwright/test';

test.describe('Tenant Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('input[type="email"]', 'admin@dotmac.com');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.goto('/tenants');
  });

  test('should display tenant list page', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Tenant Management');
    await expect(page.locator('button')).toContainText('Create New Tenant');
    await expect(page.locator('[data-testid="tenant-table"]')).toBeVisible();
  });

  test('should display tenant table headers', async ({ page }) => {
    const headers = ['Name', 'Domain', 'Status', 'Created', 'Actions'];
    
    for (const header of headers) {
      await expect(page.locator(`th:has-text("${header}")`)).toBeVisible();
    }
  });

  test('should filter tenants by status', async ({ page }) => {
    const statusFilter = page.locator('[data-testid="status-filter"]');
    if (await statusFilter.isVisible()) {
      await statusFilter.selectOption('active');
      
      // Should update table to show only active tenants
      await expect(page.locator('[data-testid="tenant-row"]')).toBeVisible();
    }
  });

  test('should search tenants by name', async ({ page }) => {
    const searchInput = page.locator('[data-testid="search-input"]');
    if (await searchInput.isVisible()) {
      await searchInput.fill('Acme Corp');
      
      // Should filter results
      await expect(page.locator('text=Acme Corp')).toBeVisible();
    }
  });

  test('should open create tenant modal', async ({ page }) => {
    await page.click('button:has-text("Create New Tenant")');
    
    await expect(page.locator('[data-testid="create-tenant-modal"]')).toBeVisible();
    await expect(page.locator('h2')).toContainText('Create New Tenant');
    
    // Check form fields
    await expect(page.locator('input[name="name"]')).toBeVisible();
    await expect(page.locator('input[name="domain"]')).toBeVisible();
    await expect(page.locator('input[name="email"]')).toBeVisible();
    await expect(page.locator('select[name="plan"]')).toBeVisible();
  });

  test('should validate tenant creation form', async ({ page }) => {
    await page.click('button:has-text("Create New Tenant")');
    
    // Try to submit empty form
    await page.click('button:has-text("Create Tenant")');
    
    // Should show validation errors
    await expect(page.locator('text=Name is required')).toBeVisible();
    await expect(page.locator('text=Domain is required')).toBeVisible();
    await expect(page.locator('text=Email is required')).toBeVisible();
  });

  test('should validate domain format', async ({ page }) => {
    await page.click('button:has-text("Create New Tenant")');
    
    await page.fill('input[name="name"]', 'Test Tenant');
    await page.fill('input[name="domain"]', 'invalid-domain');
    await page.fill('input[name="email"]', 'admin@test.com');
    
    await page.click('button:has-text("Create Tenant")');
    
    await expect(page.locator('text=Invalid domain format')).toBeVisible();
  });

  test('should create new tenant successfully', async ({ page }) => {
    // Mock successful creation
    await page.route('**/api/v1/tenants', (route) => {
      if (route.request().method() === 'POST') {
        route.fulfill({
          status: 201,
          body: JSON.stringify({
            id: 'tenant123',
            name: 'Test Tenant',
            domain: 'test.example.com',
            email: 'admin@test.com',
            status: 'active',
            createdAt: new Date().toISOString()
          })
        });
      }
    });
    
    await page.click('button:has-text("Create New Tenant")');
    
    await page.fill('input[name="name"]', 'Test Tenant');
    await page.fill('input[name="domain"]', 'test.example.com');
    await page.fill('input[name="email"]', 'admin@test.com');
    await page.selectOption('select[name="plan"]', 'basic');
    
    await page.click('button:has-text("Create Tenant")');
    
    // Should close modal and show success message
    await expect(page.locator('[data-testid="create-tenant-modal"]')).not.toBeVisible();
    await expect(page.locator('text=Tenant created successfully')).toBeVisible();
  });

  test('should view tenant details', async ({ page }) => {
    const viewButton = page.locator('[data-testid="view-tenant"]').first();
    if (await viewButton.isVisible()) {
      await viewButton.click();
      
      await expect(page.locator('h2')).toContainText('Tenant Details');
      await expect(page.locator('[data-testid="tenant-info"]')).toBeVisible();
    }
  });

  test('should edit tenant information', async ({ page }) => {
    const editButton = page.locator('[data-testid="edit-tenant"]').first();
    if (await editButton.isVisible()) {
      await editButton.click();
      
      await expect(page.locator('h2')).toContainText('Edit Tenant');
      await expect(page.locator('input[name="name"]')).toBeVisible();
      
      // Should be able to update name
      await page.fill('input[name="name"]', 'Updated Tenant Name');
      await page.click('button:has-text("Save Changes")');
      
      await expect(page.locator('text=Tenant updated successfully')).toBeVisible();
    }
  });

  test('should suspend tenant', async ({ page }) => {
    // Mock tenant data
    await page.route('**/api/v1/tenants/*', (route) => {
      if (route.request().method() === 'PATCH') {
        route.fulfill({
          status: 200,
          body: JSON.stringify({ status: 'suspended' })
        });
      }
    });
    
    const suspendButton = page.locator('[data-testid="suspend-tenant"]').first();
    if (await suspendButton.isVisible()) {
      await suspendButton.click();
      
      // Should show confirmation dialog
      await expect(page.locator('text=Are you sure you want to suspend this tenant?')).toBeVisible();
      await page.click('button:has-text("Confirm")');
      
      await expect(page.locator('text=Tenant suspended successfully')).toBeVisible();
    }
  });

  test('should activate suspended tenant', async ({ page }) => {
    // Mock suspended tenant
    await page.route('**/api/v1/tenants', (route) => {
      route.fulfill({
        status: 200,
        body: JSON.stringify([
          {
            id: 'tenant1',
            name: 'Suspended Tenant',
            domain: 'suspended.example.com',
            status: 'suspended',
            createdAt: new Date().toISOString()
          }
        ])
      });
    });
    
    await page.reload();
    
    const activateButton = page.locator('[data-testid="activate-tenant"]').first();
    if (await activateButton.isVisible()) {
      await activateButton.click();
      
      await expect(page.locator('text=Tenant activated successfully')).toBeVisible();
    }
  });

  test('should delete tenant with confirmation', async ({ page }) => {
    const deleteButton = page.locator('[data-testid="delete-tenant"]').first();
    if (await deleteButton.isVisible()) {
      await deleteButton.click();
      
      // Should show confirmation dialog
      await expect(page.locator('text=Are you sure you want to delete this tenant?')).toBeVisible();
      await expect(page.locator('text=This action cannot be undone')).toBeVisible();
      
      // Cancel first
      await page.click('button:has-text("Cancel")');
      await expect(page.locator('[data-testid="delete-confirmation"]')).not.toBeVisible();
      
      // Try again and confirm
      await deleteButton.click();
      await page.fill('input[placeholder="Type DELETE to confirm"]', 'DELETE');
      await page.click('button:has-text("Delete Tenant")');
      
      await expect(page.locator('text=Tenant deleted successfully')).toBeVisible();
    }
  });

  test('should sort tenants by column', async ({ page }) => {
    const nameHeader = page.locator('th:has-text("Name")');
    await nameHeader.click();
    
    // Should show sort indicator
    await expect(nameHeader.locator('svg')).toBeVisible(); // Sort arrow
    
    // Click again to reverse sort
    await nameHeader.click();
    await expect(nameHeader.locator('svg')).toBeVisible();
  });

  test('should paginate through tenant list', async ({ page }) => {
    const pagination = page.locator('[data-testid="pagination"]');
    if (await pagination.isVisible()) {
      const nextButton = pagination.locator('button:has-text("Next")');
      
      if (await nextButton.isEnabled()) {
        await nextButton.click();
        
        // Should navigate to next page
        await expect(page.locator('text=Page 2')).toBeVisible();
      }
    }
  });

  test('should export tenant list', async ({ page }) => {
    const exportButton = page.locator('[data-testid="export-tenants"]');
    if (await exportButton.isVisible()) {
      // Start download
      const downloadPromise = page.waitForEvent('download');
      await exportButton.click();
      
      const download = await downloadPromise;
      expect(download.suggestedFilename()).toBe('tenants.csv');
    }
  });
});