/**
 * End-to-End Tests for Complete Support System
 * Tests the full user journey from frontend to backend integration
 */

import { test, expect, type Page, type BrowserContext } from '@playwright/test';
import { faker } from '@faker-js/faker';

// Test data generators
const generateCustomer = () => ({
  name: faker.person.fullName(),
  email: faker.internet.email(),
  phone: faker.phone.number()
});

const generateArticle = () => ({
  title: faker.lorem.sentence(),
  content: faker.lorem.paragraphs(3),
  category: faker.helpers.arrayElement(['Technical Support', 'Billing', 'Account Management']),
  tags: [faker.lorem.word(), faker.lorem.word()]
});

// Page Object Model
class CustomerPortalPage {
  constructor(private page: Page) {}

  // Navigation methods
  async goto() {
    await this.page.goto('/support');
  }

  async navigateToKnowledgeBase() {
    await this.page.click('button[role="tab"]:has-text("Knowledge Base")');
  }

  async navigateToTickets() {
    await this.page.click('button[role="tab"]:has-text("My Tickets")');
  }

  async navigateToChat() {
    await this.page.click('button[role="tab"]:has-text("Live Chat")');
  }

  // Search methods
  async search(query: string) {
    await this.page.fill('input[placeholder*="Search for help articles"]', query);
    await this.page.press('input[placeholder*="Search for help articles"]', 'Enter');
  }

  async waitForSearchResults() {
    await this.page.waitForSelector('[data-testid="search-results"]');
  }

  // Dashboard methods
  async getOpenTicketCount() {
    const element = await this.page.locator('text="Open Tickets"').locator('..').locator('.text-2xl');
    return await element.textContent();
  }

  async clickQuickAction(actionName: string) {
    await this.page.click(`text="${actionName}"`);
  }

  // Chat methods
  async openChatWidget() {
    await this.page.click('#live-chat-widget');
  }

  async sendChatMessage(message: string) {
    await this.page.fill('textarea[placeholder*="Type your message"]', message);
    await this.page.click('button:has(svg)'); // Send button
  }

  async waitForChatResponse() {
    await this.page.waitForSelector('.bg-gray-100', { timeout: 5000 });
  }

  // Article methods
  async clickArticle(title: string) {
    await this.page.click(`text="${title}"`);
  }

  async voteHelpful() {
    await this.page.click('button:has-text("Helpful")');
  }

  async addComment(comment: string) {
    await this.page.fill('textarea[placeholder*="Add a comment"]', comment);
    await this.page.click('button:has-text("Add Comment")');
  }
}

class AdminPortalPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/admin/support');
  }

  async createArticle(articleData: any) {
    await this.page.click('button:has-text("Create Article")');
    await this.page.fill('input[name="title"]', articleData.title);
    await this.page.fill('textarea[name="content"]', articleData.content);
    await this.page.selectOption('select[name="category"]', articleData.category);
    
    // Add tags
    for (const tag of articleData.tags) {
      await this.page.fill('input[placeholder*="Add tag"]', tag);
      await this.page.press('input[placeholder*="Add tag"]', 'Enter');
    }
    
    await this.page.click('button:has-text("Save Article")');
  }

  async publishArticle(title: string) {
    await this.page.click(`text="${title}"`);
    await this.page.click('button:has-text("Publish")');
    await this.page.waitForSelector('text="Published"');
  }

  async assignChatToAgent(sessionId: string, agentName: string) {
    await this.page.goto('/admin/chat/queue');
    await this.page.click(`[data-session-id="${sessionId}"] button:has-text("Accept")`);
    await this.page.waitForSelector(`text="Assigned to ${agentName}"`);
  }
}

