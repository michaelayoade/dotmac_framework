"""Minimal test router to isolate the StandardDeps dependency issue."""

from fastapi import APIRouter
from pydantic import BaseModel
from dotmac_shared.api.dependencies import StandardDeps
from dotmac_shared.api.exception_handlers import standard_exception_handler

# Create minimal router
router = APIRouter(prefix="/test", tags=["Test"])

class TestResponse(BaseModel):
    message: str

@router.get("/ping", response_model=TestResponse)
async def ping():
    return TestResponse(message="pong")

@router.get("/deps-test", response_model=TestResponse)
@standard_exception_handler  
async def deps_test(deps: StandardDeps) -> TestResponse:
    return TestResponse(message=f"deps work - user: {deps.user_id}")

if __name__ == "__main__":
    print("Testing router creation...")
    try:
        print("✅ Minimal router created successfully")
        print(f"✅ Routes: {len(router.routes)}")
        for route in router.routes:
            print(f"  - {route.methods} {route.path}")
    except Exception as e:
        print(f"❌ Router creation failed: {e}")
        import traceback
        traceback.print_exc()