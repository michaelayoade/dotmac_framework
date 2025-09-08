"""
DotMac Performance Benchmarking Suite

Modular benchmarking toolkit providing:
- Core benchmarking framework with BenchmarkRunner
- Optional HTTP endpoint benchmarking (requires httpx)
- Optional database query profiling (requires sqlalchemy)  
- Optional system metrics collection (requires psutil)
- Benchmark comparison and reporting utilities

Quick Start:
    from dotmac_benchmarking import BenchmarkRunner
    
    runner = BenchmarkRunner()
    results = await runner.run("test", your_async_function, samples=5)
    
    # With optional modules
    from dotmac_benchmarking.http import benchmark_http_request  # requires [http]
    from dotmac_benchmarking.db import benchmark_query          # requires [db]
    from dotmac_benchmarking.system import snapshot             # requires [system]
"""

from .core import BenchmarkRunner
from .report import summarize, to_json

__version__ = "1.0.0"

__all__ = [
    "BenchmarkRunner",
    "summarize",
    "to_json",
]