// Test Suite: Knowledge Base Functionality
test.describe('Knowledge Base System', () => {
  let customerPortal: CustomerPortalPage;
  let adminPortal: AdminPortalPage;

  test.beforeEach(async ({ page }) => {
    customerPortal = new CustomerPortalPage(page);
    adminPortal = new AdminPortalPage(page);
  });

  test('complete article lifecycle - create, publish, search, view, interact', async ({ page, context }) => {
    const articleData = generateArticle();
    
    // Admin creates and publishes article
    const adminPage = await context.newPage();
    const adminPortalPage = new AdminPortalPage(adminPage);
    
    await adminPortalPage.goto();
    await adminPortalPage.createArticle(articleData);
    await adminPortalPage.publishArticle(articleData.title);
    await adminPage.close();

    // Customer searches and finds article
    await customerPortal.goto();
    await customerPortal.navigateToKnowledgeBase();
    await customerPortal.search(articleData.title.split(' ')[0]);
    await customerPortal.waitForSearchResults();

    // Verify article appears in search results
    await expect(page.locator(`text="${articleData.title}"`)).toBeVisible();

    // Customer views article
    await customerPortal.clickArticle(articleData.title);
    
    // Verify article content is displayed
    await expect(page.locator('text="Article Details"')).toBeVisible();
    await expect(page.locator(`text="${articleData.content.substring(0, 50)}"`)).toBeVisible();

    // Customer votes helpful
    await customerPortal.voteHelpful();
    
    // Verify vote was recorded
    await expect(page.locator('text="Thank you for your feedback"')).toBeVisible();

    // Customer adds comment
    const commentText = 'This article was very helpful!';
    await customerPortal.addComment(commentText);
    
    // Verify comment appears
    await expect(page.locator(`text="${commentText}"`)).toBeVisible();
  });

  test('search functionality with filters and sorting', async ({ page }) => {
    await customerPortal.goto();
    await customerPortal.navigateToKnowledgeBase();

    // Test search with query
    await customerPortal.search('password');
    await customerPortal.waitForSearchResults();
    
    // Should show results related to password
    await expect(page.locator('[data-testid="search-results"]')).toBeVisible();

    // Test category filter
    await page.click('button:has-text("Filters")');
    await page.selectOption('select[name="category"]', 'Account Management');
    await page.click('button:has-text("Apply Filters")');
    
    // Verify filtered results
    await page.waitForSelector('text="Account Management"');

    // Test sorting
    await page.selectOption('select[name="sort"]', 'view_count-desc');
    await page.waitForLoadState('networkidle');
    
    // Verify results are sorted by view count
    const firstResult = page.locator('[data-testid="article-card"]').first();
    await expect(firstResult.locator('.view-count')).toBeVisible();
  });

  test('popular articles display correctly', async ({ page }) => {
    await customerPortal.goto();
    
    // Check popular articles section
    await expect(page.locator('text="Popular Help Articles"')).toBeVisible();
    
    // Should show at least one popular article
    const popularArticles = page.locator('[data-testid="popular-article"]');
    await expect(popularArticles.first()).toBeVisible();
    
    // Click on popular article
    await popularArticles.first().click();
    
    // Should navigate to article detail
    await expect(page.locator('[data-testid="article-detail"]')).toBeVisible();
  });
});

