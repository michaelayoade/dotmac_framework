def test_import_tenant():
    import importlib
    mod = importlib.import_module('dotmac.tenant')
    assert hasattr(mod, 'TenantIdentityResolver')
    assert hasattr(mod, 'TenantMiddleware')

