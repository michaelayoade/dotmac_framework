import asyncio
import json
import logging
import os
from typing import Any, Optional

import aiohttp


class EmailProvider:
    def __init__(self):
        self.driver = os.getenv("EMAIL_DRIVER", "smtp2go")
        self.api_key = os.getenv("SMTP2GO_API_KEY") or os.getenv("SENDGRID_API_KEY")

    async def send(self, to: str, template: str, vars: Optional[dict[str, Any]] = None) -> str:
        """Send email via configured provider"""
        if vars is None:
            vars = {}
        if self.driver == "smtp2go":
            return await self._send_smtp2go(to, template, vars)
        if self.driver == "sendgrid":
            return await self._send_sendgrid(to, template, vars)
        raise ValueError(f"Unsupported email driver: {self.driver}")

    async def _send_smtp2go(self, to: str, template: str, vars: dict[str, Any]) -> str:
        """Send via SMTP2GO API"""
        url = "https://api.smtp2go.com/v3/email/send"

        # Load template content (simplified - you'd load from templates directory)
        subject, body = self._load_template(template, vars)

        payload = {
            "api_key": self.api_key,
            "to": [to],
            "sender": os.getenv("FROM_EMAIL", "noreply@yourdomain.com"),
            "subject": subject,
            "html_body": body,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                result = await response.json()
                if response.status == 200:
                    return result["data"]["email_id"]
                raise Exception(f"SMTP2GO error: {result}")

    async def _send_sendgrid(self, to: str, template: str, vars: dict[str, Any]) -> str:
        """Send via SendGrid API"""
        url = "https://api.sendgrid.com/v3/mail/send"

        subject, body = self._load_template(template, vars)

        payload = {
            "personalizations": [{"to": [{"email": to}]}],
            "from": {"email": os.getenv("FROM_EMAIL", "noreply@yourdomain.com")},
            "subject": subject,
            "content": [{"type": "text/html", "value": body}],
        }

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 202:
                    # SendGrid doesn't return message ID in response body
                    return f"sg_{int(asyncio.get_event_loop().time())}"
                error = await response.text()
                raise Exception(f"SendGrid error: {error}")

    def _load_template(self, template: str, vars: dict[str, Any]) -> tuple:
        """Load and render email template"""
        # Simplified template system - in production you'd use Jinja2 or similar
        templates = {
            "welcome": {
                "subject": "Welcome to DotMac!",
                "body": f"<h1>Welcome {vars.get('name', 'there')}!</h1><p>Your account is now active.</p>",
            },
            "payment_due": {
                "subject": "Payment Due Reminder",
                "body": f"<p>Hi {vars.get('name', 'there')}, your payment of ${vars.get('amount', '0')} is due.</p>",
            },
        }

        tmpl = templates.get(template, {"subject": "Notification", "body": "<p>You have a new notification.</p>"})

        return tmpl["subject"], tmpl["body"]

    async def handle_webhook(self, raw_body: bytes) -> dict[str, Any]:
        """Handle inbound email webhooks (bounces, opens, etc.)"""
        try:
            data = json.loads(raw_body.decode())
            # Process webhook data based on provider
            return {"processed": True, "events": data}
        except Exception as e:
            logging.exception(f"Failed to process email webhook: {e}")
            return {"error": str(e)}