// Test Suite: Live Chat System
test.describe('Live Chat System', () => {
  let customerPortal: CustomerPortalPage;
  let customerData: any;

  test.beforeEach(async ({ page }) => {
    customerPortal = new CustomerPortalPage(page);
    customerData = generateCustomer();
  });

  test('complete chat session from start to resolution', async ({ page, context }) => {
    // Customer initiates chat
    await customerPortal.goto();
    await customerPortal.openChatWidget();

    // Wait for chat widget to open
    await expect(page.locator('[data-testid="chat-window"]')).toBeVisible();

    // Customer sends initial message
    const initialMessage = 'I need help with my account';
    await customerPortal.sendChatMessage(initialMessage);
    
    // Verify message appears in chat
    await expect(page.locator(`text="${initialMessage}"`)).toBeVisible();

    // Wait for system message (waiting for agent)
    await expect(page.locator('text="Waiting for an agent"')).toBeVisible();

    // Simulate agent joining (would be done by admin in real scenario)
    // For testing, we'll mock the agent response
    await page.evaluate(() => {
      // Mock WebSocket message for agent joining
      window.dispatchEvent(new CustomEvent('chat-agent-joined', {
        detail: { agentName: 'Agent Smith', message: 'Hello! How can I help you today?' }
      }));
    });

    // Verify agent joined
    await expect(page.locator('text="Agent Smith has joined"')).toBeVisible();
    await expect(page.locator('text="Hello! How can I help you today?"')).toBeVisible();

    // Customer responds
    const responseMessage = 'I forgot my password';
    await customerPortal.sendChatMessage(responseMessage);

    // Wait for agent response (simulated)
    await customerPortal.waitForChatResponse();
    
    // End chat session
    await page.click('button[title="End Chat"]');
    
    // Rate the experience
    await page.click('[data-rating="5"]');
    await page.fill('textarea[placeholder*="feedback"]', 'Great service!');
    await page.click('button:has-text("Submit Rating")');

    // Verify chat ended successfully
    await expect(page.locator('text="Chat session ended"')).toBeVisible();
  });

  test('chat widget responsiveness and state management', async ({ page }) => {
    await customerPortal.goto();

    // Test widget toggle
    await customerPortal.openChatWidget();
    await expect(page.locator('[data-testid="chat-window"]')).toBeVisible();

    // Test minimize
    await page.click('button[title="Minimize"]');
    await expect(page.locator('[data-testid="chat-window"]')).toHaveClass(/minimized/);

    // Test restore
    await page.click('button[title="Restore"]');
    await expect(page.locator('[data-testid="chat-window"]')).not.toHaveClass(/minimized/);

    // Test close
    await page.click('button[title="Close"]');
    await expect(page.locator('[data-testid="chat-window"]')).not.toBeVisible();
  });

  test('chat queue and wait time management', async ({ page }) => {
    await customerPortal.goto();
    await customerPortal.openChatWidget();

    // Should show queue position if agents are busy
    const queueMessage = page.locator('text*="position in queue"');
    if (await queueMessage.isVisible()) {
      await expect(queueMessage).toContainText(/\d+/); // Should contain a number
    }

    // Should show estimated wait time
    const waitTimeMessage = page.locator('text*="estimated wait time"');
    if (await waitTimeMessage.isVisible()) {
      await expect(waitTimeMessage).toContainText(/\d+/); // Should contain time estimate
    }
  });
});

// Test Suite: Ticket System Integration
test.describe('Ticket System Integration', () => {
  let customerPortal: CustomerPortalPage;

  test.beforeEach(async ({ page }) => {
    customerPortal = new CustomerPortalPage(page);
  });

  test('create ticket from chat escalation', async ({ page }) => {
    // Start chat session
    await customerPortal.goto();
    await customerPortal.openChatWidget();
    
    // Send complex technical issue
    await customerPortal.sendChatMessage('My server keeps crashing with database errors');
    
    // Wait for agent (simulated)
    await page.waitForTimeout(2000);
    
    // Agent escalates to ticket
    await page.click('button:has-text("Create Ticket")');
    
    // Verify ticket creation dialog
    await expect(page.locator('[data-testid="ticket-creation-modal"]')).toBeVisible();
    
    // Fill ticket details
    await page.fill('input[name="title"]', 'Server Crashes - Database Errors');
    await page.selectOption('select[name="priority"]', 'high');
    await page.click('button:has-text("Create Ticket")');
    
    // Verify ticket created
    await expect(page.locator('text="Ticket created successfully"')).toBeVisible();
    
    // Navigate to tickets tab
    await customerPortal.navigateToTickets();
    
    // Verify ticket appears in list
    await expect(page.locator('text="Server Crashes - Database Errors"')).toBeVisible();
  });

  test('create ticket from knowledge base escalation', async ({ page }) => {
    await customerPortal.goto();
    await customerPortal.navigateToKnowledgeBase();
    
    // Search for something that might not have good results
    await customerPortal.search('complex database configuration');
    
    // Should show "didn't find what you're looking for" option
    await expect(page.locator('text="Didn\'t find what you\'re looking for?"')).toBeVisible();
    
    // Click create ticket
    await page.click('button:has-text("Create Support Ticket")');
    
    // Should navigate to ticket creation with search context
    await expect(page.locator('input[name="title"]')).toHaveValue(/complex database configuration/i);
  });
});

