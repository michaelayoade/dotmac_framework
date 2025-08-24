"""
CONTRACT TESTING - API AND SERVICE CONTRACTS
============================================

Tests API contracts and external service integrations to ensure
that changes don't break external dependencies or downstream consumers.

Focus: Payment processors, SNMP devices, email services, SMS providers
"""

import pytest
import httpx
import json
import asyncio
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from enum import Enum
import jsonschema
from jsonschema import validate, ValidationError


class ContractType(Enum):
    PAYMENT_PROCESSOR = "payment_processor"
    SNMP_DEVICE = "snmp_device"
    EMAIL_SERVICE = "email_service"
    SMS_SERVICE = "sms_service"
    WEBHOOKS = "webhooks"


@dataclass
class ContractTest:
    """Contract test definition."""
    name: str
    contract_type: ContractType
    request_schema: Dict[str, Any]
    response_schema: Dict[str, Any]
    expected_behavior: str
    test_data: Dict[str, Any]


class ContractValidator:
    """
    Validates API contracts against expected schemas and behaviors.
    
    Uses JSON Schema validation and mock responses to ensure
    external service contracts are maintained.
    """
    
    def __init__(self):
        self.contracts = self._load_contracts()
    
    def validate_request(self, contract_name: str, request_data: Dict[str, Any]) -> bool:
        """Validate request data against contract schema."""
        contract = self.contracts.get(contract_name)
        if not contract:
            raise ValueError(f"Contract {contract_name} not found")
        
        try:
            validate(instance=request_data, schema=contract.request_schema)
            return True
        except ValidationError as e:
            raise ValueError(f"Request validation failed: {e.message}")
    
    def validate_response(self, contract_name: str, response_data: Dict[str, Any]) -> bool:
        """Validate response data against contract schema."""
        contract = self.contracts.get(contract_name)
        if not contract:
            raise ValueError(f"Contract {contract_name} not found")
        
        try:
            validate(instance=response_data, schema=contract.response_schema)
            return True
        except ValidationError as e:
            raise ValueError(f"Response validation failed: {e.message}")
    
    def _load_contracts(self) -> Dict[str, ContractTest]:
        """Load contract definitions."""
        return {
            'stripe_payment': ContractTest(
                name='stripe_payment',
                contract_type=ContractType.PAYMENT_PROCESSOR,
                request_schema=self._stripe_payment_request_schema(),
                response_schema=self._stripe_payment_response_schema(),
                expected_behavior='Process payment and return confirmation',
                test_data=self._stripe_test_data()
            ),
            'sendgrid_email': ContractTest(
                name='sendgrid_email',
                contract_type=ContractType.EMAIL_SERVICE,
                request_schema=self._sendgrid_request_schema(),
                response_schema=self._sendgrid_response_schema(),
                expected_behavior='Send email and return message ID',
                test_data=self._sendgrid_test_data()
            ),
            'twilio_sms': ContractTest(
                name='twilio_sms', 
                contract_type=ContractType.SMS_SERVICE,
                request_schema=self._twilio_request_schema(),
                response_schema=self._twilio_response_schema(),
                expected_behavior='Send SMS and return message SID',
                test_data=self._twilio_test_data()
            ),
            'snmp_device': ContractTest(
                name='snmp_device',
                contract_type=ContractType.SNMP_DEVICE,
                request_schema=self._snmp_request_schema(),
                response_schema=self._snmp_response_schema(),
                expected_behavior='Query device status and return metrics',
                test_data=self._snmp_test_data()
            ),
            'billing_webhook': ContractTest(
                name='billing_webhook',
                contract_type=ContractType.WEBHOOKS,
                request_schema=self._webhook_request_schema(),
                response_schema=self._webhook_response_schema(),
                expected_behavior='Receive webhook and acknowledge',
                test_data=self._webhook_test_data()
            )
        }
    
    # Schema definitions
    def _stripe_payment_request_schema(self) -> Dict[str, Any]:
        """Stripe payment request schema."""
        return {
            "type": "object",
            "properties": {
                "amount": {"type": "integer", "minimum": 1},
                "currency": {"type": "string", "enum": ["usd", "eur", "gbp", "cad"]},
                "payment_method": {"type": "string"},
                "customer": {"type": "string"},
                "description": {"type": "string"},
                "metadata": {
                    "type": "object",
                    "properties": {
                        "invoice_id": {"type": "string"},
                        "customer_id": {"type": "string"}
                    }
                }
            },
            "required": ["amount", "currency", "payment_method"],
            "additionalProperties": False
        }
    
    def _stripe_payment_response_schema(self) -> Dict[str, Any]:
        """Stripe payment response schema."""
        return {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "amount": {"type": "integer"},
                "currency": {"type": "string"},
                "status": {"type": "string", "enum": ["succeeded", "pending", "failed"]},
                "created": {"type": "integer"},
                "payment_method": {"type": "string"},
                "receipt_url": {"type": ["string", "null"]},
                "failure_code": {"type": ["string", "null"]},
                "failure_message": {"type": ["string", "null"]}
            },
            "required": ["id", "amount", "currency", "status", "created"],
            "additionalProperties": True
        }
    
    def _sendgrid_request_schema(self) -> Dict[str, Any]:
        """SendGrid email request schema."""
        return {
            "type": "object",
            "properties": {
                "personalizations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "to": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "email": {"type": "string", "format": "email"},
                                        "name": {"type": "string"}
                                    },
                                    "required": ["email"]
                                }
                            },
                            "subject": {"type": "string"}
                        },
                        "required": ["to", "subject"]
                    }
                },
                "from": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string", "format": "email"},
                        "name": {"type": "string"}
                    },
                    "required": ["email"]
                },
                "content": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["text/plain", "text/html"]},
                            "value": {"type": "string"}
                        },
                        "required": ["type", "value"]
                    }
                }
            },
            "required": ["personalizations", "from", "content"]
        }
    
    def _sendgrid_response_schema(self) -> Dict[str, Any]:
        """SendGrid response schema."""
        return {
            "type": "object",
            "properties": {
                "message_id": {"type": "string"},
                "status": {"type": "string", "enum": ["sent", "queued", "failed"]},
                "timestamp": {"type": "integer"}
            },
            "required": ["message_id", "status"]
        }
    
    def _twilio_request_schema(self) -> Dict[str, Any]:
        """Twilio SMS request schema."""
        return {
            "type": "object",
            "properties": {
                "To": {"type": "string", "pattern": r"^\+1\d{10}$"},
                "From": {"type": "string", "pattern": r"^\+1\d{10}$"},
                "Body": {"type": "string", "maxLength": 1600},
                "StatusCallback": {"type": "string", "format": "uri"}
            },
            "required": ["To", "From", "Body"]
        }
    
    def _twilio_response_schema(self) -> Dict[str, Any]:
        """Twilio SMS response schema."""
        return {
            "type": "object",
            "properties": {
                "sid": {"type": "string"},
                "status": {"type": "string", "enum": ["queued", "sent", "failed", "delivered"]},
                "to": {"type": "string"},
                "from": {"type": "string"},
                "body": {"type": "string"},
                "price": {"type": ["string", "null"]},
                "error_code": {"type": ["integer", "null"]},
                "error_message": {"type": ["string", "null"]}
            },
            "required": ["sid", "status", "to", "from", "body"]
        }
    
    def _snmp_request_schema(self) -> Dict[str, Any]:
        """SNMP device query schema."""
        return {
            "type": "object",
            "properties": {
                "host": {"type": "string", "format": "ipv4"},
                "community": {"type": "string"},
                "oids": {
                    "type": "array",
                    "items": {"type": "string", "pattern": r"^\d+(\.\d+)*$"}
                },
                "version": {"type": "string", "enum": ["1", "2c", "3"]}
            },
            "required": ["host", "community", "oids"]
        }
    
    def _snmp_response_schema(self) -> Dict[str, Any]:
        """SNMP device response schema."""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "values": {
                    "type": "object",
                    "patternProperties": {
                        r"^\d+(\.\d+)*$": {
                            "type": "object",
                            "properties": {
                                "value": {"type": ["string", "integer", "number"]},
                                "type": {"type": "string"}
                            },
                            "required": ["value", "type"]
                        }
                    }
                },
                "error": {"type": ["string", "null"]}
            },
            "required": ["success"]
        }
    
    def _webhook_request_schema(self) -> Dict[str, Any]:
        """Webhook request schema."""
        return {
            "type": "object",
            "properties": {
                "event_type": {"type": "string"},
                "timestamp": {"type": "integer"},
                "data": {"type": "object"},
                "signature": {"type": "string"}
            },
            "required": ["event_type", "timestamp", "data"]
        }
    
    def _webhook_response_schema(self) -> Dict[str, Any]:
        """Webhook response schema."""
        return {
            "type": "object",
            "properties": {
                "acknowledged": {"type": "boolean"},
                "processed_at": {"type": "integer"},
                "message": {"type": "string"}
            },
            "required": ["acknowledged"]
        }
    
    # Test data
    def _stripe_test_data(self) -> Dict[str, Any]:
        return {
            "request": {
                "amount": 7999,  # $79.99
                "currency": "usd",
                "payment_method": "pm_1234567890",
                "customer": "cus_1234567890",
                "description": "Monthly ISP service",
                "metadata": {
                    "invoice_id": "INV-20240101-ABCD1234",
                    "customer_id": "customer_123"
                }
            },
            "response": {
                "id": "pi_1234567890abcdef",
                "amount": 7999,
                "currency": "usd",
                "status": "succeeded",
                "created": 1640995200,
                "payment_method": "pm_1234567890",
                "receipt_url": "https://pay.stripe.com/receipts/123",
                "failure_code": None,
                "failure_message": None
            }
        }
    
    def _sendgrid_test_data(self) -> Dict[str, Any]:
        return {
            "request": {
                "personalizations": [
                    {
                        "to": [{"email": "customer@example.com", "name": "John Smith"}],
                        "subject": "Your ISP Bill is Ready"
                    }
                ],
                "from": {"email": "billing@dotmacisp.com", "name": "DotMac ISP"},
                "content": [
                    {
                        "type": "text/plain",
                        "value": "Your monthly bill is now available for download."
                    }
                ]
            },
            "response": {
                "message_id": "14c5d75ce93-dfe23c70-94c3-11e9-a7d5-4b65b0a42c5a",
                "status": "sent",
                "timestamp": 1640995200
            }
        }
    
    def _twilio_test_data(self) -> Dict[str, Any]:
        return {
            "request": {
                "To": "+15551234567",
                "From": "+15559876543",
                "Body": "Your DotMac ISP service will be installed tomorrow at 2 PM.",
                "StatusCallback": "https://api.dotmacisp.com/webhooks/sms/status"
            },
            "response": {
                "sid": "SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "status": "queued",
                "to": "+15551234567",
                "from": "+15559876543",
                "body": "Your DotMac ISP service will be installed tomorrow at 2 PM.",
                "price": "0.0075",
                "error_code": None,
                "error_message": None
            }
        }
    
    def _snmp_test_data(self) -> Dict[str, Any]:
        return {
            "request": {
                "host": "192.168.1.1",
                "community": "public",
                "oids": ["1.3.6.1.2.1.1.3.0", "1.3.6.1.2.1.2.2.1.10.1"],
                "version": "2c"
            },
            "response": {
                "success": True,
                "values": {
                    "1.3.6.1.2.1.1.3.0": {
                        "value": "1234567",
                        "type": "timeticks"
                    },
                    "1.3.6.1.2.1.2.2.1.10.1": {
                        "value": "1024000000",
                        "type": "counter64"
                    }
                },
                "error": None
            }
        }
    
    def _webhook_test_data(self) -> Dict[str, Any]:
        return {
            "request": {
                "event_type": "payment.succeeded",
                "timestamp": 1640995200,
                "data": {
                    "payment_id": "pi_1234567890abcdef",
                    "amount": 7999,
                    "customer_id": "cus_1234567890"
                },
                "signature": "t=1640995200,v1=abcdef123456..."
            },
            "response": {
                "acknowledged": True,
                "processed_at": 1640995205,
                "message": "Payment webhook processed successfully"
            }
        }


