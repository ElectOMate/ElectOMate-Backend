"""HTML report generator for benchmark results."""

from datetime import datetime
from pathlib import Path

def generate_html_report(results: list, metrics: dict, output_path: str):
    """Generate comprehensive HTML benchmark report."""

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Source Extraction Benchmark Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            margin: 0;
            padding: 24px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            color: #58a6ff;
            font-size: 32px;
            margin-bottom: 8px;
        }}
        .timestamp {{
            color: #8b949e;
            font-size: 14px;
            margin-bottom: 32px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }}
        .metric-card {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 16px;
        }}
        .metric-label {{
            color: #8b949e;
            font-size: 12px;
            text-transform: uppercase;
            margin-bottom: 8px;
        }}
        .metric-value {{
            font-size: 32px;
            font-weight: 700;
        }}
        .metric-value.success {{
            color: #3fb950;
        }}
        .metric-value.warning {{
            color: #d29922;
        }}
        .metric-value.error {{
            color: #f85149;
        }}
        .results-table {{
            width: 100%;
            border-collapse: collapse;
            background: #161b22;
            border-radius: 8px;
            overflow: hidden;
        }}
        .results-table th {{
            background: #1c2128;
            padding: 12px;
            text-align: left;
            color: #8b949e;
            font-size: 12px;
            text-transform: uppercase;
            border-bottom: 1px solid #30363d;
        }}
        .results-table td {{
            padding: 12px;
            border-bottom: 1px solid #21262d;
        }}
        .status-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }}
        .status-pass {{
            background: #238636;
            color: #fff;
        }}
        .status-fail {{
            background: #da3633;
            color: #fff;
        }}
        .screenshot-preview {{
            width: 120px;
            height: 68px;
            object-fit: cover;
            border-radius: 4px;
            border: 1px solid #30363d;
        }}
        .validation-score {{
            display: inline-block;
            width: 60px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Source Extraction Benchmark Report</h1>
        <p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Overall Success Rate</div>
                <div class="metric-value {'success' if metrics['overall_success_rate'] >= 0.95 else 'warning' if metrics['overall_success_rate'] >= 0.80 else 'error'}">
                    {metrics['overall_success_rate']:.1%}
                </div>
            </div>

            <div class="metric-card">
                <div class="metric-label">Tests Passed</div>
                <div class="metric-value success">
                    {metrics['passed']} / {metrics['total_tests']}
                </div>
            </div>

            <div class="metric-card">
                <div class="metric-label">Screenshot Success</div>
                <div class="metric-value {'success' if metrics['screenshot_success_rate'] >= 0.90 else 'warning'}">
                    {metrics['screenshot_success_rate']:.1%}
                </div>
            </div>

            <div class="metric-card">
                <div class="metric-label">Visual Quality</div>
                <div class="metric-value {'success' if metrics['visual_quality_score'] >= 0.80 else 'warning'}">
                    {metrics['visual_quality_score']:.1%}
                </div>
            </div>

            <div class="metric-card">
                <div class="metric-label">URL Validity</div>
                <div class="metric-value {'success' if metrics['url_validity'] >= 0.95 else 'warning'}">
                    {metrics['url_validity']:.1%}
                </div>
            </div>

            <div class="metric-card">
                <div class="metric-label">Data Extraction</div>
                <div class="metric-value {'success' if metrics.get('data_extraction_accuracy', 0) >= 0.80 else 'warning'}">
                    {metrics.get('data_extraction_accuracy', 0):.1%}
                </div>
            </div>
        </div>

        <h2 style="color: #c9d1d9; margin-top: 48px;">Test Results</h2>
        <table class="results-table">
            <thead>
                <tr>
                    <th>Test Case</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Screenshot</th>
                    <th>URL Valid</th>
                    <th>Screenshot Quality</th>
                    <th>Text Accuracy</th>
                </tr>
            </thead>
            <tbody>
"""

    for result in results:
        status_class = "status-pass" if result["passed"] else "status-fail"
        status_text = "PASS" if result["passed"] else "FAIL"

        screenshot_html = ""
        if result.get("screenshot_path") and Path(result["screenshot_path"]).exists():
            screenshot_html = f'<img src="file://{result["screenshot_path"]}" class="screenshot-preview" alt="Screenshot">'
        else:
            screenshot_html = '<span style="color: #8b949e;">No screenshot</span>'

        url_valid = "✓" if result["validations"].get("url_valid", False) else "✗"
        screenshot_quality = f"{result['validations'].get('screenshot_quality', 0):.1%}"
        text_accuracy = f"{result['validations'].get('text_accuracy', 0):.1%}"

        html += f"""
                <tr>
                    <td><strong>{result['name']}</strong></td>
                    <td>{result['type']}</td>
                    <td><span class="status-badge {status_class}">{status_text}</span></td>
                    <td>{screenshot_html}</td>
                    <td class="validation-score">{url_valid}</td>
                    <td class="validation-score">{screenshot_quality}</td>
                    <td class="validation-score">{text_accuracy}</td>
                </tr>
"""

    html += """
            </tbody>
        </table>

        <div style="margin-top: 48px; padding: 16px; background: #161b22; border-radius: 8px; border: 1px solid #30363d;">
            <h3 style="margin-top: 0;">Screenshot Locations</h3>
            <p style="color: #8b949e;">All screenshots saved to:</p>
            <code style="background: #0d1117; padding: 8px 12px; display: block; border-radius: 4px; color: #58a6ff;">
                benchmark_sources/output/screenshots/
            </code>
        </div>
    </div>
</body>
</html>
"""

    with open(output_path, "w") as f:
        f.write(html)

    print(f"  Report generated: {output_path}")
