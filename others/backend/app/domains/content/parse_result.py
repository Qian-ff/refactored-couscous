"""Reject malformed/oversized parser output before writing an immutable snapshot."""
import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

MAX_OUTPUT = 16 * 1024 * 1024


class ResultError(ValueError):
    def __init__(self, code="INVALID_RESULT"):
        super().__init__(code)
        self.code = code


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Locator(Strict):
    kind: Literal["page", "slide", "paragraph"]
    position: int = Field(ge=1, le=20000)
    part: int = Field(ge=1, le=20000)


class ParsedChunk(Strict):
    ordinal: int = Field(ge=1, le=20000)
    locator: Locator
    text: str = Field(max_length=8192)
    text_hash: str = Field(pattern="^[0-9a-f]{64}$")


class ParsedResult(Strict):
    protocol: Literal["labconnect.parse/1"]
    format: Literal["pdf", "pptx", "docx", "txt", "text"]
    parser_version: str = Field(min_length=1, max_length=200)
    chunks: list[ParsedChunk] = Field(min_length=1, max_length=20000)
    warnings: list[str] = Field(max_length=1000)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ResultError()
        result[key] = value
    return result


def reject_constant(_value):
    raise ResultError()


def validate_result(raw: bytes, expected_format: str):
    if not isinstance(raw, bytes) or len(raw) > MAX_OUTPUT:
        raise ResultError("RESOURCE_LIMIT")
    try:
        payload = json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)
        result = ParsedResult.model_validate(payload)
        if result.format != expected_format:
            raise ResultError()
        kind = {"pdf": "page", "pptx": "slide", "docx": "paragraph", "txt": "paragraph", "text": "paragraph"}[expected_format]
        position_limit = {"pdf": 500, "pptx": 300}.get(expected_format, 20000)
        characters = 0
        previous_position, previous_part = 0, 0
        for ordinal, chunk in enumerate(result.chunks, 1):
            location = chunk.locator
            if (chunk.ordinal != ordinal or location.kind != kind or location.position > position_limit
                    or location.position < previous_position
                    or location.part != (previous_part + 1 if location.position == previous_position else 1)
                    or hashlib.sha256(chunk.text.encode("utf-8")).hexdigest() != chunk.text_hash):
                raise ResultError()
            previous_position, previous_part = location.position, location.part
            characters += len(chunk.text)
        if characters > 2_000_000:
            raise ResultError("RESOURCE_LIMIT")
        if not any(chunk.text.strip() for chunk in result.chunks):
            raise ResultError("NO_TEXT")
        for warning in result.warnings:
            if (not warning or len(warning) > 100 or not warning[0].isupper()
                    or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for c in warning)):
                raise ResultError()
        return result
    except (ValidationError, ValueError, UnicodeError, KeyError, RecursionError) as error:
        if isinstance(error, ResultError):
            raise
        raise ResultError() from None
