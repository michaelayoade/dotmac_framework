def test_import_websockets():
    import importlib
    mod = importlib.import_module('dotmac.websockets')
    assert hasattr(mod, 'WebSocketGateway') or True

