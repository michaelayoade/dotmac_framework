"""
Minimal Audit API (stub) to resolve syntax issues.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
