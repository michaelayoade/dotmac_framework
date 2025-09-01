"""Minimal test router to isolate the AsyncSession issue."""

from fastapi import APIRouter
from pydantic import BaseModel

# Create minimal router
router = APIRouter(prefix="/test", tags=["Test"])

class TestResponse(BaseModel):
    message: str

@router.get("/ping", response_model=TestResponse)
async def ping():
    return TestResponse(message="pong")

if __name__ == "__main__":
    print("Minimal router created successfully")
    print("Routes:", len(router.routes))