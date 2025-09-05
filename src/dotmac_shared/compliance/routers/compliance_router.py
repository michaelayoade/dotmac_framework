"""
Compliance Router (stubbed to resolve syntax issues).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
