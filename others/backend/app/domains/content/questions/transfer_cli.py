"""Fixed one-shot worker. A passes a kernel-sealed fd; stdout is bounded JSON/CSV/XLSX.

No database, dotenv, shell, network client or user-supplied path is imported here.
Process timeout and filesystem isolation remain the trusted runner's responsibility.
"""
import argparse
import os
import sys
from typing import Literal

from pydantic import Field, ValidationError

from app.domains.content.questions.schemas import DraftContent, StrictModel, canonical_bytes
from app.domains.content.questions.transfer_codec import INPUT_LIMITS, OUTPUT_LIMIT, VERSION, TransferError, export_template, parse_template


class ExportInput(StrictModel):
    protocol: Literal["labconnect.question-transfer/1"]
    questions: tuple[DraftContent, ...] = Field(min_length=1, max_length=1000)


def process(source, operation, format):
    if operation not in {"import", "export"} or format not in INPUT_LIMITS:
        raise TransferError("unsupported_operation")
    limit = INPUT_LIMITS[format] if operation == "import" else OUTPUT_LIMIT
    data = source.read(limit + 1)
    if len(data) > limit:
        raise TransferError("input_size")
    if operation == "import":
        return canonical_bytes(parse_template(data, format))
    request = ExportInput.model_validate_json(data)
    return export_template(request.questions, format)


def main():
    parser = argparse.ArgumentParser(description="Fixed labconnect.question-transfer/1 worker")
    parser.add_argument("--operation", choices=["import", "export"], required=True)
    parser.add_argument("--format", choices=["csv", "xlsx"], required=True)
    parser.add_argument("--input-fd", type=int, required=True)
    args = parser.parse_args()
    try:
        import fcntl
        required = fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL
        if args.input_fd < 0 or fcntl.fcntl(args.input_fd, fcntl.F_GET_SEALS) & required != required:
            raise ValueError("Unsealed input")
        with os.fdopen(os.dup(args.input_fd), "rb") as source:
            result = process(source, args.operation, args.format)
        if len(result) > OUTPUT_LIMIT:
            raise TransferError("output_size")
    except TransferError as error:
        result = canonical_bytes({"protocol": VERSION, "error_code": str(error)})
    except (ValidationError, ValueError, RecursionError):
        result = canonical_bytes({"protocol": VERSION, "error_code": "invalid_input"})
    except Exception:
        # Parser/library errors can contain uploaded text, credentials or mounted paths.
        result = canonical_bytes({"protocol": VERSION, "error_code": "transfer_failed"})
    else:
        sys.stdout.buffer.write(result)
        return 0
    sys.stdout.buffer.write(result)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
