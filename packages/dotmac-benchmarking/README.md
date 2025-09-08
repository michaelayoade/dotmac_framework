# dotmac-benchmarking

Modular benchmarking toolkit for API, database, HTTP, and system profiling with comparison and reporting capabilities.

## Purpose

The `dotmac-benchmarking` package provides a comprehensive suite of benchmarking tools for:
- API endpoint load testing and performance profiling
- Database query performance analysis  
- HTTP request benchmarking
- System resource monitoring (CPU, memory, disk, network)
- Benchmark comparison and regression detection
- Automated performance reporting

## Installation

### Basic Installation
```bash
pip install dotmac-benchmarking
```

### With Optional Dependencies
```bash
# HTTP benchmarking support
pip install dotmac-benchmarking[http]

# Database benchmarking support  
pip install dotmac-benchmarking[db]

# System metrics collection
pip install dotmac-benchmarking[system]

# All optional dependencies
pip install dotmac-benchmarking[http,db,system]
```

## Quick Start

### Basic Benchmark Runner

```python
import asyncio
from dotmac_benchmarking import BenchmarkRunner

async def sample_function():
    """Function to benchmark"""
    await asyncio.sleep(0.1)
    return "completed"

async def main():
    runner = BenchmarkRunner()
    
    # Run benchmark with 5 samples
    results = await runner.run("sample_test", sample_function, samples=5)
    
    print(f"Average time: {results['avg_duration']:.3f}s")
    print(f"Min time: {results['min_duration']:.3f}s") 
    print(f"Max time: {results['max_duration']:.3f}s")

asyncio.run(main())
```

### HTTP Benchmarking (requires `[http]` extra)

```python
from dotmac_benchmarking.http import benchmark_http_request
import httpx

async def benchmark_api():
    async with httpx.AsyncClient() as client:
        results = await benchmark_http_request(
            client, 
            "GET", 
            "https://api.example.com/health"
        )
        
        print(f"Response time: {results['duration']:.3f}s")
        print(f"Status code: {results['status_code']}")
```

### Database Benchmarking (requires `[db]` extra)

```python
from dotmac_benchmarking.db import benchmark_query
from sqlalchemy.ext.asyncio import create_async_engine

async def benchmark_database():
    engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
    
    results = await benchmark_query(
        engine,
        "SELECT COUNT(*) FROM users WHERE active = $1",
        {"1": True}
    )
    
    print(f"Query time: {results['duration']:.3f}s")
    print(f"Rows affected: {results.get('rowcount', 'N/A')}")
```

### System Monitoring (requires `[system]` extra)

```python
from dotmac_benchmarking.system import snapshot

# Take a system snapshot
metrics = snapshot()
print(f"CPU usage: {metrics['cpu_percent']}%")
print(f"Memory usage: {metrics['memory_percent']}%")  
print(f"Disk usage: {metrics['disk_usage']}%")
```

### Benchmark Comparison

```python
from dotmac_benchmarking import BenchmarkRunner
from dotmac_benchmarking.report import summarize, to_json

async def compare_implementations():
    runner = BenchmarkRunner()
    
    # Benchmark different implementations
    results_v1 = await runner.run("algorithm_v1", algorithm_v1)
    results_v2 = await runner.run("algorithm_v2", algorithm_v2)
    
    # Compare results
    comparison = runner.compare([results_v1, results_v2])
    
    # Generate report
    summary = summarize([results_v1, results_v2])
    report_json = to_json(summary)
    
    print(report_json)
```

## API Reference

### Core Classes

#### `BenchmarkRunner`

The main benchmarking orchestrator.

```python
class BenchmarkRunner:
    async def run(
        self, 
        label: str, 
        fn: Callable[[], Awaitable[Any]], 
        *, 
        samples: int = 3
    ) -> dict:
        """Run benchmark with specified number of samples"""
        
    def compare(self, results: list[dict]) -> dict:
        """Compare multiple benchmark results"""
```

### HTTP Module (optional)

```python
async def benchmark_http_request(
    client: httpx.AsyncClient, 
    method: str, 
    url: str, 
    **kwargs
) -> dict:
    """Benchmark an HTTP request"""
```

### Database Module (optional)  

```python
async def benchmark_query(
    engine_or_session, 
    query: str, 
    params: dict | None = None
) -> dict:
    """Benchmark a database query"""
```

### System Module (optional)

```python
def snapshot() -> dict[str, Any]:
    """Take a snapshot of current system metrics"""
```

### Report Module

```python
def summarize(results: list[dict]) -> dict:
    """Create summary from multiple benchmark results"""
    
def to_json(report: dict) -> str:
    """Convert report to JSON string"""
```

## Examples

See the `examples/` directory for comprehensive usage examples:

- `basic_benchmarking.py` - Core benchmarking functionality
- `http_benchmarking.py` - HTTP endpoint testing  
- `database_benchmarking.py` - Database query profiling
- `system_monitoring.py` - System resource monitoring
- `comparison_reporting.py` - Benchmark comparison and reporting

## Development

### Setup Development Environment

```bash
git clone https://github.com/dotmac-dev/dotmac-framework.git
cd dotmac-framework/packages/dotmac-benchmarking

# Install with development dependencies
pip install -e .[dev,http,db,system]

# Run tests
pytest

# Run linting
ruff check .

# Run type checking  
mypy .
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=dotmac_benchmarking --cov-report=html

# Run only fast tests
pytest -m "not slow"
```

## Security Considerations

- HTTP benchmarking respects rate limits and includes safety timeouts
- Database benchmarking uses parameterized queries to prevent SQL injection
- System monitoring does not log sensitive process information  
- All benchmarks include configurable resource limits to prevent system overload

## License

MIT License - see [LICENSE](../../LICENSE) for details.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and changes.