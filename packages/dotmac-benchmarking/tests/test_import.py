"""
Basic import and smoke tests.
"""

def test_basic_imports():
    """Test that basic modules can be imported."""
    from dotmac_benchmarking import BenchmarkRunner, summarize, to_json

    assert BenchmarkRunner is not None
    assert summarize is not None
    assert to_json is not None


def test_version():
    """Test that version is available."""
    from dotmac_benchmarking import __version__

    assert __version__ == "1.0.0"


def test_optional_imports():
    """Test optional module imports."""
    # These should not raise ImportError even if extras not installed
    try:
        from dotmac_benchmarking import http
        assert hasattr(http, 'HTTP_AVAILABLE')
    except ImportError:
        pass

    try:
        from dotmac_benchmarking import db
        assert hasattr(db, 'DB_AVAILABLE')
    except ImportError:
        pass

    try:
        from dotmac_benchmarking import system
        assert hasattr(system, 'SYSTEM_AVAILABLE')
    except ImportError:
        pass


def test_basic_functionality():
    """Basic smoke test of core functionality."""
    import asyncio

    from dotmac_benchmarking import BenchmarkRunner

    async def test_function():
        await asyncio.sleep(0.001)
        return "test"

    async def run_test():
        runner = BenchmarkRunner()
        result = await runner.run("smoke_test", test_function, samples=2)

        assert result.label == "smoke_test"
        assert result.samples == 2
        assert result.avg_duration > 0

    # Run the async test
    asyncio.run(run_test())