# CONTRACT TESTS
@pytest.mark.contract
@pytest.mark.external_api
class TestPaymentProcessorContracts:
    """Test payment processor API contracts."""
    
    def test_stripe_payment_contract(self):
        """CONTRACT: Stripe payment API contract validation."""
        validator = ContractValidator()
        contract = validator.contracts['stripe_payment']
        
        # Test request validation
        request_data = contract.test_data['request']
        assert validator.validate_request('stripe_payment', request_data)
        
        # Test response validation  
        response_data = contract.test_data['response']
        assert validator.validate_response('stripe_payment', response_data)
        
        # Test that invalid request fails
        invalid_request = {**request_data, 'amount': -100}  # Negative amount
        with pytest.raises(ValueError, match="Request validation failed"):
            validator.validate_request('stripe_payment', invalid_request)
    
    @patch('httpx.AsyncClient.post')
    async def test_stripe_payment_integration_contract(self, mock_post):
        """CONTRACT: Stripe payment integration maintains expected behavior."""
        # Mock Stripe response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "pi_test_123456",
            "amount": 7999,
            "currency": "usd", 
            "status": "succeeded",
            "created": 1640995200,
            "payment_method": "pm_test_card",
            "receipt_url": "https://pay.stripe.com/receipts/test123"
        }
        mock_post.return_value = mock_response
        
        # Test payment processing
        payment_processor = StripePaymentProcessor(api_key="sk_test_123")
        result = await payment_processor.process_payment(
            amount=Decimal('79.99'),
            currency='usd',
            payment_method='pm_test_card',
            customer_id='cus_test_123'
        )
        
        # Verify contract compliance
        assert result['status'] == 'succeeded'
        assert result['amount'] == 7999  # Stripe uses cents
        assert 'id' in result
        assert result['id'].startswith('pi_')


