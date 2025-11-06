#!/usr/bin/env python3
"""
Run all tests one by one and generate a comprehensive report.
"""
import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def run_test(test_path):
    """Run a single test and return result."""
    result = subprocess.run(
        ["python3", "-m", "pytest", test_path, "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    return {
        "test": test_path,
        "passed": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    }


def collect_all_tests():
    """Collect all test files and individual tests."""
    result = subprocess.run(
        ["python3", "-m", "pytest", "tests/", "--collect-only", "-q"],
        capture_output=True,
        text=True
    )
    
    tests = []
    for line in result.stdout.split('\n'):
        if '::' in line and 'test_' in line:
            tests.append(line.strip())
    return tests


def generate_report(results):
    """Generate a comprehensive test report."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r["passed"]),
            "failed": sum(1 for r in results if not r["passed"])
        },
        "results": results,
        "by_status": {
            "passed": [r["test"] for r in results if r["passed"]],
            "failed": [r["test"] for r in results if not r["passed"]]
        }
    }
    
    return report


def main():
    """Main function to run all tests and generate report."""
    print("=" * 80)
    print("Running All Tests One By One")
    print("=" * 80)
    print()
    
    # Collect all tests
    print("Collecting all tests...")
    tests = collect_all_tests()
    print(f"Found {len(tests)} tests")
    print()
    
    # Run each test
    results = []
    for i, test in enumerate(tests, 1):
        print(f"[{i}/{len(tests)}] Running: {test}")
        result = run_test(test)
        results.append(result)
        
        status = "✅ PASSED" if result["passed"] else "❌ FAILED"
        print(f"  {status}")
        if not result["passed"]:
            # Show first few lines of error
            error_lines = result["stderr"].split('\n')[:5]
            for line in error_lines:
                if line.strip():
                    print(f"    {line}")
        print()
    
    # Generate report
    report = generate_report(results)
    
    # Save report
    report_file = Path("test_report.json")
    report_file.write_text(json.dumps(report, indent=2))
    
    # Print summary
    print("=" * 80)
    print("TEST REPORT SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {report['summary']['total']}")
    print(f"Passed: {report['summary']['passed']} ✅")
    print(f"Failed: {report['summary']['failed']} ❌")
    print()
    print(f"Report saved to: {report_file}")
    print()
    
    if report['summary']['failed'] > 0:
        print("FAILED TESTS:")
        for test in report['by_status']['failed']:
            print(f"  - {test}")
        print()
    
    return 0 if report['summary']['failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())


