import csv
import io
import unittest
import zipfile

from app.domains.content.questions.schemas import DraftContent
from app.domains.content.questions.tests.unit.test_schema import sample_question
from app.domains.content.questions.transfer_codec import (
    COLUMNS, INPUT_LIMITS, VERSION, TransferError, _openpyxl, export_template, parse_template, validate_xlsx_archive,
)


def content(**changes):
    return DraftContent.model_validate({"payload": {**sample_question(), **changes}})


def csv_bytes(rows):
    text = io.StringIO(newline="")
    csv.writer(text).writerows(rows)
    return text.getvalue().encode("utf-8")


def archive(worksheet, extra=None):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as target:
        for name, body in {
            "[Content_Types].xml": "<Types/>", "_rels/.rels": "<Relationships/>",
            "xl/workbook.xml": "<workbook/>", "xl/_rels/workbook.xml.rels": "<Relationships/>",
            "xl/worksheets/sheet1.xml": worksheet, **(extra or {}),
        }.items():
            target.writestr(name, body)
    return output.getvalue()


class TransferCodecTests(unittest.TestCase):
    def test_csv_export_is_lossless_and_formula_safe_even_for_whitespace_and_apostrophes(self):
        for text in ("=SUM(1,2)", "+1", "-1", "@name", "'quoted", "实验,\"中文\"\n下一行"):
            with self.subTest(text=text):
                original = content(stem=text)
                raw = export_template([original], "csv")
                cells = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
                self.assertTrue(all(cell.startswith("'") for cell in cells[2]))
                result = parse_template(raw, "csv")
                self.assertEqual(result.rows[0].content, original)
                self.assertIsNone(result.rows[0].error)
                self.assertEqual(result.digest(), parse_template(raw, "csv").digest())

    def test_batch_duplicate_uses_prompt_and_options_even_with_conflicting_answers(self):
        raw = export_template([content(), content(answer_ids=["b"])], "csv")
        result = parse_template(raw, "csv")
        self.assertIsNone(result.rows[0].duplicate_of)
        self.assertEqual(result.rows[1].duplicate_of, 3)

    def test_row_error_is_safe_and_does_not_echo_private_uploaded_text(self):
        result = parse_template(csv_bytes([[VERSION, "literal-text-v1"], COLUMNS,
            ["single", "private secret", "not json", "[]", "secret", "[]", "easy", "{}"]]), "csv")
        self.assertEqual(result.rows[0].error, "invalid_question")
        self.assertNotIn("secret", result.model_dump_json())

    def test_invalid_encoding_columns_and_formula_prefix_are_rejected(self):
        for raw in (b"\xff", csv_bytes([[VERSION, "unknown"]]), csv_bytes([[VERSION, "literal-text-v1"], ["bad"]])):
            with self.subTest(raw=raw), self.assertRaises(TransferError):
                parse_template(raw, "csv")
        result = parse_template(csv_bytes([[VERSION, "literal-text-v1"], COLUMNS,
            ["single", "\t=CMD()", "[]", "[]", "text", "[]", "easy", "{}"]]), "csv")
        self.assertEqual(result.rows[0].error, "formula_prefix")

    def test_input_row_and_export_size_bounds(self):
        with self.assertRaisesRegex(TransferError, "input_size"):
            parse_template(b"x" * (INPUT_LIMITS["csv"] + 1), "csv")
        with self.assertRaisesRegex(TransferError, "row_limit"):
            parse_template(csv_bytes([[VERSION, "literal-text-v1"], COLUMNS] + [["bad"]] * 1001), "csv")
        with self.assertRaisesRegex(TransferError, "export_size"):
            export_template([content(stem="安" * 3500)] * 150, "csv")

    def test_zip_checks_actual_expansion_not_compressed_size(self):
        raw = archive("<sheet>" + "a" * 16777216 + "</sheet>")
        self.assertLess(len(raw), INPUT_LIMITS["xlsx"])
        with self.assertRaisesRegex(TransferError, "xlsx_expanded_size"):
            validate_xlsx_archive(raw)

    def test_zip_rejects_traversal_macros_and_external_links(self):
        for extra in ({"../escape.xml": "<x/>"}, {"xl/vbaProject.bin": "macro"},
                      {"xl/_rels/workbook.xml.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship TargetMode="External" Target="https://example.test"/></Relationships>'}):
            with self.subTest(parts=list(extra)), self.assertRaises(TransferError):
                validate_xlsx_archive(archive("<sheet/>", extra))

    def test_all_xml_is_checked_for_entities_formulas_and_out_of_range_cells(self):
        for xml in ('<!DOCTYPE a [<!ENTITY x "secret">]><sheet>&x;</sheet>',
                    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><f>1+1</f></worksheet>',
                    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><c r="XFD1048576"/></worksheet>'):
            with self.subTest(xml=xml[:40]), self.assertRaises(TransferError):
                validate_xlsx_archive(archive(xml))

    def test_real_xlsx_roundtrip_requires_the_exact_approved_dependencies(self):
        try:
            _openpyxl()
        except TransferError:
            self.skipTest("A has not installed/locked the approved XLSX dependencies")
        raw = export_template([content(stem="=SUM(1,2)")], "xlsx")
        result = parse_template(raw, "xlsx")
        self.assertEqual(result.rows[0].content.payload.stem, "=SUM(1,2)")


if __name__ == "__main__":
    unittest.main()