@pytest.mark.contract
@pytest.mark.external_api  
class TestEmailServiceContracts:
    """Test email service API contracts."""
    
    def test_sendgrid_email_contract(self):
        """CONTRACT: SendGrid email API contract validation."""
        validator = ContractValidator()
        contract = validator.contracts['sendgrid_email']
        
        # Test request validation
        request_data = contract.test_data['request']
        assert validator.validate_request('sendgrid_email', request_data)
        
        # Test response validation
        response_data = contract.test_data['response']
        assert validator.validate_response('sendgrid_email', response_data)
        
        # Test invalid email format fails
        invalid_request = {**request_data}
        invalid_request['personalizations'][0]['to'][0]['email'] = 'not-an-email'
        
        with pytest.raises(ValueError, match="Request validation failed"):
            validator.validate_request('sendgrid_email', invalid_request)
    
    @patch('httpx.AsyncClient.post')
    async def test_sendgrid_integration_contract(self, mock_post):
        """CONTRACT: SendGrid integration maintains expected behavior.""" 
        # Mock SendGrid response
        mock_response = Mock()
        mock_response.status_code = 202  # SendGrid returns 202 for queued
        mock_response.headers = {'X-Message-Id': 'test-message-id-12345'}
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response
        
        # Test email sending
        email_service = SendGridEmailService(api_key="SG.test-key")
        result = await email_service.send_email(
            to_email="customer@example.com",
            subject="Test Email",
            content="Test email content",
            from_email="noreply@dotmacisp.com"
        )
        
        # Verify contract compliance
        assert result['status'] == 'sent'
        assert 'message_id' in result
        assert result['message_id'] == 'test-message-id-12345'


