"""
Tests for reporting functionality.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from dotmac_benchmarking.report import compare_reports, generate_markdown_report, save_report, summarize, to_json


class TestReportFunctions:
    """Test reporting functions."""

    def test_summarize_empty(self):
        """Test summarizing empty results."""
        summary = summarize([])
        assert "error" in summary
        assert summary["error"] == "No results provided"

    def test_summarize_benchmark_results(self):
        """Test summarizing BenchmarkResult-style dicts."""
        results = [
            {
                "label": "test1",
                "samples": 3,
                "avg_duration": 0.1,
                "min_duration": 0.09,
                "max_duration": 0.11,
                "p95_duration": 0.105,
                "timestamp": "2025-01-06T10:00:00Z"
            },
            {
                "label": "test2",
                "samples": 3,
                "avg_duration": 0.2,
                "min_duration": 0.18,
                "max_duration": 0.22,
                "p95_duration": 0.21,
                "timestamp": "2025-01-06T10:01:00Z"
            }
        ]

        summary = summarize(results)

        assert summary["total_benchmarks"] == 2
        assert len(summary["benchmarks"]) == 2

        # Check overall stats
        stats = summary["overall_stats"]
        assert stats["fastest_avg"] == 0.1
        assert stats["slowest_avg"] == 0.2
        assert stats["overall_avg"] == pytest.approx(0.15, abs=0.01)
        assert stats["overall_median"] == pytest.approx(0.15, abs=0.01)

        # Check comparisons
        comparisons = summary["comparisons"]
        assert comparisons["baseline_duration"] == 0.1
        assert len(comparisons["relative_performance"]) == 2

        fast_comp = next(c for c in comparisons["relative_performance"] if c["label"] == "test1")
        slow_comp = next(c for c in comparisons["relative_performance"] if c["label"] == "test2")

        assert fast_comp["ratio"] == 1.0
        assert fast_comp["percent_slower"] == 0.0
        assert fast_comp["is_baseline"] is True

        assert slow_comp["ratio"] == 2.0
        assert slow_comp["percent_slower"] == 100.0
        assert slow_comp["is_baseline"] is False

    def test_summarize_generic_results(self):
        """Test summarizing generic result dicts."""
        results = [
            {
                "label": "query1",
                "duration": 0.05,
                "success": True,
                "timestamp": "2025-01-06T10:00:00Z"
            },
            {
                "query": "SELECT * FROM users",
                "duration": 0.1,
                "success": True,
                "timestamp": "2025-01-06T10:01:00Z"
            }
        ]

        summary = summarize(results)

        assert summary["total_benchmarks"] == 2
        assert len(summary["benchmarks"]) == 2

        # Should handle different label fields
        labels = {b["label"] for b in summary["benchmarks"]}
        assert "query1" in labels
        assert "SELECT * FROM users" in labels

    def test_to_json(self):
        """Test JSON serialization."""
        report = {"test": "data", "number": 42}
        json_str = to_json(report)

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed == report

        # Should be formatted with indentation
        assert "\n" in json_str
        assert "  " in json_str

    def test_to_json_custom_indent(self):
        """Test JSON with custom indentation."""
        report = {"nested": {"data": "value"}}
        json_str = to_json(report, indent=4)

        # Should use 4-space indentation
        lines = json_str.split('\n')
        assert any('    "data"' in line for line in lines)

    def test_generate_markdown_report(self):
        """Test markdown report generation."""
        report = {
            "total_benchmarks": 2,
            "overall_stats": {
                "fastest_avg": 0.1,
                "slowest_avg": 0.2,
                "overall_avg": 0.15,
                "overall_stdev": 0.05
            },
            "benchmarks": [
                {
                    "label": "test1",
                    "avg_duration": 0.1,
                    "min_duration": 0.09,
                    "max_duration": 0.11,
                    "p95_duration": 0.105,
                    "samples": 5
                }
            ],
            "comparisons": {
                "baseline_duration": 0.1,
                "relative_performance": [
                    {
                        "label": "test1",
                        "ratio": 1.0,
                        "percent_slower": 0.0,
                        "is_baseline": True
                    }
                ]
            }
        }

        markdown = generate_markdown_report(report)

        # Should contain expected sections
        assert "# Benchmark Report" in markdown
        assert "## Overall Statistics" in markdown
        assert "## Individual Results" in markdown
        assert "## Relative Performance" in markdown

        # Should contain specific data
        assert "**Total Benchmarks:** 2" in markdown
        assert "0.1000s" in markdown
        assert "test1" in markdown

    def test_compare_reports(self):
        """Test comparing two reports."""
        report1 = {
            "benchmarks": [
                {"label": "shared_test", "avg_duration": 0.1},
                {"label": "unique1", "avg_duration": 0.2}
            ]
        }

        report2 = {
            "benchmarks": [
                {"label": "shared_test", "avg_duration": 0.15},
                {"label": "unique2", "avg_duration": 0.3}
            ]
        }

        comparison = compare_reports(report1, report2, "Before", "After")

        assert comparison["report1_label"] == "Before"
        assert comparison["report2_label"] == "After"
        assert len(comparison["comparisons"]) == 1

        shared_comp = comparison["comparisons"][0]
        assert shared_comp["label"] == "shared_test"
        assert shared_comp["duration1"] == 0.1
        assert shared_comp["duration2"] == 0.15
        assert shared_comp["ratio"] == pytest.approx(1.5, abs=0.01)
        assert shared_comp["percent_change"] == pytest.approx(50.0, abs=0.01)
        assert shared_comp["is_faster"] is False
        assert shared_comp["is_slower"] is True

    def test_summarize_benchmark_result_objects(self):
        """Test summarizing actual BenchmarkResult objects."""
        # Create mock BenchmarkResult objects
        result1 = MagicMock()
        result1.label = "obj_test1"
        result1.samples = 5
        result1.avg_duration = 0.2
        result1.min_duration = 0.18
        result1.max_duration = 0.22
        result1.p95_duration = 0.21
        result1.timestamp = "2025-01-06T10:00:00Z"

        result2 = MagicMock()
        result2.label = "obj_test2"  
        result2.samples = 3
        result2.avg_duration = 0.1
        result2.min_duration = 0.09
        result2.max_duration = 0.11
        result2.p95_duration = 0.105
        result2.timestamp = "2025-01-06T10:01:00Z"

        summary = summarize([result1, result2])

        assert summary["total_benchmarks"] == 2
        assert len(summary["benchmarks"]) == 2

        # Check that object attributes were accessed correctly
        benchmarks = {b["label"]: b for b in summary["benchmarks"]}
        assert "obj_test1" in benchmarks
        assert "obj_test2" in benchmarks
        
        assert benchmarks["obj_test1"]["samples"] == 5
        assert benchmarks["obj_test1"]["avg_duration"] == 0.2
        assert benchmarks["obj_test2"]["samples"] == 3
        assert benchmarks["obj_test2"]["avg_duration"] == 0.1

    def test_save_report_json(self):
        """Test saving report as JSON."""
        report = {"test": "data", "benchmarks": []}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name

        try:
            save_report(report, temp_path, "json")
            
            # Verify file was created and contains correct JSON
            with open(temp_path, 'r') as f:
                content = f.read()
                loaded = json.loads(content)
                assert loaded == report
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_save_report_markdown(self):
        """Test saving report as markdown."""
        report = {
            "total_benchmarks": 1,
            "overall_stats": {"fastest_avg": 0.1},
            "benchmarks": [],
            "comparisons": {"relative_performance": []}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
            temp_path = f.name

        try:
            save_report(report, temp_path, "markdown")
            
            # Verify file was created and contains markdown
            with open(temp_path, 'r') as f:
                content = f.read()
                assert "# Benchmark Report" in content
                assert "## Overall Statistics" in content
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_save_report_invalid_format(self):
        """Test saving with invalid format raises error."""
        report = {"test": "data"}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Unsupported format: xml"):
                save_report(report, temp_path, "xml")
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_compare_reports_zero_duration_handling(self):
        """Test comparison handling when first report has zero duration."""
        report1 = {
            "benchmarks": [
                {"label": "zero_test", "avg_duration": 0.0},
            ]
        }

        report2 = {
            "benchmarks": [
                {"label": "zero_test", "avg_duration": 0.1},
            ]
        }

        comparison = compare_reports(report1, report2)
        
        # Should handle zero duration gracefully (no division by zero)
        assert len(comparison["comparisons"]) == 0  # Skipped due to zero duration

    def test_compare_reports_with_generic_duration_field(self):
        """Test comparison using 'duration' field instead of 'avg_duration'."""
        report1 = {
            "benchmarks": [
                {"label": "generic_test", "duration": 0.2},
            ]
        }

        report2 = {
            "benchmarks": [
                {"label": "generic_test", "duration": 0.1},
            ]
        }

        comparison = compare_reports(report1, report2)
        
        assert len(comparison["comparisons"]) == 1
        comp = comparison["comparisons"][0]
        assert comp["duration1"] == 0.2
        assert comp["duration2"] == 0.1
        assert comp["ratio"] == 0.5
        assert comp["is_faster"] is True
        assert comp["is_slower"] is False
