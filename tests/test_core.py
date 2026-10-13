import unittest

from rust_v2 import Segment, parse_segment


class TestSegmentHappyPath(unittest.TestCase):
    def test_basic_pid(self):
        seg = Segment("PID|field1|field2|field3")
        self.assertEqual(seg.name, "PID")
        self.assertEqual(seg.fields, ["PID", "field1", "field2", "field3"])

    def test_single_field_no_delimiter(self):
        seg = Segment("EVN")
        self.assertEqual(seg.name, "EVN")
        self.assertEqual(seg.fields, ["EVN"])

    def test_msh_with_msh1_constant(self):
        seg = Segment("MSH|^~\\&|SENDING|RECV")
        self.assertEqual(seg.name, "MSH")
        self.assertEqual(seg.fields, ["MSH", "", "^~\\&", "SENDING", "RECV"])

    def test_len_and_iter(self):
        seg = Segment("PID|a|b|c")
        self.assertEqual(len(seg), 4)
        self.assertEqual(list(seg), ["PID", "a", "b", "c"])

    def test_getitem_index(self):
        seg = Segment("PID|a|b|c")
        self.assertEqual(seg[0], "PID")
        self.assertEqual(seg[2], "b")
        with self.assertRaises(IndexError):
            _ = seg[99]

    def test_get_method_1_based(self):
        seg = Segment("PID|a|b|c")
        self.assertEqual(seg.get(0), "PID")
        self.assertEqual(seg.get(1), "a")
        self.assertEqual(seg.get(3), "c")
        self.assertIsNone(seg.get(4))
        self.assertEqual(seg.get(4, "DEFAULT"), "DEFAULT")

    def test_as_dict_excludes_name(self):
        seg = Segment("PID|a|b")
        self.assertEqual(seg.as_dict(), {1: "a", 2: "b"})

    def test_raw_preserved(self):
        raw = "PID|a|b|"
        seg = Segment(raw)
        self.assertEqual(seg.raw, raw)


class TestTrailingDelimiter(unittest.TestCase):
    def test_trailing_delimiter_dropped(self):
        seg = Segment("PID|a|b|")
        self.assertEqual(seg.fields, ["PID", "a", "b"])

    def test_trailing_delimiter_dropped_with_empty_interior(self):
        seg = Segment("PID|a||b|")
        self.assertEqual(seg.fields, ["PID", "a", "", "b"])

    def test_multiple_trailing_delimiters_only_last_dropped(self):
        seg = Segment("PID|a||")
        self.assertEqual(seg.fields, ["PID", "a", ""])

    def test_only_delimiter(self):
        seg = Segment("|")
        self.assertEqual(seg.fields, [])
        self.assertEqual(seg.name, "")


class TestInteriorEmpties(unittest.TestCase):
    def test_interior_empty_preserved(self):
        seg = Segment("PID||b|c")
        self.assertEqual(seg.fields, ["PID", "", "b", "c"])

    def test_multiple_interior_empties(self):
        seg = Segment("PV1|||||a|b")
        self.assertEqual(seg.fields, ["PV1", "", "", "", "", "a", "b"])


class TestEmptySegment(unittest.TestCase):
    def test_empty_string(self):
        seg = Segment("")
        self.assertEqual(seg.fields, [])
        self.assertEqual(seg.name, "")

    def test_empty_string_get_returns_default(self):
        seg = Segment("")
        self.assertIsNone(seg.get(0))
        self.assertEqual(seg.get(0, "X"), "X")

    def test_empty_string_len(self):
        seg = Segment("")
        self.assertEqual(len(seg), 0)

    def test_empty_string_as_dict(self):
        seg = Segment("")
        self.assertEqual(seg.as_dict(), {})


class TestEscape(unittest.TestCase):
    def test_escaped_delimiter_preserved(self):
        seg = Segment("PID|a\\F\\b|c")
        self.assertEqual(seg.fields, ["PID", "a\\F\\b", "c"])

    def test_escaped_escape_preserved(self):
        seg = Segment("PID|a\\Eb|c")
        self.assertEqual(seg.fields, ["PID", "a\\Eb", "c"])

    def test_escape_only_at_end(self):
        seg = Segment("PID|a\\")
        self.assertEqual(seg.fields, ["PID", "a\\"])


class TestCustomDelimiters(unittest.TestCase):
    def test_custom_field_delimiter(self):
        seg = Segment("PID$a$b", field_delimiter="$")
        self.assertEqual(seg.fields, ["PID", "a", "b"])

    def test_custom_field_delimiter_with_default_escape(self):
        seg = Segment("PID$a\\$b$c", field_delimiter="$")
        self.assertEqual(seg.fields, ["PID", "a\\$b", "c"])

    def test_custom_escape_char(self):
        seg = Segment("PID|a&|b|c", escape_char="&")
        self.assertEqual(seg.fields, ["PID", "a&|b", "c"])

    def test_component_and_repetition_stored_verbatim(self):
        seg = Segment("PID|a^b~c^d|e")
        self.assertEqual(seg.fields, ["PID", "a^b~c^d", "e"])


class TestValidation(unittest.TestCase):
    def test_raw_must_be_str(self):
        with self.assertRaises(TypeError):
            Segment(123)  # type: ignore

    def test_field_delimiter_must_be_single_char(self):
        with self.assertRaises(ValueError):
            Segment("PID|a", field_delimiter="")
        with self.assertRaises(ValueError):
            Segment("PID|a", field_delimiter="||")

    def test_field_delimiter_type_checked(self):
        with self.assertRaises(TypeError):
            Segment("PID|a", field_delimiter=124)  # type: ignore

    def test_escape_char_type_checked(self):
        with self.assertRaises(TypeError):
            Segment("PID|a", escape_char=None)  # type: ignore

    def test_component_delimiter_validated(self):
        with self.assertRaises(ValueError):
            Segment("PID|a", component_delimiter="^^")

    def test_repetition_delimiter_validated(self):
        with self.assertRaises(ValueError):
            Segment("PID|a", repetition_delimiter="")


class TestParseSegment(unittest.TestCase):
    def test_returns_list(self):
        result = parse_segment("PID|a|b|c")
        self.assertIsInstance(result, list)
        self.assertEqual(result, ["PID", "a", "b", "c"])

    def test_custom_delimiters(self):
        result = parse_segment("PID$a$b", field_delimiter="$")
        self.assertEqual(result, ["PID", "a", "b"])

    def test_trailing_delimiter_dropped(self):
        result = parse_segment("PID|a|")
        self.assertEqual(result, ["PID", "a"])

    def test_empty_returns_empty_list(self):
        result = parse_segment("")
        self.assertEqual(result, [])

    def test_escape(self):
        result = parse_segment("PID|a\\F\\b|c")
        self.assertEqual(result, ["PID", "a\\F\\b", "c"])


class TestRepr(unittest.TestCase):
    def test_repr_shows_name_and_fields(self):
        seg = Segment("PID|a|b")
        r = repr(seg)
        self.assertIn("PID", r)
        self.assertIn("fields", r)


if __name__ == "__main__":
    unittest.main()