@pytest.mark.contract
@pytest.mark.network_device
class TestSNMPDeviceContracts:
    """Test SNMP network device contracts."""
    
    def test_snmp_device_contract(self):
        """CONTRACT: SNMP device query contract validation."""
        validator = ContractValidator()
        contract = validator.contracts['snmp_device']
        
        # Test request validation
        request_data = contract.test_data['request']
        assert validator.validate_request('snmp_device', request_data)
        
        # Test response validation
        response_data = contract.test_data['response']
        assert validator.validate_response('snmp_device', response_data)
        
        # Test invalid IP address fails
        invalid_request = {**request_data, 'host': '999.999.999.999'}
        with pytest.raises(ValueError, match="Request validation failed"):
            validator.validate_request('snmp_device', invalid_request)
    
    @patch('pysnmp.hlapi.nextCmd')
    def test_snmp_device_integration_contract(self, mock_snmp):
        """CONTRACT: SNMP device integration maintains expected behavior."""
        # Mock SNMP response
        mock_snmp.return_value = [
            (None, None, 0, [
                ('1.3.6.1.2.1.1.3.0', '1234567'),
                ('1.3.6.1.2.1.2.2.1.10.1', '1024000000')
            ])
        ]
        
        # Test SNMP query
        snmp_client = SNMPClient()
        result = snmp_client.query_device(
            host='192.168.1.1',
            community='public',
            oids=['1.3.6.1.2.1.1.3.0', '1.3.6.1.2.1.2.2.1.10.1']
        )
        
        # Verify contract compliance
        assert result['success'] is True
        assert '1.3.6.1.2.1.1.3.0' in result['values']
        assert '1.3.6.1.2.1.2.2.1.10.1' in result['values']


