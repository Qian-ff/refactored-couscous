"""Bounded CSV parsing. Secrets are inputs only, never part of an error/preview."""
import csv
import hashlib
import hmac
import io
import json
from dataclasses import dataclass

from pydantic import SecretStr

from app.core.config import settings

ACCOUNT_COLUMNS = (
    "username", "student_no", "display_name", "college_code", "major_code", "role",
    "temporary_password", "gender", "contact",
)
ROSTER_COLUMNS = ("username",)
MAX_ROWS = 500
MAX_BYTES = 1_048_576


@dataclass(frozen=True)
class CsvRow:
    line: int
    values: dict[str, str]


def fingerprint(value: object) -> str:
    """A keyed digest prevents persisted password-bearing requests becoming a hash oracle."""
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False,
                     default=lambda item: item.get_secret_value() if isinstance(item, SecretStr) else str(item),
                     separators=(",", ":"))
    return hmac.new(settings.SECRET_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()


def csv_template(kind: str) -> str:
    columns = ACCOUNT_COLUMNS if kind == "accounts" else ROSTER_COLUMNS
    output = io.StringIO(newline="")
    csv.writer(output).writerow(columns)
    return "\ufeff" + output.getvalue()


def parse_csv(text: str, kind: str) -> tuple[list[CsvRow], list[dict]]:
    if kind not in {"accounts", "roster"}:
        return [], [{"line": 1, "field": "kind", "message": "不支持的导入类型"}]
    try:
        size = len(text.encode("utf-8"))
    except UnicodeError:
        return [], [{"line": 1, "field": "csv", "message": "CSV 包含无效 Unicode 字符"}]
    if size > MAX_BYTES:
        return [], [{"line": 1, "field": "csv", "message": "CSV 不得超过 1 MiB"}]
    allowed = ACCOUNT_COLUMNS if kind == "accounts" else ROSTER_COLUMNS
    required = {"username", "display_name", "college_code", "role", "temporary_password"} if kind == "accounts" else {"username"}
    errors, rows = [], []
    try:
        reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff"), newline=""), strict=True)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)) or not required.issubset(headers) or set(headers) - set(allowed):
            return [], [{"line": 1, "field": "headers", "message": "列名重复、缺少必填列或包含未知列，请使用模板"}]
        seen: dict[str, set[str]] = {"username": set(), "student_no": set()}
        for row_number, data in enumerate(reader, start=1):
            line = reader.line_num
            if row_number > MAX_ROWS:
                errors.append({"line": line, "field": "csv", "message": f"每批最多 {MAX_ROWS} 行"})
                break
            if None in data or any(value is None for value in data.values()):
                errors.append({"line": line, "field": "csv", "message": "行列数与模板不一致"})
                continue
            values = {key: (value if key == "temporary_password" else value.strip()) for key, value in data.items()}
            for field in required:
                if not values.get(field):
                    errors.append({"line": line, "field": field, "message": "必填值为空"})
            for field in seen:
                value = values.get(field, "")
                if value and value in seen[field]:
                    errors.append({"line": line, "field": field, "message": "文件内重复"})
                seen[field].add(value)
            rows.append(CsvRow(line, values))
        if not rows and not errors:
            errors.append({"line": 2, "field": "csv", "message": "没有待导入数据"})
    except (csv.Error, UnicodeError):
        errors.append({"line": 1, "field": "csv", "message": "CSV 格式无效，请使用 UTF-8 CSV 模板"})
    return rows, errors
