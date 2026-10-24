"""Reproducible trusted tests. Sandbox evidence must be supplied by A separately."""
import argparse
import json
import unittest
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    packages = {}
    for name in ("pypdf", "python-docx", "python-pptx", "lxml"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    complete = result.wasSuccessful() and all(packages.values()) and not result.skipped
    report = {"scope": "trusted-synthetic", "sandbox_verified": False,
              "packages": packages, "tests": result.testsRun,
              "failures": len(result.failures), "errors": len(result.errors),
              "skipped": len(result.skipped),
              "four_format_integration_verified": bool(complete),
              "dependencies_ready": all(packages.values())}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
