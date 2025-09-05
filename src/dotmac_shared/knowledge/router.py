"""
Knowledge Base API Router (stub to fix syntax issues).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/knowledge", tags=["knowledge-base"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
