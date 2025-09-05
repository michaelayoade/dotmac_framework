"""
Minimal ISPUserAdapter stub for tests.
"""

from __future__ import annotations


class ISPUserAdapter:
    def __init__(self, *args, **kwargs):  # noqa: ANN001
        pass

    async def to_isp_user(self, user):  # noqa: ANN001
        return user

    async def from_isp_user(self, isp_user):  # noqa: ANN001
        return isp_user


__all__ = ["ISPUserAdapter"]
