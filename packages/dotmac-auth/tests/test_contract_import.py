def test_import_auth():
    import importlib
    mod = importlib.import_module('dotmac.auth')
    assert hasattr(mod, 'JWTService')
    assert hasattr(mod, 'EdgeJWTValidator')

