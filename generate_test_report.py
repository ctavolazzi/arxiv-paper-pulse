#!/usr/bin/env python3
"""
Generate comprehensive test report by running all tests one by one.
"""
import subprocess
import json
from pathlib import Path
from datetime import datetime


def run_all_tests():
    """Run all tests and generate report."""
    print("=" * 80)
    print("TEST REPORT GENERATOR")
    print("=" * 80)
    print()

    # Collect all test files
    test_files = list(Path("tests").glob("test_*.py"))
    print(f"Found {len(test_files)} test files")
    print()

    # Run pytest with verbose output
    print("Running all tests...")
    result = subprocess.run(
        ["python3", "-m", "pytest", "tests/", "-v", "--tb=short", "--json-report", "--json-report-file=test_report.json"],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    # Try to read JSON report if it exists
    report_file = Path("test_report.json")
    if report_file.exists():
        report_data = json.loads(report_file.read_text())
        print()
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {report_data.get('summary', {}).get('total', 'N/A')}")
        print(f"Passed: {report_data.get('summary', {}).get('passed', 'N/A')}")
        print(f"Failed: {report_data.get('summary', {}).get('failed', 'N/A')}")
        print(f"Errors: {report_data.get('summary', {}).get('error', 'N/A')}")
        print()

        if report_data.get('summary', {}).get('failed', 0) > 0:
            print("FAILED TESTS:")
            for test in report_data.get('tests', []):
                if test.get('outcome') == 'failed':
                    print(f"  - {test.get('nodeid')}")
                    print(f"    {test.get('call', {}).get('longrepr', '')[:200]}")
            print()

    return result.returncode


if __name__ == "__main__":
    exit(run_all_tests())

