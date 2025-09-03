/**
 * MailHog Helper - Utilities for E2E email testing with MailHog
 * Provides methods to interact with MailHog API for email verification in E2E tests
 */

import { expect } from '@playwright/test';

export interface EmailFilter {
  to?: string;
  from?: string;
  subject?: string | RegExp;
  timeout?: number;
  shouldExist?: boolean;
}

export interface EmailMessage {
  id: string;
  from: {
    email: string;
    name: string;
  };
  to: Array<{
    email: string;
    name: string;
  }>;
  subject: string;
  body: {
    text: string;
    html: string;
  };
  headers: Record<string, string[]>;
  timestamp: string;
  raw: string;
}

export class MailHogHelper {
  constructor(private mailHogUrl: string = 'http://localhost:8025') {}

  /**
   * Wait for an email matching the specified criteria
   */
  async waitForEmail(filter: EmailFilter): Promise<EmailMessage | null> {
    const timeout = filter.timeout || 30000;
    const startTime = Date.now();
    const checkInterval = 1000; // Check every second

    while (Date.now() - startTime < timeout) {
      const emails = await this.getAllEmails();

      for (const email of emails) {
        if (this.emailMatchesFilter(email, filter)) {
          return email;
        }
      }

      // Wait before next check
      await new Promise((resolve) => setTimeout(resolve, checkInterval));
    }

    if (filter.shouldExist !== false) {
      throw new Error(
        `Email matching filter not found within ${timeout}ms. Filter: ${JSON.stringify(filter)}`
      );
    }

    return null;
  }

  /**
   * Check if an email exists without waiting
   */
  async checkForEmail(filter: EmailFilter): Promise<boolean> {
    try {
      const email = await this.waitForEmail({
        ...filter,
        timeout: filter.timeout || 5000,
        shouldExist: false,
      });
      return email !== null;
    } catch {
      return false;
    }
  }