@pytest.mark.contract
@pytest.mark.webhooks
class TestWebhookContracts:
    """Test webhook contracts for external integrations."""
    
    def test_billing_webhook_contract(self):
        """CONTRACT: Billing webhook contract validation."""
        validator = ContractValidator()
        contract = validator.contracts['billing_webhook']
        
        # Test request validation
        request_data = contract.test_data['request']
        assert validator.validate_request('billing_webhook', request_data)
        
        # Test response validation
        response_data = contract.test_data['response'] 
        assert validator.validate_response('billing_webhook', response_data)
    
    def test_webhook_signature_validation(self):
        """CONTRACT: Webhook signature validation is enforced."""
        webhook_handler = WebhookHandler(secret_key="test-webhook-secret")
        
        # Valid webhook payload
        payload = {
            "event_type": "payment.succeeded",
            "timestamp": 1640995200,
            "data": {"payment_id": "pi_123", "amount": 7999}
        }
        
        # Test with valid signature
        signature = webhook_handler.generate_signature(payload)
        assert webhook_handler.validate_signature(payload, signature)
        
        # Test with invalid signature fails
        invalid_signature = "invalid-signature"
        assert not webhook_handler.validate_signature(payload, invalid_signature)


# MOCK IMPLEMENTATIONS FOR TESTING
class StripePaymentProcessor:
    """Mock Stripe payment processor for contract testing."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def process_payment(
        self, 
        amount: Decimal, 
        currency: str, 
        payment_method: str,
        customer_id: str
    ) -> Dict[str, Any]:
        """Process payment through Stripe API."""
        # Convert to cents
        amount_cents = int(amount * 100)
        
        # Mock API call (in real implementation, this would call Stripe)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.stripe.com/v1/payment_intents",
                headers={"Authorization": f"Bearer {self.api_key}"},
                data={
                    "amount": amount_cents,
                    "currency": currency,
                    "payment_method": payment_method,
                    "customer": customer_id,
                    "confirm": True
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Payment failed: {response.status_code}")


class SendGridEmailService:
    """Mock SendGrid email service for contract testing."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def send_email(
        self, 
        to_email: str, 
        subject: str, 
        content: str,
        from_email: str = "noreply@dotmacisp.com"
    ) -> Dict[str, Any]:
        """Send email through SendGrid API."""
        payload = {
            "personalizations": [
                {"to": [{"email": to_email}], "subject": subject}
            ],
            "from": {"email": from_email},
            "content": [{"type": "text/plain", "value": content}]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
            if response.status_code == 202:
                message_id = response.headers.get('X-Message-Id', 'unknown')
                return {
                    'status': 'sent',
                    'message_id': message_id
                }
            else:
                raise Exception(f"Email send failed: {response.status_code}")


class SNMPClient:
    """Mock SNMP client for contract testing."""
    
    def query_device(
        self, 
        host: str, 
        community: str, 
        oids: List[str]
    ) -> Dict[str, Any]:
        """Query SNMP device for OID values."""
        try:
            # Mock SNMP query (in real implementation, would use pysnmp)
            values = {}
            for oid in oids:
                if oid == "1.3.6.1.2.1.1.3.0":  # System uptime
                    values[oid] = {"value": "1234567", "type": "timeticks"}
                elif oid == "1.3.6.1.2.1.2.2.1.10.1":  # Interface bytes in
                    values[oid] = {"value": "1024000000", "type": "counter64"}
                else:
                    values[oid] = {"value": "unknown", "type": "string"}
            
            return {
                "success": True,
                "values": values,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "values": {},
                "error": str(e)
            }


class WebhookHandler:
    """Mock webhook handler for contract testing."""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
    
    def generate_signature(self, payload: Dict[str, Any]) -> str:
        """Generate webhook signature."""
        import hashlib
        import hmac
        
        payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"
    
    def validate_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        """Validate webhook signature."""
        expected_signature = self.generate_signature(payload)
        return hmac.compare_digest(expected_signature, signature)


if __name__ == "__main__":
    # Quick contract validation test
    validator = ContractValidator()
    
    # Test Stripe contract
    stripe_contract = validator.contracts['stripe_payment']
    request_data = stripe_contract.test_data['request']
    response_data = stripe_contract.test_data['response']
    
    assert validator.validate_request('stripe_payment', request_data)
    assert validator.validate_response('stripe_payment', response_data)
    
    print("✅ Contract testing validation passed!")