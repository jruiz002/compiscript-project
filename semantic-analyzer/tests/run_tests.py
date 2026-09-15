#!/usr/bin/env python3
# tests/run_tests.py
"""
Compiscript Test Harness.

Runs all test files in tests/success/ and tests/failure/
and reports pass/fail status.

Usage:
  python tests/run_tests.py
  python tests/run_tests.py --verbose
  python tests/run_tests.py --filter test_arithmetic
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import List, Optional

# Ensure project root is on the path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "compiler", "generated"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "compiler", "generated", "compiler"))


# -----------------------------------------------------------------------
# Colors
# -----------------------------------------------------------------------
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    DIM = "\033[2m"


def green(s): return f"{C.GREEN}{s}{C.RESET}"
def red(s):   return f"{C.RED}{s}{C.RESET}"
def yellow(s): return f"{C.YELLOW}{s}{C.RESET}"
def cyan(s):  return f"{C.CYAN}{s}{C.RESET}"
def bold(s):  return f"{C.BOLD}{s}{C.RESET}"
def dim(s):   return f"{C.DIM}{s}{C.RESET}"


# -----------------------------------------------------------------------
# Test Result
# -----------------------------------------------------------------------
@dataclass
class TestResult:
    name: str
    passed: bool
    category: str       # 'success' | 'failure'
    errors: List[dict]
    warnings: List[dict]
    duration_ms: float
    fail_reason: str = ""


# -----------------------------------------------------------------------
# Runner
# -----------------------------------------------------------------------

def run_test(filepath: str, expect_errors: bool) -> TestResult:
    """
    Run a single .cps file through the compiler.
    expect_errors=True  → test should produce at least one error
    expect_errors=False → test should produce zero errors
    """
    from compiler.driver import compile_source

    name = os.path.basename(filepath)
    category = "failure" if expect_errors else "success"

    try:
        with open(filepath, encoding="utf-8") as f:
            source = f.read()

        start = time.perf_counter()
        result = compile_source(source, source_name=filepath)
        elapsed = (time.perf_counter() - start) * 1000

        errors = result.get("errors", [])
        warnings = result.get("warnings", [])
        has_errors = bool(errors)

        if expect_errors:
            passed = has_errors
            fail_reason = "" if passed else "Expected semantic errors but none were found"
        else:
            passed = not has_errors
            fail_reason = ""
            if not passed:
                fail_reason = "; ".join(e["message"] for e in errors[:3])

        return TestResult(
            name=name,
            passed=passed,
            category=category,
            errors=errors,
            warnings=warnings,
            duration_ms=elapsed,
            fail_reason=fail_reason,
        )

    except Exception as exc:
        return TestResult(
            name=name,
            passed=False,
            category=category,
            errors=[],
            warnings=[],
            duration_ms=0.0,
            fail_reason=f"Exception: {exc}",
        )


def discover_tests(test_dir: str, category: str) -> List[str]:
    path = os.path.join(test_dir, category)
    if not os.path.isdir(path):
        return []
    return sorted(
        os.path.join(path, f)
        for f in os.listdir(path)
        if f.endswith(".cps")
    )


def print_result(tr: TestResult, verbose: bool):
    icon = green("✓") if tr.passed else red("✗")
    dur = dim(f"{tr.duration_ms:.1f}ms")
    label = bold(tr.name)
    print(f"  {icon}  {label} {dur}")
    if not tr.passed and tr.fail_reason:
        print(f"       {red('→')} {tr.fail_reason}")
    if verbose and tr.errors:
        for e in tr.errors:
            print(f"       {yellow('!')} [{e['phase']}] {e['line']}:{e['column']} {e['message']}")
    if verbose and tr.warnings:
        for w in tr.warnings:
            print(f"       {dim('~')} warn {w['line']}:{w['column']} {w['message']}")


def main():
    parser = argparse.ArgumentParser(description="Compiscript Test Runner")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--filter", "-f", metavar="PATTERN",
                        help="Only run tests whose name contains PATTERN")
    parser.add_argument("--json", action="store_true", help="Output JSON summary")
    args = parser.parse_args()

    test_dir = os.path.dirname(os.path.abspath(__file__))

    success_files = discover_tests(test_dir, "success")
    failure_files = discover_tests(test_dir, "failure")

    if args.filter:
        pattern = args.filter.lower()
        success_files = [f for f in success_files if pattern in f.lower()]
        failure_files = [f for f in failure_files if pattern in f.lower()]

    results: List[TestResult] = []

    total_start = time.perf_counter()

    # --- Success tests ---
    if success_files:
        print(f"\n{bold(cyan('── Success Tests ──'))}")
        for fp in success_files:
            tr = run_test(fp, expect_errors=False)
            results.append(tr)
            print_result(tr, args.verbose)

    # --- Failure tests ---
    if failure_files:
        print(f"\n{bold(cyan('── Failure Tests ──'))}")
        for fp in failure_files:
            tr = run_test(fp, expect_errors=True)
            results.append(tr)
            print_result(tr, args.verbose)

    total_elapsed = (time.perf_counter() - total_start) * 1000

    # --- Summary ---
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total = len(results)

    print(f"\n{'─' * 50}")
    print(f"  {bold('Results')}: {green(f'{passed} passed')}, {red(f'{failed} failed')}, {total} total  {dim(f'{total_elapsed:.0f}ms')}")

    if args.json:
        summary = {
            "passed": passed,
            "failed": failed,
            "total": total,
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "category": r.category,
                    "duration_ms": r.duration_ms,
                    "fail_reason": r.fail_reason,
                    "error_count": len(r.errors),
                    "warning_count": len(r.warnings),
                }
                for r in results
            ],
        }
        print(json.dumps(summary, indent=2))

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
