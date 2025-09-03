def test_import_tasks():
    import importlib
    mod = importlib.import_module('dotmac.tasks')
    assert hasattr(mod, 'BackgroundOperationsMiddleware')
    assert hasattr(mod, 'BackgroundOperationsManager')

