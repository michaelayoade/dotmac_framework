import json
import logging
import os
from typing import Any, Dict

import aiohttp


class WhatsAppProvider:
    def __init__(self):
        self.driver = os.getenv("WHATSAPP_DRIVER", "ultramsg")
        self.ultramsg_instance = os.getenv("ULTRAMSG_INSTANCE_ID")
        self.ultramsg_token = os.getenv("ULTRAMSG_TOKEN")

    async def send(self, to: str, template: str = None, vars: Dict[str, Any] = {}, body: str = None) -> str:
        """Send WhatsApp message via configured provider"""
        if self.driver == "ultramsg":
            return await self._send_ultramsg(to, template, vars, body)
        if self.driver == "infobip":
            return await self._send_infobip(to, template, vars, body)
        raise ValueError(f"Unsupported WhatsApp driver: {self.driver}")

    async def _send_ultramsg(self, to: str, template: str = None, vars: Dict[str, Any] = {}, body: str = None) -> str:
        """Send via UltraMsg API"""
        url = f"https://api.ultramsg.com/{self.ultramsg_instance}/messages/chat"

        message_body = body or self._load_template(template, vars)

        data = {
            "token": self.ultramsg_token,
            "to": to,  # format: +1234567890@c.us
            "body": message_body
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                result = await response.json()
                if result.get("sent"):
                    return result.get("id", "ultramsg_" + str(int(asyncio.get_event_loop().time())
                raise Exception(f"UltraMsg error: {result}")

    async def _send_infobip(self, to: str, template: str = None, vars: Dict[str, Any] = {}, body: str = None) -> str:
        """Send via Infobip API"""
        url = "https://api.infobip.com/whatsapp/1/message/text"

        message_body = body or self._load_template(template, vars)

        payload = {
            "from": os.getenv("INFOBIP_SENDER", "DotMac"),
            "to": to,
            "content": {
                "text": message_body
            }
        }

        headers = {
            "Authorization": f"App {os.getenv('INFOBIP_API_KEY')}",
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                result = await response.json()
                if response.status == 200:
                    return result["messages"][0]["messageId"]
                raise Exception(f"Infobip error: {result}")

    def _load_template(self, template: str, vars: Dict[str, Any]) -> str:
        """Load and render WhatsApp template"""
        templates = {
            "welcome": f"🎉 Welcome {vars.get('name', 'there')}!\n\nYour DotMac account is now active. We're excited to have you on board!",
            "payment_due": f"💰 Payment Reminder\n\nHi {vars.get('name', 'there')}, your payment of ${vars.get('amount', '0')} is due.\n\nPlease pay to avoid service interruption.",
            "verification": f"🔐 Verification Code\n\nYour verification code is: *{vars.get('code', '000000')}*\n\nDo not share this code with anyone.",
            "order_update": f"📦 Order Update\n\nHi {vars.get('name', 'there')}, your order #{vars.get('order_id', 'N/A')} is now {vars.get('status', 'processing')}.",
            "support": f"🆘 Support Message\n\n{vars.get('message', 'Our support team will get back to you shortly.')}"
        }

        return templates.get(template, f"📢 Notification\n\n{vars.get('message', 'You have a new update from DotMac.')}")

    async def handle_webhook(self, raw_body: bytes) -> Dict[str, Any]:
        """Handle inbound WhatsApp webhooks (replies, status updates)"""
        try:
            if self.driver == "ultramsg":
                return await self._handle_ultramsg_webhook(raw_body)
            if self.driver == "infobip":
                return await self._handle_infobip_webhook(raw_body)
        except Exception as e:
            logging.exception(f"Failed to process WhatsApp webhook: {e}")
            return {"error": str(e)}

    async def _handle_ultramsg_webhook(self, raw_body: bytes) -> Dict[str, Any]:
        """Handle UltraMsg webhook"""
        data = json.loads(raw_body.decode()

        result = {
            "from": data.get("from"),
            "to": data.get("to"),
            "body": data.get("body"),
            "type": data.get("type", "text"),
            "message_id": data.get("id"),
            "timestamp": data.get("time"),
            "provider": "ultramsg"
        }

        return result

    async def _handle_infobip_webhook(self, raw_body: bytes) -> Dict[str, Any]:
        """Handle Infobip webhook"""
        data = json.loads(raw_body.decode()

        # Infobip can send different webhook types
        if "results" in data:
            # Delivery report
            result = {
                "type": "delivery_report",
                "message_id": data["results"][0].get("messageId"),
                "status": data["results"][0].get("status", {}).get("groupName"),
                "provider": "infobip"
            }
        else:
            # Incoming message
            result = {
                "type": "incoming_message",
                "from": data.get("from"),
                "to": data.get("to"),
                "body": data.get("message", {}).get("text"),
                "message_id": data.get("messageId"),
                "timestamp": data.get("receivedAt"),
                "provider": "infobip"
            }

        return result