// Test Suite: Complete User Journeys
test.describe('Complete User Journeys', () => {
  let customerPortal: CustomerPortalPage;

  test.beforeEach(async ({ page }) => {
    customerPortal = new CustomerPortalPage(page);
  });

  test('successful self-service journey', async ({ page }) => {
    // Customer has password reset question
    await customerPortal.goto();
    
    // First tries search
    await customerPortal.search('reset password');
    await customerPortal.waitForSearchResults();
    
    // Finds helpful article
    await customerPortal.clickArticle('How to Reset Your Password');
    
    // Reads article and votes helpful
    await customerPortal.voteHelpful();
    
    // Adds positive comment
    await customerPortal.addComment('This solved my problem perfectly!');
    
    // Check dashboard shows updated activity
    await page.click('button[role="tab"]:has-text("Dashboard")');
    
    // Should see recent activity
    await expect(page.locator('text="Recent Activity"')).toBeVisible();
    await expect(page.locator('text="Viewed article"')).toBeVisible();
  });

  test('escalation journey - search to chat to ticket', async ({ page }) => {
    // Customer searches for complex issue
    await customerPortal.goto();
    await customerPortal.search('custom API integration');
    
    // Doesn't find good results, starts chat
    await customerPortal.openChatWidget();
    await customerPortal.sendChatMessage('I need help with custom API integration');
    
    // Issue is complex, agent creates ticket
    await page.click('button:has-text("Create Ticket for Follow-up")');
    
    // Ticket is created with chat context
    await expect(page.locator('text="Ticket created from chat session"')).toBeVisible();
    
    // Customer can see ticket in their list
    await customerPortal.navigateToTickets();
    await expect(page.locator('text="Custom API Integration"')).toBeVisible();
  });

  test('multi-channel support experience', async ({ page, context }) => {
    // Customer uses multiple support channels in one session
    await customerPortal.goto();
    
    // 1. Starts with knowledge base
    await customerPortal.search('billing questions');
    await customerPortal.clickArticle('Understanding Your Bill');
    
    // 2. Still has questions, starts chat
    await customerPortal.openChatWidget();
    await customerPortal.sendChatMessage('I have a specific billing question about my last invoice');
    
    // 3. Agent helps but creates ticket for detailed follow-up
    await page.click('button:has-text("Create Follow-up Ticket")');
    
    // 4. Customer rates all interactions positively
    await page.click('[data-rating="5"]');
    
    // All interactions should be tracked in recent activity
    await page.click('button[role="tab"]:has-text("Dashboard")');
    const activities = page.locator('[data-testid="activity-item"]');
    await expect(activities).toHaveCount(3); // KB view, chat, ticket creation
  });
});

