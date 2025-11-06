#!/usr/bin/env python3
"""
Run all tests one by one and generate a comprehensive report.
"""
import subprocess
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def get_all_tests():
    """Get list of all test files and individual tests."""
    result = subprocess.run(
        ["python3", "-m", "pytest", "tests/", "--collect-only", "-q"],
        capture_output=True,
        text=True
    )

    tests = []
    for line in result.stdout.split('\n'):
        if '::' in line and ('test_' in line or 'Test' in line):
            test_name = line.strip()
            if test_name and not test_name.startswith('<'):
                tests.append(test_name)

    return tests


def run_single_test(test_name):
    """Run a single test and return result."""
    print(f"Running: {test_name}")
    result = subprocess.run(
        ["python3", "-m", "pytest", test_name, "-v", "--tb=line"],
        capture_output=True,
        text=True
    )

    passed = result.returncode == 0
    status = "✅ PASSED" if passed else "❌ FAILED"

    # Extract error message if failed
    error = None
    if not passed:
        # Try to find the error in stderr or stdout
        error_lines = []
        for line in (result.stderr + result.stdout).split('\n'):
            if any(keyword in line.lower() for keyword in ['error', 'failed', 'assertion', 'exception']):
                error_lines.append(line.strip())
                if len(error_lines) >= 3:
                    break
        error = ' | '.join(error_lines[:3])

    return {
        "test": test_name,
        "passed": passed,
        "status": status,
        "error": error
    }


def main():
    """Main function."""
    print("=" * 80)
    print("RUNNING ALL TESTS ONE BY ONE")
    print("=" * 80)
    print()

    # Get all tests
    print("Collecting tests...")
    tests = get_all_tests()
    print(f"Found {len(tests)} tests")
    print()

    # Run each test
    results = []
    passed_count = 0
    failed_count = 0

    for i, test in enumerate(tests, 1):
        print(f"[{i}/{len(tests)}] ", end="")
        result = run_single_test(test)
        results.append(result)

        if result["passed"]:
            passed_count += 1
        else:
            failed_count += 1
            print(f"  ERROR: {result['error']}")

        print(f"  {result['status']}")
        print()

    # Generate summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {len(tests)}")
    print(f"Passed: {passed_count} ✅")
    print(f"Failed: {failed_count} ❌")
    print()

    if failed_count > 0:
        print("FAILED TESTS:")
        for result in results:
            if not result["passed"]:
                print(f"  - {result['test']}")
                if result["error"]:
                    print(f"    {result['error']}")
        print()

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": len(tests),
            "passed": passed_count,
            "failed": failed_count
        },
        "results": results
    }

    report_file = Path("test_report_detailed.json")
    report_file.write_text(json.dumps(report, indent=2))
    print(f"Detailed report saved to: {report_file}")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

