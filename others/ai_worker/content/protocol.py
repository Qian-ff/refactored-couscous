"""Versioned JSON boundary for the isolated parser (not a process sandbox)."""
import hashlib
import json
from dataclasses import dataclass

PROTOCOL = "labconnect.parse/1"
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
MAX_TEXT_CHARS = 2_000_000
MAX_CHUNKS = 20_000
MAX_CHUNK_CHARS = 8192
FORMATS = {"pdf": "page", "pptx": "slide", "docx": "paragraph", "txt": "paragraph", "text": "paragraph"}


class ParseError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Chunk:
    ordinal: int
    position: int
    part: int
    text: str

    def as_json(self, kind: str) -> dict:
        return {"ordinal": self.ordinal, "locator": {"kind": kind, "position": self.position,
                "part": self.part}, "text": self.text, "text_hash": text_hash(self.text)}


def encode_result(format_name: str, chunks: list[Chunk], warnings: list[str], parser_version: str) -> bytes:
    """Produce one bounded result; callers must also bound subprocess streams while reading."""
    if format_name not in FORMATS:
        raise ParseError("UNSUPPORTED_TYPE")
    if not parser_version or len(parser_version) > 200:
        raise ParseError("INVALID_RESULT")
    if not chunks or not any(chunk.text.strip() for chunk in chunks):
        raise ParseError("NO_TEXT")
    if len(chunks) > MAX_CHUNKS or sum(len(chunk.text) for chunk in chunks) > MAX_TEXT_CHARS:
        raise ParseError("RESOURCE_LIMIT")
    if len(warnings) > 1000 or any(not isinstance(w, str) or len(w) > 500 for w in warnings):
        raise ParseError("INVALID_RESULT")
    for ordinal, chunk in enumerate(chunks, 1):
        if (type(chunk.ordinal) is not int or chunk.ordinal != ordinal
                or type(chunk.position) is not int or chunk.position < 1
                or type(chunk.part) is not int or chunk.part < 1
                or not isinstance(chunk.text, str) or len(chunk.text) > MAX_CHUNK_CHARS):
            raise ParseError("INVALID_RESULT")
    payload = {"protocol": PROTOCOL, "format": format_name, "parser_version": parser_version,
               "chunks": [chunk.as_json(FORMATS[format_name]) for chunk in chunks], "warnings": warnings}
    # Bound encoding incrementally rather than constructing an unbounded bytes response.
    output = bytearray()
    for piece in json.JSONEncoder(ensure_ascii=False, separators=(",", ":")).iterencode(payload):
        encoded = piece.encode("utf-8")
        if len(output) + len(encoded) > MAX_OUTPUT_BYTES:
            raise ParseError("RESOURCE_LIMIT")
        output.extend(encoded)
    return bytes(output)


def split_text(text: str, position: int, start_ordinal: int) -> list[Chunk]:
    """Splitting preserves the original page/paragraph and records a stable part number."""
    if type(position) is not int or position < 1 or type(start_ordinal) is not int or start_ordinal < 1:
        raise ParseError("INVALID_RESULT")
    return [Chunk(start_ordinal + part, position, part + 1, text[offset:offset + MAX_CHUNK_CHARS])
            for part, offset in enumerate(range(0, len(text), MAX_CHUNK_CHARS))]
