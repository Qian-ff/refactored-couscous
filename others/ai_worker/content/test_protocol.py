"""Trusted synthetic protocol checks; full parser/sandbox checks are added as implemented."""
import json
import unittest

from content.protocol import Chunk, ParseError, encode_result, split_text, text_hash


class ProtocolTests(unittest.TestCase):
    def test_long_chinese_paragraph_keeps_locator_and_hash(self):
        text = "实验安全" * 3000
        chunks = split_text(text, 7, 1)
        result = json.loads(encode_result("docx", chunks, [], "synthetic/1"))
        self.assertEqual("".join(c["text"] for c in result["chunks"]), text)
        self.assertEqual([c["locator"]["position"] for c in result["chunks"]], [7, 7])
        self.assertEqual(result["chunks"][1]["locator"]["part"], 2)
        self.assertEqual(result["chunks"][0]["text_hash"], text_hash(chunks[0].text))

    def test_empty_is_not_success(self):
        with self.assertRaisesRegex(ParseError, "NO_TEXT"):
            encode_result("pdf", [Chunk(1, 1, 1, "  ")], [], "test/1")

    def test_invalid_ordinal_and_location(self):
        for chunk in (Chunk(2, 1, 1, "x"), Chunk(1, 0, 1, "x"), Chunk(1, True, 1, "x")):
            with self.subTest(chunk=chunk), self.assertRaisesRegex(ParseError, "INVALID_RESULT"):
                encode_result("pdf", [chunk], [], "test/1")

    def test_oversized_chunk_rejected_not_truncated(self):
        with self.assertRaisesRegex(ParseError, "INVALID_RESULT"):
            encode_result("txt", [Chunk(1, 1, 1, "x" * 8193)], [], "test/1")

    def test_hidden_content_warning_preserved_as_text(self):
        result = json.loads(encode_result("pptx", [Chunk(1, 3, 1, "<script>资料</script>")],
                                          ["HIDDEN_SLIDES"], "test/1"))
        self.assertEqual(result["warnings"], ["HIDDEN_SLIDES"])
        self.assertEqual(result["chunks"][0]["locator"]["kind"], "slide")
        self.assertEqual(result["chunks"][0]["text"], "<script>资料</script>")


if __name__ == "__main__":
    unittest.main()
