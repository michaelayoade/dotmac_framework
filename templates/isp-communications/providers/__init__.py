from .email import EmailProvider
from .sms import SMSProvider
from .whatsapp import WhatsAppProvider


# Initialize providers
email = EmailProvider()
sms = SMSProvider()
whatsapp = WhatsAppProvider()

__all__ = ["email", "sms", "whatsapp"]
