import { Page } from '@playwright/test';

export class MailHogHelper {
  constructor(
    private page: Page,
    private baseUrl = 'http://localhost:8025'
  ) {}

  async fetchLatestEmail(toContains: string): Promise<{ subject: string; body: string } | null> {
    try {
      const res = await this.page.request.get(`${this.baseUrl}/api/v2/messages`);
      if (!res.ok()) return null;
      const data = await res.json();
      const items = (data?.items || []) as any[];
      const msg = items.find((i) =>
        (i?.Content?.Headers?.To || []).some((t: string) => t.includes(toContains))
      );
      if (!msg) return null;
      const subject = (msg?.Content?.Headers?.Subject || [''])[0] as string;
      const body = msg?.Content?.Body || '';
      return { subject, body };
    } catch {
      return null;
    }
  }

  extractFirstLink(htmlOrText: string): string | null {
    const m = htmlOrText.match(/https?:\/\/[^\s"']+/);
    return m ? m[0] : null;
  }

  async openLinkInPage(link: string) {
    await this.page.goto(link);
  }
}
