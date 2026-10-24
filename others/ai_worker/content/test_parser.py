import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from content.archive import MAIN_TYPES, inspect_office
from content.parser import parse_file
from content.protocol import ParseError


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "input"

    def test_utf8_paragraphs_and_crlf(self):
        self.path.write_bytes("安全\r\n\r\n实验".encode())
        result = json.loads(parse_file(self.path, "txt"))
        self.assertEqual([c["locator"]["position"] for c in result["chunks"]], [1, 3])
        self.assertEqual([c["text"] for c in result["chunks"]], ["安全", "实验"])

    def test_bom_and_explicit_chinese_encoding(self):
        for codec, selected in (("utf-16", "utf-8"), ("utf-8-sig", "utf-8"), ("gb18030", "gb18030")):
            with self.subTest(codec=codec):
                self.path.write_bytes("安全".encode(codec))
                self.assertEqual(json.loads(parse_file(self.path, "txt", selected))["chunks"][0]["text"], "安全")

    def test_invalid_encoding_not_silently_dropped(self):
        self.path.write_bytes(b"\xffabc")
        with self.assertRaisesRegex(ParseError, "INVALID_ENCODING"):
            parse_file(self.path, "txt")

    def test_txt_size_and_binary(self):
        self.path.write_bytes(b"x" * (1024 * 1024 + 1))
        with self.assertRaisesRegex(ParseError, "RESOURCE_LIMIT"):
            parse_file(self.path, "txt")
        self.path.write_bytes(b"abc\x00")
        with self.assertRaisesRegex(ParseError, "CORRUPT_FILE"):
            parse_file(self.path, "txt")

    def office(self, extra=None, xml=b"<root/>"):
        main, media = MAIN_TYPES["docx"]
        with ZipFile(self.path, "w", ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                             f'<Override PartName="/{main}" ContentType="{media}"/></Types>')
            archive.writestr(main, xml)
            if extra:
                archive.writestr(*extra)

    def test_office_type_and_actual_xml(self):
        self.office()
        self.assertIn("word/document.xml", inspect_office(self.path, "docx"))
        with self.assertRaisesRegex(ParseError, "UNSUPPORTED_TYPE"):
            inspect_office(self.path, "pptx")

    def test_zip_traversal_and_macro_rejected(self):
        for name, code in (("../escape.xml", "CORRUPT_FILE"), ("word/vbaProject.bin", "UNSUPPORTED_TYPE")):
            self.office((name, b"x"))
            with self.subTest(name=name), self.assertRaisesRegex(ParseError, code):
                inspect_office(self.path, "docx")

    def test_doctype_rejected_in_utf8_and_utf16(self):
        text = '<!DOCTYPE root [<!ENTITY x "unsafe">]><root>&x;</root>'
        for codec in ("utf-8", "utf-16"):
            self.office(xml=text.encode(codec))
            with self.subTest(codec=codec), self.assertRaisesRegex(ParseError, "CORRUPT_FILE"):
                inspect_office(self.path, "docx")

    def test_decompression_ratio(self):
        self.office(("bomb.bin", b"x" * 100000))
        with self.assertRaisesRegex(ParseError, "RESOURCE_LIMIT"):
            inspect_office(self.path, "docx")

    def test_pdf_signature_rejected_before_import(self):
        self.path.write_bytes(b"not a PDF")
        with self.assertRaisesRegex(ParseError, "UNSUPPORTED_TYPE"):
            parse_file(self.path, "pdf")


if __name__ == "__main__":
    unittest.main()
