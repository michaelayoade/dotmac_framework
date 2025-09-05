import json
import logging
import os
from typing import Any, Optional
from urllib.parse import parse_qs

import aiohttp


class SMSProvider:
    def __init__(self):
        self.driver = os.getenv("SMS_DRIVER", "twilio")
        self.twilio_sid = os.getenv("TWILIO_SID")
        self.twilio_token = os.getenv("TWILIO_TOKEN")
        self.twilio_from = os.getenv("TWILIO_FROM_NUMBER")

    async def send(self, to: str, template: Optional[str] = None, vars: Optional[dict[str, Any]] = None, body: Optional[str] = None) -> str:
        """Send SMS via configured provider"""
        if vars is None:
            vars = {}
        if self.driver == "twilio":
            return await self._send_twilio(to, template, vars, body)
        if self.driver == "vonage":
            return await self._send_vonage(to, template, vars, body)
        raise ValueError(f"Unsupported SMS driver: {self.driver}")

    async def _send_twilio(self, to: str, template: Optional[str] = None, vars: Optional[dict[str, Any]] = None, body: Optional[str] = None) -> str:
        """Send via Twilio API"""
        if vars is None:
            vars = {}
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_sid}/Messages.json"

        message_body = body or self._load_template(template, vars)

        data = {"From": self.twilio_from, "To": to, "Body": message_body}

        auth = aiohttp.BasicAuth(self.twilio_sid, self.twilio_token)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, auth=auth) as response:
                result = await response.json()
                if response.status == 201:
                    return result["sid"]
                raise Exception(f"Twilio error: {result}")

    async def _send_vonage(self, to: str, template: Optional[str] = None, vars: Optional[dict[str, Any]] = None, body: Optional[str] = None) -> str:
        """Send via Vonage (Nexmo) API"""
        if vars is None:
            vars = {}
        url = "https://rest.nexmo.com/sms/json"

        message_body = body or self._load_template(template, vars)

        data = {
            "api_key": os.getenv("VONAGE_API_KEY"),
            "api_secret": os.getenv("VONAGE_API_SECRET"),
            "from": os.getenv("VONAGE_FROM_NUMBER", "DotMac"),
            "to": to,
            "text": message_body,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                result = await response.json()
                if result["messages"][0]["status"] == "0":
                    return result["messages"][0]["message-id"]
                raise Exception(f"Vonage error: {result}")

    def _load_template(self, template: str, vars: dict[str, Any]) -> str:
        """Load and render SMS template"""
        templates = {
            "welcome": f"Welcome {vars.get('name', 'there')}! Your DotMac account is now active.",
            "payment_due": f"Hi {vars.get('name', 'there')}, your payment of ${vars.get('amount', '0')} is due. Please pay to avoid service interruption.",
            "verification": f"Your verification code is: {vars.get('code', '000000')}",
            "alert": f"Alert: {vars.get('message', 'System notification')}",
        }

        return templates.get(template, f"Notification: {vars.get('message', 'You have a new update.')}")

    async def handle_webhook(self, raw_body: bytes) -> dict[str, Any]:
        """Handle inbound SMS webhooks (replies, delivery receipts)"""
        try:
            if self.driver == "twilio":
                return await self._handle_twilio_webhook(raw_body)
            if self.driver == "vonage":
                return await self._handle_vonage_webhook(raw_body)
        except Exception as e:
            logging.exception(f"Failed to process SMS webhook: {e}")
            return {"error": str(e)}

    async def _handle_twilio_webhook(self, raw_body: bytes) -> dict[str, Any]:
        """Handle Twilio SMS webhook"""
        # Twilio sends form-encoded data
        data = parse_qs(raw_body.decode())

        # Extract key fields
        result = {
            "from": data.get("From", [""])[0],
            "to": data.get("To", [""])[0],
            "body": data.get("Body", [""])[0],
            "message_sid": data.get("MessageSid", [""])[0],
            "provider": "twilio",
        }

        return result

    async def _handle_vonage_webhook(self, raw_body: bytes) -> dict[str, Any]:
        """Handle Vonage SMS webhook"""
        data = json.loads(raw_body.decode())

        result = {
            "from": data.get("msisdn"),
            "to": data.get("to"),
            "body": data.get("text"),
            "message_id": data.get("messageId"),
            "provider": "vonage",
        }

        return result
