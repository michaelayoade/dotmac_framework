def test_import_database():
    import importlib
    mod = importlib.import_module('dotmac.database')
    assert hasattr(mod, 'Base')
    assert hasattr(mod, 'create_async_engine')

