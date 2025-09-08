"""
Shared model definitions for the DotMac framework.
"""

from .customer import *
from .service_plan import *

__all__ = [
    "Customer",
    "ServicePlan",
    "BandwidthTier",
]
