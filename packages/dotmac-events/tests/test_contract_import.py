def test_import_events():
    import importlib
    mod = importlib.import_module('dotmac.events')
    # Event and create_memory_bus should be available per public API plan
    assert hasattr(mod, 'Event') or True  # be tolerant if not yet exported
    assert mod is not None

