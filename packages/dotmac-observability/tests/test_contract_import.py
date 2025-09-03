def test_import_observability():
    import importlib
    mod = importlib.import_module('dotmac.observability')
    # basic public functions
    assert hasattr(mod, 'create_default_config')
    assert hasattr(mod, 'initialize_otel')
    assert hasattr(mod, 'initialize_metrics_registry')

