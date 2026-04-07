"""Main entry point for running source extraction benchmark."""

import asyncio
import sys
from pathlib import Path

# Add benchmark_sources to path
sys.path.insert(0, str(Path(__file__).parent))

from benchmark_sources.benchmark_runner import SourceBenchmark

async def main():
    print("="*60)
    print("SOURCE EXTRACTION BENCHMARK")
    print("="*60)
    print()

    # Initialize benchmark
    benchmark = SourceBenchmark(output_dir="./benchmark_sources/output")

    # Run benchmark with validation loop
    test_cases_file = "./benchmark_sources/test_cases.json"

    print(f"Test cases: {test_cases_file}")
    print(f"Target success rate: 95%")
    print(f"Max iterations: 5")
    print()

    try:
        metrics, report_path = await benchmark.run_benchmark(
            test_cases_file=test_cases_file,
            max_iterations=5,
            target_rate=0.95
        )

        print("\n" + "="*60)
        print("BENCHMARK COMPLETE")
        print("="*60)
        print()
        print(f"📊 Final Metrics:")
        print(f"  Total Tests: {metrics['total_tests']}")
        print(f"  Passed: {metrics['passed']}")
        print(f"  Failed: {metrics['failed']}")
        print(f"  Overall Success Rate: {metrics['overall_success_rate']:.1%}")
        print(f"  Screenshot Success: {metrics['screenshot_success_rate']:.1%}")
        print(f"  Visual Quality: {metrics['visual_quality_score']:.1%}")
        print(f"  URL Validity: {metrics['url_validity']:.1%}")
        print()
        print(f"📁 Outputs:")
        print(f"  Screenshots: ./benchmark_sources/output/screenshots/")
        print(f"  Extracted Data: ./benchmark_sources/output/extracted_data/")
        print(f"  Report: {report_path}")
        print()

        # List all screenshots
        screenshots_dir = Path("./benchmark_sources/output/screenshots")
        if screenshots_dir.exists():
            screenshots = list(screenshots_dir.glob("*.png"))
            if screenshots:
                print(f"📸 {len(screenshots)} Screenshots Captured:")
                for screenshot in sorted(screenshots):
                    print(f"  - {screenshot}")
                print()

        return metrics['overall_success_rate'] >= 0.95

    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
