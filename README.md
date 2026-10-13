# rust-v2

`rust-v2` parses a single HL7 v2 pipe-and-hat segment line into a list of fields, honoring custom field, component, and repetition delimiters and respecting the HL7 escape character.

```python
from rust_v2 import Segment, parse_segment

seg = Segment("PID|field1|field2|field3")
seg.name        # 'PID'
seg.fields      # ['PID', 'field1', 'field2', 'field3']
seg.get(3)      # 'field2'  (1-based; index 0 is the segment name)

fields = parse_segment("MSH|^~\\&|SENDING|RECV")
# ['MSH', '', '^~\\&', 'SENDING', 'RECV']
```

## Why this exists

HL7 v2 messages are pipe-and-hat text: fields separated by `|`, components by `^`, repetitions by `~`. Parsing one segment into fields is the first thing any HL7 consumer does, and getting the delimiter and escape handling right at this layer means downstream code can stop re-implementing it. This library does exactly that one job, on one segment at a time, with no opinion about what the fields mean.

The trade-off: this library does not split components or repetitions, and does not assemble messages from multiple segments. It is the field-splitting layer, deliberately small. Higher-level consumers handle component decomposition against a schema.

## Edge cases you will hit

- **Trailing field delimiter is discarded.** A segment written `PID|a|b|` parses to `['PID', 'a', 'b']`, not `['PID', 'a', 'b', '']`. HL7 transports commonly emit a trailing `|` before the segment terminator; treating it as a present-but-empty field would inflate every segment with a phantom trailing field. Only the last empty field is dropped — interior empties (`PID||b`) are preserved.
- **MSH-1 appears as an empty field.** Because MSH-1 is the field delimiter itself, `Segment('MSH|^~\&|...')` yields `['MSH', '', '^~\&', ...]`. This is consistent with treating `|` purely as a splitter.
- **Empty input yields `[]`, not `['']`.** A one-field segment named `''` is not a meaningful HL7 segment.
- **Escape sequences are preserved verbatim.** `\F\` in the input remains `\F\` in the field value; the character immediately following the escape character is protected from being seen as a delimiter. Full escape-sequence *translation* (e.g. `\F\` → `|`) is not performed — that is a value-layer concern.

## Running the tests

```
PYTHONPATH=src python -m unittest discover -s tests
```
