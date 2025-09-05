"""
Operations API Routers (minimal, syntax-safe stubs).
"""

from fastapi import APIRouter, HTTPException


class OperationsRouterFactory:
    """Minimal factory to avoid parse errors in CI/linting.

    Replace or extend with full implementations as needed.
    """

    @classmethod
    def create_network_monitoring_router(
        cls, service_class, prefix: str = "/network-monitoring"
    ) -> APIRouter:
        router = APIRouter(prefix=prefix, tags=["operations", "network-monitoring"])

        @router.get("/health")
        async def health() -> dict[str, str]:
            return {"status": "ok"}

        @router.post("/endpoints")
        async def not_implemented():
            raise HTTPException(status_code=501, detail="Not implemented")

        return router

    @classmethod
    def create_customer_lifecycle_router(
        cls, service_class, prefix: str = "/customer-lifecycle"
    ) -> APIRouter:
        router = APIRouter(prefix=prefix, tags=["operations", "customer-lifecycle"])

        @router.get("/health")
        async def health() -> dict[str, str]:
            return {"status": "ok"}

        @router.post("/register")
        async def not_implemented():
            raise HTTPException(status_code=501, detail="Not implemented")

        return router
