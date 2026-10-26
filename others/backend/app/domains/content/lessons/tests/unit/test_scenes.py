import unittest

from app.domains.content.lessons.scenes import UnsafeScene, validate_svg

PREFIX = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540">'
SAFE = PREFIX + '<rect id="desk" x="10" y="20" width="200" height="100" fill="#087F8C"/><text x="20" y="50">实验台</text></svg>'


class SceneSecurityTests(unittest.TestCase):
    def test_passive_chinese_svg_is_stable_and_has_a_hash(self):
        result = validate_svg(SAFE)
        self.assertEqual(result.view_box, (0.0, 0.0, 960.0, 540.0))
        self.assertIn("实验台", result.svg)
        self.assertEqual(result.sha256, validate_svg(result.svg).sha256)

    def test_active_elements_and_attributes_are_rejected(self):
        for body in ('<script>alert(1)</script>', '<foreignObject/>', '<image href="https://example.test/x"/>',
                     '<style>rect{fill:red}</style>', '<rect onclick="alert(1)"/>', '<rect fill="url(https://example.test/x)"/>',
                     '<g style="display:none"/>', '<use href="#desk"/>'):
            with self.subTest(body=body), self.assertRaises(UnsafeScene):
                validate_svg(PREFIX + body + '</svg>')

    def test_doctype_entities_and_processing_instructions_are_rejected(self):
        for value in ('<!DOCTYPE svg [<!ENTITY x "expanded">]>' + PREFIX + '<text>&x;</text></svg>',
                      '<?xml-stylesheet href="https://example.test/x"?>' + SAFE,
                      '<!DOCTYPE svg SYSTEM "file:///private">' + SAFE):
            with self.subTest(value=value[:30]), self.assertRaises(UnsafeScene):
                validate_svg(value)

    def test_bounds_and_repeated_ids(self):
        for value in (PREFIX + '<g>' * 26 + '</g>' * 26 + '</svg>',
                      PREFIX + '<rect/>' * 2001 + '</svg>',
                      PREFIX + '<rect id="same"/><circle id="same"/></svg>',
                      SAFE.replace('960 540', '0 540'), SAFE.replace('x="10"', 'x="1e999"'),
                      PREFIX + '<text>' + '安' * 90000 + '</text></svg>'):
            with self.subTest(size=len(value)), self.assertRaises(UnsafeScene):
                validate_svg(value)

    def test_foreign_namespace_and_malformed_xml(self):
        for value in ('<svg viewBox="0 0 10 10"/>', PREFIX + '<svg xmlns="http://www.w3.org/1999/xhtml"/></svg>',
                      PREFIX + '<rect></svg>'):
            with self.subTest(value=value[:50]), self.assertRaises(UnsafeScene):
                validate_svg(value)


if __name__ == "__main__":
    unittest.main()
