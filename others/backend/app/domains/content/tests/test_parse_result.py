import hashlib
import json
import unittest

from app.domains.content.parse_result import ResultError, validate_result


def payload():
    text = "实验室安全"
    return {"protocol": "labconnect.parse/1", "format": "docx", "parser_version": "synthetic/1", "warnings": [],
            "chunks": [{"ordinal": 1, "locator": {"kind": "paragraph", "position": 2, "part": 1},
                        "text": text, "text_hash": hashlib.sha256(text.encode()).hexdigest()}]}


class ResultTests(unittest.TestCase):
    def test_valid_chinese_and_gap_keeps_source_position(self):
        result = validate_result(json.dumps(payload()).encode(), "docx")
        self.assertEqual(result.chunks[0].locator.position, 2)
        self.assertEqual(result.chunks[0].text, "实验室安全")

    def test_malformed_hash_ordinal_and_locator(self):
        for change in ({"text_hash": "a" * 64}, {"ordinal": True}, {"ordinal": 2},
                       {"locator": {"kind": "page", "position": 2, "part": 1}},
                       {"locator": {"kind": "paragraph", "position": 2, "part": 2}},
                       {"text": "x" * 8193}):
            data = payload()
            data["chunks"][0].update(change)
            with self.subTest(change=list(change)), self.assertRaises(ResultError):
                validate_result(json.dumps(data).encode(), "docx")

    def test_format_and_unknown_fields_rejected(self):
        data = payload()
        with self.assertRaises(ResultError):
            validate_result(json.dumps(data).encode(), "pdf")
        data["file_path"] = "/private/source"
        with self.assertRaises(ResultError):
            validate_result(json.dumps(data).encode(), "docx")

    def test_duplicate_json_keys_not_last_value_wins(self):
        with self.assertRaises(ResultError):
            validate_result(b'{"format":"docx","format":"pdf"}', "pdf")

    def test_oversized_output_rejected_before_json_decode(self):
        with self.assertRaisesRegex(ResultError, "RESOURCE_LIMIT"):
            validate_result(b" " * (16 * 1024 * 1024 + 1), "docx")

    def test_warnings_cannot_carry_document_or_paths(self):
        for value in ("/private/source", "SOME secret", "中文正文"):
            data = payload()
            data["warnings"] = [value]
            with self.subTest(value=value), self.assertRaises(ResultError):
                validate_result(json.dumps(data).encode(), "docx")

    def test_fragment_part_sequence(self):
        data = payload()
        data["chunks"].append(dict(data["chunks"][0], ordinal=2,
                                   locator={"kind": "paragraph", "position": 2, "part": 2}))
        validate_result(json.dumps(data).encode(), "docx")
        data["chunks"][1]["locator"]["position"] = 1
        with self.assertRaises(ResultError):
            validate_result(json.dumps(data).encode(), "docx")


if __name__ == "__main__":
    unittest.main()
