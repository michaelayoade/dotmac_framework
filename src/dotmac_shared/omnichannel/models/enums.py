"""
Common enumerations for the omnichannel service.
"""

from enum import Enum


class ChannelType(str, Enum):
    """Communication channel types."""

    EMAIL = "email"
    SMS = "sms"
    PHONE = "phone"
    CHAT = "chat"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    SLACK = "slack"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    WEBHOOK = "webhook"
    API = "api"
    SOCIAL_MEDIA = "social_media"
    VIDEO_CALL = "video_call"
    IN_PERSON = "in_person"


class MessageStatus(str, Enum):
    """Message delivery status enumeration."""

    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    BOUNCED = "bounced"
    REJECTED = "rejected"
    RATE_LIMITED = "rate_limited"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