  /**
   * Get all emails from MailHog
   */
  async getAllEmails(): Promise<EmailMessage[]> {
    try {
      const response = await fetch(`${this.mailHogUrl}/api/v2/messages`);
      if (!response.ok) {
        throw new Error(`MailHog API error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      return data.items?.map(this.transformMailHogMessage) || [];
    } catch (error) {
      console.error('Error fetching emails from MailHog:', error);
      return [];
    }
  }

  /**
   * Get all emails for a specific recipient
   */
  async getAllEmailsForRecipient(email: string): Promise<EmailMessage[]> {
    const allEmails = await this.getAllEmails();
    return allEmails.filter((msg) =>
      msg.to.some((recipient) => recipient.email.toLowerCase() === email.toLowerCase())
    );
  }

  /**
   * Clear all emails from MailHog
   */
  async clearAllEmails(): Promise<void> {
    try {
      const response = await fetch(`${this.mailHogUrl}/api/v1/messages`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`Failed to clear MailHog emails: ${response.status}`);
      }

      console.log('Cleared all emails from MailHog');
    } catch (error) {
      console.error('Error clearing MailHog emails:', error);
    }
  }

  /**
   * Get a specific email by ID
   */
  async getEmailById(emailId: string): Promise<EmailMessage | null> {
    try {
      const response = await fetch(`${this.mailHogUrl}/api/v1/messages/${emailId}`);
      if (!response.ok) {
        return null;
      }

      const data = await response.json();
      return this.transformMailHogMessage(data);
    } catch (error) {
      console.error('Error fetching email by ID:', error);
      return null;
    }
  }

  /**
   * Extract password reset link from email content
   */
  extractResetLinkFromEmail(email: EmailMessage): string | null {
    const content = email.body.html || email.body.text;

    // Common patterns for reset links
    const patterns = [
      /https?:\/\/[^\s]+\/auth\/reset-password[^\s\)"]*/g,
      /https?:\/\/[^\s]+\/password\/reset[^\s\)"]*/g,
      /https?:\/\/[^\s]+\/reset[^\s\)"]*/g,
      /href="([^"]*reset-password[^"]*)/g,
      /href='([^']*reset-password[^']*)'/g,
    ];

    for (const pattern of patterns) {
      const matches = content.match(pattern);
      if (matches && matches.length > 0) {
        let link = matches[0];

        // Clean up href extraction
        if (link.startsWith('href="') || link.startsWith("href='")) {
          link = link.substring(6);
        }

        // Ensure it's a complete URL
        if (link.startsWith('http')) {
          return link;
        }
      }
    }

    // Fallback: look for any URL with 'token=' parameter
    const tokenPattern = /https?:\/\/[^\s]+\?[^\s]*token=[^\s\)"']*/g;
    const tokenMatches = content.match(tokenPattern);
    if (tokenMatches && tokenMatches.length > 0) {
      return tokenMatches[0];
    }

    return null;
  }

  /**
   * Extract verification link from email content (for email verification)
   */
  extractVerificationLinkFromEmail(email: EmailMessage): string | null {
    const content = email.body.html || email.body.text;

    const patterns = [
      /https?:\/\/[^\s]+\/auth\/verify-email[^\s\)"]*/g,
      /https?:\/\/[^\s]+\/verify[^\s\)"]*/g,
      /href="([^"]*verify[^"]*)/g,
    ];

    for (const pattern of patterns) {
      const matches = content.match(pattern);
      if (matches && matches.length > 0) {
        let link = matches[0];
        if (link.startsWith('href="')) {
          link = link.substring(6);
        }
        return link;
      }
    }

    return null;
  }

  /**
   * Extract OTP/verification code from email content
   */
  extractOTPFromEmail(email: EmailMessage): string | null {
    const content = email.body.text || email.body.html.replace(/<[^>]*>/g, '');

    // Common OTP patterns
    const patterns = [
      /verification code[:\s]*([A-Z0-9]{6,8})/i,
      /your code[:\s]*([A-Z0-9]{6,8})/i,
      /code[:\s]*([A-Z0-9]{6,8})/i,
      /\b([A-Z0-9]{6})\b/, // 6-digit alphanumeric
      /\b([0-9]{6})\b/, // 6-digit numeric
    ];

    for (const pattern of patterns) {
      const match = content.match(pattern);
      if (match && match[1]) {
        return match[1];
      }
    }

    return null;
  }

  /**
   * Verify email contains specific content
   */
  verifyEmailContent(email: EmailMessage, expectedContent: string | RegExp): boolean {
    const content = `${email.subject} ${email.body.text} ${email.body.html}`;

    if (typeof expectedContent === 'string') {
      return content.toLowerCase().includes(expectedContent.toLowerCase());
    } else {
      return expectedContent.test(content);
    }
  }

  /**
   * Get email statistics for testing
   */
  async getEmailStats(): Promise<{
    totalEmails: number;
    emailsByDomain: Record<string, number>;
    emailsBySubject: Record<string, number>;
    recentEmails: number; // Last hour
  }> {
    const emails = await this.getAllEmails();
    const now = Date.now();
    const oneHourAgo = now - 60 * 60 * 1000;

    const stats = {
      totalEmails: emails.length,
      emailsByDomain: {} as Record<string, number>,
      emailsBySubject: {} as Record<string, number>,
      recentEmails: 0,
    };

    for (const email of emails) {
      // Count by domain
      for (const recipient of email.to) {
        const domain = recipient.email.split('@')[1];
        stats.emailsByDomain[domain] = (stats.emailsByDomain[domain] || 0) + 1;
      }

      // Count by subject
      stats.emailsBySubject[email.subject] = (stats.emailsBySubject[email.subject] || 0) + 1;

      // Count recent emails
      if (new Date(email.timestamp).getTime() > oneHourAgo) {
        stats.recentEmails++;
      }
    }

    return stats;
  }

  /**
   * Wait for multiple emails matching criteria
   */
  async waitForMultipleEmails(
    filters: EmailFilter[],
    timeout: number = 30000
  ): Promise<EmailMessage[]> {
    const startTime = Date.now();
    const foundEmails: EmailMessage[] = [];

    while (Date.now() - startTime < timeout && foundEmails.length < filters.length) {
      const emails = await this.getAllEmails();

      for (const filter of filters) {
        if (foundEmails.some((found) => this.emailMatchesFilter(found, filter))) {
          continue; // Already found this one
        }

        const matchingEmail = emails.find((email) => this.emailMatchesFilter(email, filter));
        if (matchingEmail) {
          foundEmails.push(matchingEmail);
        }
      }

      if (foundEmails.length < filters.length) {
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
    }

    return foundEmails;
  }

  /**
   * Transform MailHog message format to our EmailMessage interface
   */
  private transformMailHogMessage(mailHogMsg: any): EmailMessage {
    return {
      id: mailHogMsg.ID,
      from: {
        email: mailHogMsg.From?.Mailbox + '@' + mailHogMsg.From?.Domain || '',
        name: mailHogMsg.From?.Name || '',
      },
      to: (mailHogMsg.To || []).map((to: any) => ({
        email: to.Mailbox + '@' + to.Domain,
        name: to.Name || '',
      })),
      subject: mailHogMsg.Content?.Headers?.Subject?.[0] || '',
      body: {
        text: mailHogMsg.Content?.Body || '',
        html: this.extractHtmlFromMimeBody(
          mailHogMsg.Content?.Body || '',
          mailHogMsg.Content?.Headers
        ),
      },
      headers: mailHogMsg.Content?.Headers || {},
      timestamp: mailHogMsg.Created,
      raw: JSON.stringify(mailHogMsg),
    };
  }

  /**
   * Extract HTML content from MIME body if present
   */
  private extractHtmlFromMimeBody(body: string, headers: any): string {
    const contentType = headers?.['Content-Type']?.[0] || '';

    if (contentType.includes('text/html')) {
      return body;
    }

    if (contentType.includes('multipart')) {
      // Look for HTML part in multipart message
      const htmlMatch = body.match(
        /Content-Type:\s*text\/html[\s\S]*?\r?\n\r?\n([\s\S]*?)(?=\r?\n--)/
      );
      if (htmlMatch) {
        return htmlMatch[1];
      }
    }

    return ''; // No HTML content found
  }

  /**
   * Check if email matches the given filter
   */
  private emailMatchesFilter(email: EmailMessage, filter: EmailFilter): boolean {
    if (
      filter.to &&
      !email.to.some((recipient) =>
        recipient.email.toLowerCase().includes(filter.to!.toLowerCase())
      )
    ) {
      return false;
    }

    if (filter.from && !email.from.email.toLowerCase().includes(filter.from.toLowerCase())) {
      return false;
    }

    if (filter.subject) {
      if (typeof filter.subject === 'string') {
        if (!email.subject.toLowerCase().includes(filter.subject.toLowerCase())) {
          return false;
        }
      } else {
        if (!filter.subject.test(email.subject)) {
          return false;
        }
      }
    }

    return true;
  }

  /**
   * Utility to validate MailHog is running and accessible
   */
  async validateMailHogConnection(): Promise<boolean> {
    try {
      const response = await fetch(`${this.mailHogUrl}/api/v2/messages`);
      return response.ok;
    } catch {
      return false;
    }
  }

  /**
   * Get MailHog configuration info
   */
  async getMailHogInfo(): Promise<any> {
    try {
      const response = await fetch(`${this.mailHogUrl}/api/v1/info`);
      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.error('Error getting MailHog info:', error);
    }
    return null;
  }
}
