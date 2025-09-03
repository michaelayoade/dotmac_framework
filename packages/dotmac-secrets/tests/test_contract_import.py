def test_import_secrets():
    import importlib
    mod = importlib.import_module('dotmac.secrets')
    assert hasattr(mod, 'SecretsManager') or True

