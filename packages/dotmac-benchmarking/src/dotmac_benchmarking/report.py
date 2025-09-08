"""
Benchmark reporting and summary utilities.
"""

import json
import statistics
from typing import Any


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Create a summary report from multiple benchmark results.
    
    Args:
        results: List of benchmark result dictionaries
        
    Returns:
        Dictionary containing summary statistics and comparisons
        
    Example:
        from dotmac_benchmarking import BenchmarkRunner
        from dotmac_benchmarking.report import summarize, to_json
        
        runner = BenchmarkRunner()
        result1 = await runner.run("test1", func1)  
        result2 = await runner.run("test2", func2)
        
        summary = summarize([result1.dict(), result2.dict()])
        print(to_json(summary))
    """
    if not results:
        return {"error": "No results provided"}

    summary = {
        "total_benchmarks": len(results),
        "benchmarks": [],
        "overall_stats": {},
        "comparisons": {}
    }

    all_durations = []

    # Process each result
    for result in results:
        if isinstance(result, dict):
            # Handle dict format (from BenchmarkResult.dict() or raw dict)
            if "avg_duration" in result:
                # BenchmarkResult format
                benchmark_summary = {
                    "label": result.get("label", "unknown"),
                    "samples": result.get("samples", 0),
                    "avg_duration": result.get("avg_duration", 0),
                    "min_duration": result.get("min_duration", 0),
                    "max_duration": result.get("max_duration", 0),
                    "p95_duration": result.get("p95_duration", 0),
                    "timestamp": result.get("timestamp", "")
                }
                all_durations.append(result["avg_duration"])
            else:
                # Generic result format
                duration = result.get("duration", 0)
                benchmark_summary = {
                    "label": result.get("label", result.get("query", "unknown")),
                    "duration": duration,
                    "success": result.get("success", True),
                    "timestamp": result.get("timestamp", "")
                }
                all_durations.append(duration)
        else:
            # Handle BenchmarkResult objects
            benchmark_summary = {
                "label": getattr(result, "label", "unknown"),
                "samples": getattr(result, "samples", 0),
                "avg_duration": getattr(result, "avg_duration", 0),
                "min_duration": getattr(result, "min_duration", 0),
                "max_duration": getattr(result, "max_duration", 0),
                "p95_duration": getattr(result, "p95_duration", 0),
                "timestamp": getattr(result, "timestamp", "")
            }
            all_durations.append(getattr(result, "avg_duration", 0))

        summary["benchmarks"].append(benchmark_summary)

    # Calculate overall statistics
    if all_durations:
        summary["overall_stats"] = {
            "fastest_avg": min(all_durations),
            "slowest_avg": max(all_durations),
            "overall_avg": statistics.mean(all_durations),
            "overall_median": statistics.median(all_durations),
            "overall_stdev": statistics.stdev(all_durations) if len(all_durations) > 1 else 0
        }

        # Generate comparisons (relative to fastest)
        fastest_duration = min(all_durations)
        summary["comparisons"] = {
            "baseline_duration": fastest_duration,
            "relative_performance": []
        }

        for i, benchmark in enumerate(summary["benchmarks"]):
            duration = all_durations[i]
            ratio = duration / fastest_duration if fastest_duration > 0 else 1.0

            summary["comparisons"]["relative_performance"].append({
                "label": benchmark["label"],
                "ratio": ratio,
                "percent_slower": (ratio - 1.0) * 100,
                "is_baseline": duration == fastest_duration
            })

    return summary


def to_json(report: dict[str, Any], *, indent: int = 2) -> str:
    """
    Convert a report dictionary to formatted JSON string.
    
    Args:
        report: Report dictionary (from summarize())
        indent: JSON indentation level
        
    Returns:
        Formatted JSON string
    """
    return json.dumps(report, indent=indent, default=str)


def generate_markdown_report(report: dict[str, Any]) -> str:
    """
    Generate a markdown-formatted report.
    
    Args:
        report: Report dictionary (from summarize())
        
    Returns:
        Markdown-formatted report string
    """
    md = ["# Benchmark Report\n"]

    # Overall stats
    if "overall_stats" in report:
        stats = report["overall_stats"]
        md.append("## Overall Statistics\n")
        md.append(f"- **Total Benchmarks:** {report['total_benchmarks']}")
        md.append(f"- **Fastest Average:** {stats.get('fastest_avg', 0):.4f}s")
        md.append(f"- **Slowest Average:** {stats.get('slowest_avg', 0):.4f}s")
        md.append(f"- **Overall Average:** {stats.get('overall_avg', 0):.4f}s")
        md.append(f"- **Standard Deviation:** {stats.get('overall_stdev', 0):.4f}s\n")

    # Individual benchmarks
    md.append("## Individual Results\n")
    md.append("| Label | Avg Duration | Min | Max | P95 | Samples |")
    md.append("|-------|--------------|-----|-----|-----|---------|")

    for benchmark in report.get("benchmarks", []):
        label = benchmark.get("label", "unknown")
        avg = benchmark.get("avg_duration", benchmark.get("duration", 0))
        min_dur = benchmark.get("min_duration", "N/A")
        max_dur = benchmark.get("max_duration", "N/A")
        p95 = benchmark.get("p95_duration", "N/A")
        samples = benchmark.get("samples", "N/A")

        md.append(f"| {label} | {avg:.4f}s | {min_dur} | {max_dur} | {p95} | {samples} |")

    md.append("")

    # Relative performance
    if "comparisons" in report:
        comps = report["comparisons"]
        md.append("## Relative Performance\n")
        md.append("| Label | Ratio | % Slower | Baseline |")
        md.append("|-------|--------|----------|----------|")

        for perf in comps.get("relative_performance", []):
            label = perf["label"]
            ratio = perf["ratio"]
            percent = perf["percent_slower"]
            baseline = "✓" if perf["is_baseline"] else ""

            md.append(f"| {label} | {ratio:.2f}x | {percent:.1f}% | {baseline} |")

    return "\n".join(md)


def save_report(
    report: dict[str, Any],
    filename: str,
    format: str = "json"
) -> None:
    """
    Save report to file.
    
    Args:
        report: Report dictionary
        filename: Output filename
        format: Output format ("json" or "markdown")
    """
    with open(filename, 'w') as f:
        if format.lower() == "json":
            f.write(to_json(report))
        elif format.lower() in ("md", "markdown"):
            f.write(generate_markdown_report(report))
        else:
            raise ValueError(f"Unsupported format: {format}. Use 'json' or 'markdown'")


def compare_reports(
    report1: dict[str, Any],
    report2: dict[str, Any],
    label1: str = "Report 1",
    label2: str = "Report 2"
) -> dict[str, Any]:
    """
    Compare two benchmark reports.
    
    Args:
        report1: First benchmark report
        report2: Second benchmark report  
        label1: Label for first report
        label2: Label for second report
        
    Returns:
        Comparison report
    """
    comparison = {
        "report1_label": label1,
        "report2_label": label2,
        "comparisons": []
    }

    # Create lookup maps by benchmark label
    benchmarks1 = {b["label"]: b for b in report1.get("benchmarks", [])}
    benchmarks2 = {b["label"]: b for b in report2.get("benchmarks", [])}

    # Compare matching benchmarks
    common_labels = set(benchmarks1.keys()) & set(benchmarks2.keys())

    for label in common_labels:
        b1 = benchmarks1[label]
        b2 = benchmarks2[label]

        duration1 = b1.get("avg_duration", b1.get("duration", 0))
        duration2 = b2.get("avg_duration", b2.get("duration", 0))

        if duration1 > 0:
            ratio = duration2 / duration1
            percent_change = (ratio - 1.0) * 100

            comparison["comparisons"].append({
                "label": label,
                "duration1": duration1,
                "duration2": duration2,
                "ratio": ratio,
                "percent_change": percent_change,
                "is_faster": ratio < 1.0,
                "is_slower": ratio > 1.0
            })

    return comparison