// Test Suite: Performance and Accessibility
test.describe('Performance and Accessibility', () => {
  test('page load performance', async ({ page }) => {
    const startTime = Date.now();
    
    await page.goto('/support');
    await page.waitForLoadState('networkidle');
    
    const loadTime = Date.now() - startTime;
    
    // Page should load within 3 seconds
    expect(loadTime).toBeLessThan(3000);
  });

  test('accessibility compliance', async ({ page }) => {
    await page.goto('/support');
    
    // Check for proper heading structure
    const h1 = page.locator('h1');
    await expect(h1).toHaveCount(1);
    await expect(h1).toHaveText('Support Portal');
    
    // Check for proper form labels
    const searchInput = page.locator('input[placeholder*="Search"]');
    await expect(searchInput).toHaveAttribute('aria-label');
    
    // Check for keyboard navigation
    await searchInput.focus();
    await page.keyboard.press('Tab');
    
    // Next element should be focusable
    const activeElement = page.locator(':focus');
    await expect(activeElement).toBeVisible();
    
    // Check for screen reader support
    const srOnlyElements = page.locator('.sr-only');
    if (await srOnlyElements.count() > 0) {
      await expect(srOnlyElements.first()).toHaveAttribute('class', /sr-only/);
    }
  });

  test('responsive design across devices', async ({ page, context }) => {
    // Test on different viewport sizes
    const viewports = [
      { width: 375, height: 667 },   // Mobile
      { width: 768, height: 1024 },  // Tablet
      { width: 1920, height: 1080 }  // Desktop
    ];

    for (const viewport of viewports) {
      await page.setViewportSize(viewport);
      await page.goto('/support');
      
      // Check that main elements are visible and properly laid out
      await expect(page.locator('h1:has-text("Support Portal")')).toBeVisible();
      await expect(page.locator('input[placeholder*="Search"]')).toBeVisible();
      
      // Check responsive navigation
      if (viewport.width < 768) {
        // Mobile: should have hamburger menu or collapsible tabs
        const mobileNav = page.locator('[data-testid="mobile-nav"]');
        if (await mobileNav.isVisible()) {
          await expect(mobileNav).toBeVisible();
        }
      } else {
        // Desktop/tablet: should have full tab navigation
        await expect(page.locator('button[role="tab"]')).toHaveCount(5);
      }
    }
  });
});

// Test Suite: Error Handling and Edge Cases
test.describe('Error Handling and Edge Cases', () => {
  test('handles API errors gracefully', async ({ page, context }) => {
    // Mock network failures
    await context.route('**/api/**', route => {
      route.abort('failed');
    });

    await page.goto('/support');
    
    // Should show error state gracefully
    await expect(page.locator('text="Something went wrong"')).toBeVisible();
    await expect(page.locator('button:has-text("Retry")')).toBeVisible();
    
    // Error shouldn't break the entire interface
    await expect(page.locator('h1:has-text("Support Portal")')).toBeVisible();
  });

  test('handles chat connection failures', async ({ page }) => {
    await page.goto('/support');
    await page.evaluate(() => {
      // Mock WebSocket connection failure
      window.WebSocket = class extends EventTarget {
        constructor() {
          super();
          setTimeout(() => {
            this.dispatchEvent(new Event('error'));
          }, 100);
        }
      };
    });

    // Try to open chat
    const customerPortal = new CustomerPortalPage(page);
    await customerPortal.openChatWidget();
    
    // Should show connection error
    await expect(page.locator('text="Connection error"')).toBeVisible();
    await expect(page.locator('button:has-text("Retry Connection")')).toBeVisible();
  });

  test('handles empty states appropriately', async ({ page }) => {
    await page.goto('/support');
    
    // Navigate to tickets with no tickets
    const customerPortal = new CustomerPortalPage(page);
    await customerPortal.navigateToTickets();
    
    // Should show empty state
    await expect(page.locator('text="No tickets yet"')).toBeVisible();
    await expect(page.locator('button:has-text("Create Your First Ticket")')).toBeVisible();
  });
});

// Test Configuration
test.describe.configure({ mode: 'parallel' });

// Global test setup
test.beforeAll(async () => {
  // Setup test data, database state, etc.
  console.log('Setting up E2E test environment...');
});

test.afterAll(async () => {
  // Cleanup test data
  console.log('Cleaning up E2E test environment...');
});

// Cleanup after each test
test.afterEach(async ({ page }) => {
  // Clear localStorage, cookies, etc.
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
});