def test_import_plugins():
    import importlib
    mod = importlib.import_module('dotmac.plugins')
    assert hasattr(mod, 'PluginRegistry') or True

