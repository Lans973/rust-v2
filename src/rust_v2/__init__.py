"""rust-v2: HL7 v2 pipe-and-hat segment parser.

Exposes:
    Segment       -- parse-and-hold representation of one HL7 v2 segment.
    parse_segment -- functional convenience wrapper returning Segment(...).fields.
"""

from .core import Segment, parse_segment

__all__ = ["Segment", "parse_segment"]
