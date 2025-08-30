"""
Omnichannel Communication Plugins

Contains reference implementations of communication plugins
using the DotMac plugin system architecture.

Author: DotMac Framework Team
License: MIT
"""

from .twilio_sms_plugin import TwilioSMSPlugin

__all__ = ["TwilioSMSPlugin"]
