"""
Secrets Providers

Providers for secrets management integration with external systems.
"""

from .secrets import SecretsProvider, MockSecretsProvider

# Try to import DotMacSecretsAdapter if new secrets package is available
try:
    from .secrets import DotMacSecretsAdapter
    _DOTMAC_SECRETS_AVAILABLE = True
except ImportError:
    _DOTMAC_SECRETS_AVAILABLE = False

# Optional OpenBao provider - only available with secrets extra
try:
    from .openbao import OpenBaoProvider, create_openbao_provider
    _OPENBAO_AVAILABLE = True
except ImportError:
    _OPENBAO_AVAILABLE = False

# Build __all__ based on available imports
__all__ = ["SecretsProvider", "MockSecretsProvider"]

if _DOTMAC_SECRETS_AVAILABLE:
    __all__.append("DotMacSecretsAdapter")

if _OPENBAO_AVAILABLE:
    __all__.extend(["OpenBaoProvider", "create_openbao_provider"])