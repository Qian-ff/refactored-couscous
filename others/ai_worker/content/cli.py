"""One-shot CLI for A's fixed runner template; never an HTTP or shell execution API."""
import argparse
import json
import sys
from pathlib import Path

from content.parser import parse_file
from content.protocol import ParseError


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--format", choices=["pdf", "pptx", "docx", "txt", "text"], required=True)
    parser.add_argument("--encoding", choices=["utf-8", "gb18030"], default="utf-8")
    args = parser.parse_args()
    try:
        result = parse_file(args.input, args.format, args.encoding)
    except ParseError as error:
        sys.stdout.write(json.dumps({"error_code": error.code}))
        return 1
    except Exception:
        # Third-party diagnostics can contain document text or mounted paths.
        sys.stdout.write('{"error_code":"CORRUPT_FILE"}')
        return 1
    sys.stdout.buffer.write(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
