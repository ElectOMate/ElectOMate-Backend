"""Main benchmark runner for source extraction validation."""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

class SourceBenchmark:
    """Benchmark runner for source extraction with validation loop."""

    def __init__(self, output_dir: str = "./benchmark_sources/output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.screenshots_dir = self.output_dir / "screenshots"
        self.screenshots_dir.mkdir(exist_ok=True)

        self.data_dir = self.output_dir / "extracted_data"
        self.data_dir.mkdir(exist_ok=True)

        self.reports_dir = self.output_dir / "reports"
        self.reports_dir.mkdir(exist_ok=True)

        self.results = []
        self.metrics = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "screenshot_success_rate": 0.0,
            "visual_quality_score": 0.0,
            "data_extraction_accuracy": 0.0,
            "url_validity": 0.0,
            "overall_success_rate": 0.0,
        }

    async def run_benchmark(self, test_cases_file: str, max_iterations: int = 5, target_rate: float = 0.95):
        """Run benchmark with validation loop until target success rate achieved."""
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            print(f"\n{'='*60}")
            print(f"BENCHMARK ITERATION {iteration}/{max_iterations}")
            print(f"{'='*60}\n")

            # Load test cases
            with open(test_cases_file) as f:
                test_cases = json.load(f)

            self.results = []
            self.metrics["total_tests"] = len(test_cases)

            # Run each test case
            for idx, test_case in enumerate(test_cases, 1):
                print(f"\n[{idx}/{len(test_cases)}] Testing: {test_case['name']}")
                result = await self._run_test_case(test_case)
                self.results.append(result)

            # Calculate metrics
            self._calculate_metrics()

            # Generate report
            report_path = self._generate_report(iteration)
            print(f"\n📊 Report generated: {report_path}")

            # Check if target achieved
            if self.metrics["overall_success_rate"] >= target_rate:
                print(f"\n✅ Target success rate achieved: {self.metrics['overall_success_rate']:.1%}")
                break

            # Auto-fix failures before next iteration
            if iteration < max_iterations:
                print(f"\n🔧 Auto-fixing failures...")
                await self._autofix_failures()

        return self.metrics, report_path

    async def _run_test_case(self, test_case: dict) -> dict:
        """Run a single test case."""
        result = {
            "name": test_case["name"],
            "type": test_case["type"],
            "url": test_case.get("url", ""),
            "timestamp": datetime.now().isoformat(),
            "passed": False,
            "screenshot_path": "",
            "extracted_data": {},
            "validations": {},
            "errors": [],
        }

        try:
            # Import here to avoid circular dependencies
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from validators.screenshot_validator import validate_screenshot
            from validators.text_validator import validate_text_extraction
            from validators.url_validator import validate_url

            # Step 1: Validate URL
            result["validations"]["url_valid"] = validate_url(test_case.get("url", ""))

            # Step 2: Capture screenshot
            if test_case["type"] in ["news", "government", "wikipedia", "academic"]:
                screenshot_path = await self._capture_screenshot(test_case)
                result["screenshot_path"] = str(screenshot_path)
                result["validations"]["screenshot_captured"] = Path(screenshot_path).exists()

                # Validate screenshot quality
                if result["validations"]["screenshot_captured"]:
                    result["validations"]["screenshot_quality"] = validate_screenshot(screenshot_path)

            # Step 3: Extract data
            extracted_data = await self._extract_data(test_case)
            result["extracted_data"] = extracted_data

            # Step 4: Validate extraction
            if "expected_text" in test_case:
                result["validations"]["text_accuracy"] = validate_text_extraction(
                    extracted_data.get("text", ""),
                    test_case["expected_text"]
                )

            # Overall pass/fail
            result["passed"] = all(result["validations"].values())

        except Exception as e:
            result["errors"].append(str(e))
            result["passed"] = False

        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"  {status} - {result['name']}")

        return result

    async def _capture_screenshot(self, test_case: dict) -> str:
        """Capture screenshot using BrowserUse with intelligent content detection."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from browseruse_capture import capture_with_intelligent_fallback

        output_filename = f"{test_case['name'].lower().replace(' ', '_')}.png"
        output_path = str(self.screenshots_dir / output_filename)

        # Use BrowserUse for intelligent capture
        capture_result = await capture_with_intelligent_fallback(test_case["url"], output_path)

        # Store additional metadata about capture quality
        test_case["_capture_result"] = capture_result

        return output_path

    async def _extract_data(self, test_case: dict) -> dict:
        """Extract data from source."""
        # For now, just return placeholder
        # In full implementation, this would extract text from screenshot or page
        return {"text": test_case.get("url", ""), "metadata": {}}

    def _calculate_metrics(self):
        """Calculate benchmark metrics."""
        if not self.results:
            return

        passed = sum(1 for r in self.results if r["passed"])
        self.metrics["passed"] = passed
        self.metrics["failed"] = len(self.results) - passed

        # Screenshot success rate
        screenshot_captured = sum(1 for r in self.results if r["validations"].get("screenshot_captured", False))
        self.metrics["screenshot_success_rate"] = screenshot_captured / len(self.results) if self.results else 0

        # Visual quality score
        screenshot_quality = sum(r["validations"].get("screenshot_quality", 0) for r in self.results)
        self.metrics["visual_quality_score"] = screenshot_quality / len(self.results) if self.results else 0

        # URL validity
        url_valid = sum(1 for r in self.results if r["validations"].get("url_valid", False))
        self.metrics["url_validity"] = url_valid / len(self.results) if self.results else 0

        # Overall success rate
        self.metrics["overall_success_rate"] = passed / len(self.results) if self.results else 0

    def _generate_report(self, iteration: int) -> str:
        """Generate HTML benchmark report."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from reporting.report_generator import generate_html_report

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.reports_dir / f"benchmark_iteration_{iteration}_{timestamp}.html"

        generate_html_report(self.results, self.metrics, str(report_path))
        return str(report_path)

    async def _autofix_failures(self):
        """Auto-fix failed test cases."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from autofix.retry_engine import retry_with_fallbacks

        failed_cases = [r for r in self.results if not r["passed"]]
        print(f"  Found {len(failed_cases)} failures to fix")

        for result in failed_cases:
            await retry_with_fallbacks(result)


if __name__ == "__main__":
    benchmark = SourceBenchmark()
    asyncio.run(benchmark.run_benchmark("test_cases.json"))
