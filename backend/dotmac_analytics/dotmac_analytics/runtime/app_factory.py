"""
FastAPI application factory for dotmac_analytics.

Provides application creation with:
- SDK initialization
- Middleware setup
- Error handlers
- Health checks
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import RuntimeConfig, load_config


def create_app(config: RuntimeConfig = None) -> FastAPI:
    """Create FastAPI application with analytics configuration."""

    if config is None:
        config = load_config()

    app = FastAPI(
        title="DotMac Analytics",
        description="Analytics and Business Intelligence for ISP Operations",
        version="1.0.0",
        docs_url="/docs" if config.debug else None,
        redoc_url="/redoc" if config.debug else None
    )

    # CORS middleware
    if config.security.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.security.cors_origins,
            allow_credentials=True,
            allow_methods=config.security.cors_methods,
            allow_headers=config.security.cors_headers,
        )

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "dotmac-analytics"}

    return app


def create_production_app() -> FastAPI:
    """Create production-ready FastAPI application."""

    config = load_config()
    config.debug = False
    config.environment = "production"

    return create_app(config)
