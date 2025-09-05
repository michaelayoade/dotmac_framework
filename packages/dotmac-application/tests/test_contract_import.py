def test_import_application():
    import importlib

    mod = importlib.import_module("dotmac.application")
    assert hasattr(mod, "create_app")
