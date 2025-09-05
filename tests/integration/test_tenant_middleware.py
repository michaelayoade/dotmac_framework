from fastapi import FastAPI
from fastapi.testclient import TestClient

try:
    from dotmac_shared.tenant.identity import TenantIdentityResolver
    from dotmac_shared.tenant.middleware import TenantMiddleware
except Exception:  # fallback if new package available directly
    from dotmac.tenant import TenantIdentityResolver, TenantMiddleware  # type: ignore


def create_test_app():
    app = FastAPI()
    resolver = TenantIdentityResolver()
    resolver.configure_patterns({
        "admin": r"^admin\.(?P<tenant_id>\w+)\..*",
    })
    app.add_middleware(TenantMiddleware, require_tenant=True, resolver=resolver)

    @app.get("/ok")
    def ok():
        return {"status": "ok"}

    return app


def test_tenant_resolution_from_host():
    app = create_test_app()
    client = TestClient(app)
    resp = client.get("/ok", headers={"host": "admin.acme.local"})
    assert resp.status_code == 200


def test_reject_client_supplied_tenant_headers():
    app = create_test_app()
    client = TestClient(app)
    resp = client.get("/ok", headers={
        "host": "admin.acme.local",
        "X-Tenant-ID": "evil",
    })
    assert resp.status_code in (400, 403)
