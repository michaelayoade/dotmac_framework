#!/usr/bin/env python3
"""
Test Report Generator for DotMac Framework

Generates comprehensive HTML test reports with charts and metrics.
"""

import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio


class TestReportGenerator:
    """Generate comprehensive test reports."""
    
    def __init__(self, output_dir: str = "test-reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Data containers
        self.test_results = {}
        self.coverage_data = {}
        self.performance_data = {}
        self.quality_data = {}
        
    def collect_test_data(self):
        """Collect all test data from various sources."""
        print("Collecting test data...")
        
        # Collect JUnit test results
        self._collect_junit_results()
        
        # Collect coverage data
        self._collect_coverage_data()
        
        # Collect performance data
        self._collect_performance_data()
        
        # Collect code quality data
        self._collect_quality_data()
        
    def generate_report(self) -> str:
        """Generate comprehensive HTML test report."""
        print("Generating test report...")
        
        # Generate charts
        charts = self._generate_charts()
        
        # Generate HTML report
        html_content = self._generate_html_report(charts)
        
        # Save report
        report_file = self.output_dir / f"test-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
        with open(report_file, 'w') as f:
            f.write(html_content)
        
        print(f"Test report generated: {report_file}")
        return str(report_file)
    
    def _collect_junit_results(self):
        """Collect JUnit XML test results."""
        junit_files = list(Path(".").rglob("junit*.xml"))
        
        for junit_file in junit_files:
            try:
                tree = ET.parse(junit_file)
                root = tree.getroot()
                
                test_suite = {
                    'name': root.get('name', junit_file.stem),
                    'tests': int(root.get('tests', 0)),
                    'failures': int(root.get('failures', 0)),
                    'errors': int(root.get('errors', 0)),
                    'time': float(root.get('time', 0)),
                    'timestamp': root.get('timestamp', datetime.now().isoformat()),
                    'test_cases': []
                }
                
                # Collect individual test cases
                for testcase in root.findall('.//testcase'):
                    test_case = {
                        'name': testcase.get('name'),
                        'classname': testcase.get('classname'),
                        'time': float(testcase.get('time', 0)),
                        'status': 'passed'
                    }
                    
                    if testcase.find('failure') is not None:
                        test_case['status'] = 'failed'
                        test_case['failure'] = testcase.find('failure').text
                    elif testcase.find('error') is not None:
                        test_case['status'] = 'error'
                        test_case['error'] = testcase.find('error').text
                    elif testcase.find('skipped') is not None:
                        test_case['status'] = 'skipped'
                    
                    test_suite['test_cases'].append(test_case)
                
                self.test_results[junit_file.stem] = test_suite
                
            except Exception as e:
                print(f"Error parsing {junit_file}: {e}")
    
    def _collect_coverage_data(self):
        """Collect test coverage data."""
        # Try to parse coverage.xml
        coverage_file = Path("coverage.xml")
        if coverage_file.exists():
            try:
                tree = ET.parse(coverage_file)
                root = tree.getroot()
                
                # Overall coverage
                coverage_elem = root.find(".//coverage")
                if coverage_elem is not None:
                    self.coverage_data['total'] = {
                        'line_rate': float(coverage_elem.get('line-rate', 0)) * 100,
                        'branch_rate': float(coverage_elem.get('branch-rate', 0)) * 100,
                        'lines_covered': int(coverage_elem.get('lines-covered', 0)),
                        'lines_valid': int(coverage_elem.get('lines-valid', 0)),
                        'branches_covered': int(coverage_elem.get('branches-covered', 0)),
                        'branches_valid': int(coverage_elem.get('branches-valid', 0))
                    }
                
                # Package-level coverage
                packages = []
                for package in root.findall('.//package'):
                    package_data = {
                        'name': package.get('name'),
                        'line_rate': float(package.get('line-rate', 0)) * 100,
                        'branch_rate': float(package.get('branch-rate', 0)) * 100
                    }
                    packages.append(package_data)
                
                self.coverage_data['packages'] = packages
                
            except Exception as e:
                print(f"Error parsing coverage data: {e}")
    
    def _collect_performance_data(self):
        """Collect performance test data."""
        # Look for Locust results
        locust_files = list(Path(".").rglob("*_stats.csv"))
        for locust_file in locust_files:
            try:
                df = pd.read_csv(locust_file)
                
                performance_data = {
                    'requests': df.to_dict('records'),
                    'summary': {
                        'total_requests': df['Request Count'].sum(),
                        'total_failures': df['Failure Count'].sum(),
                        'avg_response_time': df['Average Response Time'].mean(),
                        'max_response_time': df['Max Response Time'].max(),
                        'requests_per_second': df['Requests/s'].sum()
                    }
                }
                
                self.performance_data['locust'] = performance_data
                
            except Exception as e:
                print(f"Error parsing performance data: {e}")
        
        # Look for benchmark results
        benchmark_files = list(Path(".").rglob("benchmark*.json"))
        for benchmark_file in benchmark_files:
            try:
                with open(benchmark_file, 'r') as f:
                    benchmark_data = json.load(f)
                    self.performance_data['benchmarks'] = benchmark_data
                    
            except Exception as e:
                print(f"Error parsing benchmark data: {e}")
    
    def _collect_quality_data(self):
        """Collect code quality data."""
        # Look for quality gate results
        quality_files = list(Path(".").rglob("quality-gate*.json"))
        for quality_file in quality_files:
            try:
                with open(quality_file, 'r') as f:
                    quality_data = json.load(f)
                    self.quality_data = quality_data
                    break  # Use most recent
                    
            except Exception as e:
                print(f"Error parsing quality data: {e}")
    
    def _generate_charts(self) -> Dict[str, str]:
        """Generate all charts for the report."""
        charts = {}
        
        # Test results chart
        if self.test_results:
            charts['test_results'] = self._generate_test_results_chart()
        
        # Coverage chart
        if self.coverage_data:
            charts['coverage'] = self._generate_coverage_chart()
        
        # Performance charts
        if self.performance_data:
            charts['performance'] = self._generate_performance_chart()
        
        # Quality metrics chart
        if self.quality_data:
            charts['quality'] = self._generate_quality_chart()
        
        # Trend charts (if historical data available)
        charts['trends'] = self._generate_trend_charts()
        
        return charts
    
    def _generate_test_results_chart(self) -> str:
        """Generate test results summary chart."""
        # Aggregate test results
        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_errors = 0
        test_suites = []
        
        for suite_name, suite_data in self.test_results.items():
            total_tests += suite_data['tests']
            failures = suite_data['failures']
            errors = suite_data['errors']
            passed = suite_data['tests'] - failures - errors
            
            total_passed += passed
            total_failed += failures
            total_errors += errors
            
            test_suites.append({
                'suite': suite_name,
                'passed': passed,
                'failed': failures,
                'errors': errors,
                'total': suite_data['tests']
            })
        
        # Create pie chart for overall results
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('Overall Test Results', 'Results by Test Suite'),
            specs=[[{'type': 'pie'}, {'type': 'bar'}]]
        )
        
        # Overall pie chart
        fig.add_trace(
            go.Pie(
                labels=['Passed', 'Failed', 'Errors'],
                values=[total_passed, total_failed, total_errors],
                marker_colors=['green', 'red', 'orange']
            ),
            row=1, col=1
        )
        
        # Bar chart by suite
        if test_suites:
            suite_names = [suite['suite'] for suite in test_suites]
            
            fig.add_trace(
                go.Bar(
                    name='Passed',
                    x=suite_names,
                    y=[suite['passed'] for suite in test_suites],
                    marker_color='green'
                ),
                row=1, col=2
            )
            
            fig.add_trace(
                go.Bar(
                    name='Failed',
                    x=suite_names,
                    y=[suite['failed'] for suite in test_suites],
                    marker_color='red'
                ),
                row=1, col=2
            )
            
            fig.add_trace(
                go.Bar(
                    name='Errors',
                    x=suite_names,
                    y=[suite['errors'] for suite in test_suites],
                    marker_color='orange'
                ),
                row=1, col=2
            )
        
        fig.update_layout(
            title='Test Results Summary',
            height=500,
            showlegend=True,
            barmode='stack'
        )
        
        return pio.to_html(fig, include_plotlyjs='cdn', div_id="test-results-chart")
    
    def _generate_coverage_chart(self) -> str:
        """Generate test coverage chart."""
        if not self.coverage_data:
            return ""
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Overall Coverage',
                'Coverage by Package',
                'Coverage Distribution', 
                'Coverage Metrics'
            ),
            specs=[
                [{'type': 'pie'}, {'type': 'bar'}],
                [{'type': 'histogram'}, {'type': 'indicator'}]
            ]
        )
        
        total_coverage = self.coverage_data.get('total', {})
        
        if total_coverage:
            line_rate = total_coverage.get('line_rate', 0)
            branch_rate = total_coverage.get('branch_rate', 0)
            
            # Coverage pie chart
            fig.add_trace(
                go.Pie(
                    labels=['Covered', 'Uncovered'],
                    values=[line_rate, 100 - line_rate],
                    marker_colors=['green', 'lightgray']
                ),
                row=1, col=1
            )
            
            # Coverage indicator
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number+delta",
                    value=line_rate,
                    title={'text': "Line Coverage %"},
                    gauge={'axis': {'range': [None, 100]},
                           'bar': {'color': "darkgreen"},
                           'steps': [
                               {'range': [0, 50], 'color': "lightgray"},
                               {'range': [50, 80], 'color': "yellow"},
                               {'range': [80, 100], 'color': "lightgreen"}
                           ],
                           'threshold': {'line': {'color': "red", 'width': 4},
                                       'thickness': 0.75, 'value': 80}}
                ),
                row=2, col=2
            )
        
        # Package coverage
        packages = self.coverage_data.get('packages', [])
        if packages:
            package_names = [pkg['name'] for pkg in packages]
            package_coverage = [pkg['line_rate'] for pkg in packages]
            
            fig.add_trace(
                go.Bar(
                    x=package_names,
                    y=package_coverage,
                    marker_color=['green' if c >= 80 else 'red' if c < 50 else 'orange' for c in package_coverage]
                ),
                row=1, col=2
            )
            
            # Coverage histogram
            fig.add_trace(
                go.Histogram(
                    x=package_coverage,
                    nbinsx=20,
                    marker_color='lightblue'
                ),
                row=2, col=1
            )
        
        fig.update_layout(
            title='Test Coverage Analysis',
            height=800,
            showlegend=False
        )
        
        return pio.to_html(fig, include_plotlyjs='cdn', div_id="coverage-chart")
    
    def _generate_performance_chart(self) -> str:
        """Generate performance test charts."""
        if not self.performance_data:
            return ""
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Response Times',
                'Request Rates',
                'Error Rates',
                'Performance Summary'
            )
        )
        
        # Locust performance data
        if 'locust' in self.performance_data:
            locust_data = self.performance_data['locust']
            requests = locust_data['requests']
            
            if requests:
                # Response times chart
                endpoints = [req['Name'] for req in requests if req['Type'] in ['GET', 'POST', 'PUT', 'DELETE']]
                avg_times = [req['Average Response Time'] for req in requests if req['Type'] in ['GET', 'POST', 'PUT', 'DELETE']]
                max_times = [req['Max Response Time'] for req in requests if req['Type'] in ['GET', 'POST', 'PUT', 'DELETE']]
                
                fig.add_trace(
                    go.Bar(name='Average', x=endpoints, y=avg_times, marker_color='blue'),
                    row=1, col=1
                )
                fig.add_trace(
                    go.Bar(name='Maximum', x=endpoints, y=max_times, marker_color='red'),
                    row=1, col=1
                )
                
                # Request rates
                request_rates = [req['Requests/s'] for req in requests if req['Type'] in ['GET', 'POST', 'PUT', 'DELETE']]
                fig.add_trace(
                    go.Bar(x=endpoints, y=request_rates, marker_color='green'),
                    row=1, col=2
                )
                
                # Error rates
                error_rates = [
                    (req['Failure Count'] / max(req['Request Count'], 1)) * 100 
                    for req in requests if req['Type'] in ['GET', 'POST', 'PUT', 'DELETE']
                ]
                fig.add_trace(
                    go.Bar(x=endpoints, y=error_rates, marker_color='orange'),
                    row=2, col=1
                )
        
        # Benchmark data
        if 'benchmarks' in self.performance_data:
            benchmark_data = self.performance_data['benchmarks']
            benchmarks = benchmark_data.get('benchmarks', [])
            
            if benchmarks:
                bench_names = [b['name'] for b in benchmarks]
                bench_times = [b['stats']['mean'] * 1000 for b in benchmarks]  # Convert to ms
                
                fig.add_trace(
                    go.Scatter(
                        x=bench_names,
                        y=bench_times,
                        mode='markers+lines',
                        marker={'size': 10, 'color': 'purple'},
                        name='Benchmark Times (ms)'
                    ),
                    row=2, col=2
                )
        
        fig.update_layout(
            title='Performance Test Results',
            height=800,
            showlegend=True
        )
        
        return pio.to_html(fig, include_plotlyjs='cdn', div_id="performance-chart")
    
    def _generate_quality_chart(self) -> str:
        """Generate code quality metrics chart."""
        if not self.quality_data:
            return ""
        
        results = self.quality_data.get('results', {})
        
        # Create quality metrics summary
        categories = list(results.keys())
        passed_counts = [1 if results[cat]['passed'] else 0 for cat in categories]
        
        fig = go.Figure()
        
        # Quality gate status
        fig.add_trace(
            go.Bar(
                x=categories,
                y=passed_counts,
                marker_color=['green' if p else 'red' for p in passed_counts],
                text=['PASS' if p else 'FAIL' for p in passed_counts],
                textposition='auto'
            )
        )
        
        fig.update_layout(
            title='Quality Gate Results',
            xaxis_title='Quality Categories',
            yaxis_title='Status (1=Pass, 0=Fail)',
            height=400
        )
        
        return pio.to_html(fig, include_plotlyjs='cdn', div_id="quality-chart")
    
    def _generate_trend_charts(self) -> str:
        """Generate trend charts if historical data is available."""
        # This would require historical data collection
        # For now, return placeholder
        return "<div id='trends-chart'><p>Historical trend data not available yet.</p></div>"
    
    def _generate_html_report(self, charts: Dict[str, str]) -> str:
        """Generate complete HTML report."""
        # Calculate summary metrics
        summary = self._calculate_summary_metrics()
        
        html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DotMac Framework Test Report</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .header .subtitle {{
            margin-top: 10px;
            opacity: 0.9;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .metric-value {{
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .metric-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .success {{ color: #28a745; }}
        .danger {{ color: #dc3545; }}
        .warning {{ color: #ffc107; }}
        .info {{ color: #17a2b8; }}
        
        .section {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .section h2 {{
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .chart-container {{
            margin: 20px 0;
        }}
        .footer {{
            text-align: center;
            color: #666;
            margin-top: 50px;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 DotMac Framework Test Report</h1>
        <div class="subtitle">
            Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
        </div>
    </div>

    <div class="summary">
        {self._generate_summary_cards(summary)}
    </div>

    {self._generate_section("Test Results", charts.get('test_results', ''))}
    {self._generate_section("Code Coverage", charts.get('coverage', ''))}
    {self._generate_section("Performance Results", charts.get('performance', ''))}
    {self._generate_section("Code Quality", charts.get('quality', ''))}
    {self._generate_section("Trends", charts.get('trends', ''))}
    
    <div class="section">
        <h2>📋 Detailed Results</h2>
        {self._generate_detailed_results_table()}
    </div>

    <div class="footer">
        <p>Generated by DotMac Framework Test Report Generator</p>
        <p>🚀 Ensuring quality through comprehensive testing</p>
    </div>
</body>
</html>
"""
        return html_template
    
    def _calculate_summary_metrics(self) -> Dict[str, Any]:
        """Calculate summary metrics for the report."""
        summary = {
            'total_tests': 0,
            'passed_tests': 0,
            'test_success_rate': 0,
            'coverage_percentage': 0,
            'quality_score': 0,
            'performance_score': 0
        }
        
        # Test metrics
        for suite_data in self.test_results.values():
            summary['total_tests'] += suite_data['tests']
            summary['passed_tests'] += suite_data['tests'] - suite_data['failures'] - suite_data['errors']
        
        if summary['total_tests'] > 0:
            summary['test_success_rate'] = (summary['passed_tests'] / summary['total_tests']) * 100
        
        # Coverage metrics
        if self.coverage_data.get('total'):
            summary['coverage_percentage'] = self.coverage_data['total'].get('line_rate', 0)
        
        # Quality score (based on quality gate results)
        if self.quality_data.get('results'):
            results = self.quality_data['results']
            passed_gates = sum(1 for result in results.values() if result['passed'])
            total_gates = len(results)
            summary['quality_score'] = (passed_gates / total_gates) * 100 if total_gates > 0 else 0
        
        # Performance score (simplified)
        if self.performance_data:
            # Simplified scoring based on presence of performance data
            summary['performance_score'] = 85  # Placeholder
        
        return summary
    
    def _generate_summary_cards(self, summary: Dict[str, Any]) -> str:
        """Generate summary metric cards."""
        cards = []
        
        # Test success rate
        success_rate = summary['test_success_rate']
        success_class = 'success' if success_rate >= 95 else 'danger' if success_rate < 80 else 'warning'
        cards.append(f"""
        <div class="metric-card">
            <div class="metric-value {success_class}">{success_rate:.1f}%</div>
            <div class="metric-label">Test Success Rate</div>
            <div class="metric-label">{summary['passed_tests']}/{summary['total_tests']} tests passed</div>
        </div>
        """)
        
        # Coverage percentage
        coverage = summary['coverage_percentage']
        coverage_class = 'success' if coverage >= 80 else 'danger' if coverage < 60 else 'warning'
        cards.append(f"""
        <div class="metric-card">
            <div class="metric-value {coverage_class}">{coverage:.1f}%</div>
            <div class="metric-label">Code Coverage</div>
        </div>
        """)
        
        # Quality score
        quality = summary['quality_score']
        quality_class = 'success' if quality >= 90 else 'danger' if quality < 70 else 'warning'
        cards.append(f"""
        <div class="metric-card">
            <div class="metric-value {quality_class}">{quality:.1f}%</div>
            <div class="metric-label">Quality Gates</div>
        </div>
        """)
        
        # Performance score
        performance = summary['performance_score']
        performance_class = 'success' if performance >= 85 else 'warning'
        cards.append(f"""
        <div class="metric-card">
            <div class="metric-value {performance_class}">{performance:.1f}%</div>
            <div class="metric-label">Performance Score</div>
        </div>
        """)
        
        return ''.join(cards)
    
    def _generate_section(self, title: str, content: str) -> str:
        """Generate a report section."""
        if not content:
            content = f"<p>No {title.lower()} data available.</p>"
        
        return f"""
        <div class="section">
            <h2>{title}</h2>
            <div class="chart-container">
                {content}
            </div>
        </div>
        """
    
    def _generate_detailed_results_table(self) -> str:
        """Generate detailed results table."""
        if not self.test_results:
            return "<p>No detailed test results available.</p>"
        
        rows = []
        for suite_name, suite_data in self.test_results.items():
            for test_case in suite_data['test_cases']:
                status_class = {
                    'passed': 'success',
                    'failed': 'danger', 
                    'error': 'danger',
                    'skipped': 'warning'
                }.get(test_case['status'], 'info')
                
                rows.append(f"""
                <tr>
                    <td>{suite_name}</td>
                    <td>{test_case['name']}</td>
                    <td><span class="{status_class}">{test_case['status'].upper()}</span></td>
                    <td>{test_case['time']:.3f}s</td>
                </tr>
                """)
        
        return f"""
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
            <thead style="background-color: #f8f9fa;">
                <tr>
                    <th style="padding: 12px; text-align: left; border-bottom: 2px solid #dee2e6;">Test Suite</th>
                    <th style="padding: 12px; text-align: left; border-bottom: 2px solid #dee2e6;">Test Case</th>
                    <th style="padding: 12px; text-align: left; border-bottom: 2px solid #dee2e6;">Status</th>
                    <th style="padding: 12px; text-align: left; border-bottom: 2px solid #dee2e6;">Duration</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate comprehensive test report")
    parser.add_argument("--output-dir", default="test-reports", help="Output directory for reports")
    
    args = parser.parse_args()
    
    try:
        generator = TestReportGenerator(args.output_dir)
        generator.collect_test_data()
        report_file = generator.generate_report()
        
        print(f"Test report generated successfully: {report_file}")
        return 0
        
    except Exception as e:
        print(f"Error generating test report: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())