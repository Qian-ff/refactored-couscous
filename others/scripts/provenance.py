"""Print or verify a checkout-bound development service without exposing local paths."""
import argparse
import json
from pathlib import Path
import runpy
import sys
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--surface", choices=["api", "web"], required=True)
    parser.add_argument("--verify-url")
    args = parser.parse_args()
    identify = runpy.run_path(str(args.root / "others/backend/app/core/provenance.py"))["identity"]
    expected = identify(args.root, args.surface)
    if args.verify_url:
        suffix = "/api/v1/dev/identity" if args.surface == "api" else "/__labconnect/identity"
        with urllib.request.urlopen(args.verify_url.rstrip("/") + suffix, timeout=5) as response:
            actual = json.load(response)
        mismatches = [key for key, value in expected.items() if actual.get(key) != value]
        if mismatches:
            raise RuntimeError("Service belongs to another or stale checkout: " + ", ".join(mismatches))
    print(json.dumps(expected))


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
