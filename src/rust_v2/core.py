"""Core parsing logic for HL7 v2 segments.

Interpretation decisions (documented once here, referenced from README):

  * Trailing delimiter policy: an unescaped trailing delimiter is discarded.
    In HL7 v2.x a trailing field separator | after the last present value is a
    transport artifact (a segment is typically written as PID|...|<lastval>| with
    a trailing | before the segment terminator) and rarely carries a "present
    but empty" field. The two cases (absent vs. present-and-empty) are
    indistinguishable from a lone | alone, so we collapse to absent.

  * Empty result policy: a segment whose name cannot be recovered (empty raw,
    or the field list reduces to a single empty string) yields fields == []
    rather than [''] -- a one-field segment named '' is not a meaningful HL7
    segment and callers should not branch on it.

  * Component and repetition delimiters are honored where they are meaningful
    for field VALUES but component/repetition splitting is left to higher-level
    consumers. This library's job is delimiter-aware field splitting.

  * MSH-1 policy: MSH-1 is the field delimiter character itself. When the
    segment name is 'MSH', an empty string is inserted at index 1 to represent
    MSH-1, so that MSH-2 (the encoding characters) lands at index 2 as
    expected.
"""

from __future__ import annotations

from typing import List, Optional, Sequence


class Segment:
    """One HL7 v2 segment, split into fields.

    Construction splits the raw segment string on an (optionally escaped)
    field delimiter. The segment name is fields[0]; remaining fields follow in
    order. Fields may be accessed by position or by attribute-style lookup via
    .get(index).

    Attributes
    ----------
    name : str
        The segment identifier (e.g. 'PID', 'MSH'). Empty string if the raw
        input had no fields.
    fields : list[str]
        The full field list, including the segment name at index 0.
    raw : str
        The original raw segment text as provided.
    """

    __slots__ = ("name", "fields", "raw")

    def __init__(
        self,
        raw: str,
        field_delimiter: str = "|",
        component_delimiter: str = "^",
        repetition_delimiter: str = "~",
        escape_char: str = "\\",
    ) -> None:
        if not isinstance(raw, str):
            raise TypeError(
                f"raw must be str, got {type(raw).__name__}"
            )
        self._validate_delimiter(
            "field_delimiter", field_delimiter
        )
        self._validate_delimiter(
            "component_delimiter", component_delimiter
        )
        self._validate_delimiter(
            "repetition_delimiter", repetition_delimiter
        )
        self._validate_delimiter("escape_char", escape_char)

        self.raw = raw
        self.fields = self._split(
            raw,
            field_delimiter,
            escape_char,
        )
        if len(self.fields) == 1 and self.fields[0] == "":
            # Distinguish 'no fields' from 'one field named ""'. The latter is
            # not a meaningful HL7 segment; callers expecting .name to be a
            # 3-letter identifier should not see a phantom field here.
            self.fields = []
        elif len(self.fields) >= 1 and self.fields[0] == "MSH":
            # MSH-1 is the field delimiter character itself. Insert an empty
            # string at index 1 to represent MSH-1 so that MSH-2 (encoding
            # characters) lands at index 2.
            self.fields.insert(1, "")
        self.name = self.fields[0] if self.fields else ""

    @staticmethod
    def _validate_delimiter(arg_name: str, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(
                f"{arg_name} must be str, got {type(value).__name__}"
            )
        if value == "":
            raise ValueError(
                f"{arg_name} must be a non-empty single character"
            )
        if len(value) != 1:
            raise ValueError(
                f"{arg_name} must be exactly one character, got {len(value)!r}"
            )

    @staticmethod
    def _split(
        text: str,
        delimiter: str,
        escape_char: str,
    ) -> List[str]:
        """Split text on delimiter, honoring escape_char as a protection.

        Trailing unescaped delimiter is dropped (see module docstring).
        """
        fields: List[str] = []
        buf: List[str] = []
        i = 0
        n = len(text)
        ended_with_delimiter = False
        while i < n:
            c = text[i]
            if c == escape_char and i + 1 < n:
                # Preserve the escape sequence verbatim. HL7 escape sequences
                # are multi-character (e.g. \\F\\, \\S\\, \\E\\); a two-char slice
                # here is just enough to protect the immediately-following
                # delimiter from being seen as a splitter. The full sequence,
                # if any, will pass through unchanged as separate buf entries
                # that we join back together.
                buf.append(c)
                buf.append(text[i + 1])
                i += 2
                ended_with_delimiter = False
                continue
            if c == delimiter:
                fields.append("".join(buf))
                buf = []
                i += 1
                ended_with_delimiter = True
                continue
            buf.append(c)
            i += 1
            ended_with_delimiter = False
        fields.append("".join(buf))

        # Drop a trailing empty field produced by a final unescaped delimiter.
        # We only drop the LAST one to preserve interior empties (which are
        # meaningful: 'a||b' has an explicit empty field at index 1).
        if ended_with_delimiter and len(fields) >= 2:
            fields.pop()
        return fields

    def get(self, index: int, default: Optional[str] = None) -> Optional[str]:
        """Return the field at 1-based index, or default if absent.

        HL7 field indices are 1-based (PID-3 is the third field). Index 0 is
        the segment name. Out-of-range indices return the default rather than
        raising -- callers commonly ask for optional fields that may be absent.
        """
        if not isinstance(index, int):
            raise TypeError(
                f"index must be int, got {type(index).__name__}"
            )
        if index < 0:
            return default
        if index >= len(self.fields):
            return default
        return self.fields[index]

    def as_dict(self) -> dict:
        """Return a mapping of 1-based index -> value for non-name fields.

        Useful for diagnostics and serialization. Excludes index 0 (name).
        """
        return {i: v for i, v in enumerate(self.fields) if i != 0}

    def __iter__(self):
        return iter(self.fields)

    def __len__(self) -> int:
        return len(self.fields)

    def __getitem__(self, index):
        return self.fields[index]

    def __repr__(self) -> str:
        return f"Segment(name={self.name!r}, fields={self.fields!r})"


def parse_segment(
    raw: str,
    field_delimiter: str = "|",
    component_delimiter: str = "^",
    repetition_delimiter: str = "~",
    escape_char: str = "\\",
) -> List[str]:
    """Parse a single HL7 v2 segment line into a list of fields.

    Convenience wrapper around Segment(raw, ...).fields. Honors custom
    delimiters and the escape character. See Segment for policies.
    """
    return Segment(
        raw,
        field_delimiter=field_delimiter,
        component_delimiter=component_delimiter,
        repetition_delimiter=repetition_delimiter,
        escape_char=escape_char,
    ).fields
