# C0DATA Conformance Vectors

Language-agnostic golden fixtures for the C0DATA spec, the normative
companion to DESIGN.md's "Canonical Form" section. Every implementation
(Crystal, Go, JS, Rust, …) should consume these files verbatim; a codec
that passes them is conforming, and two conforming codecs produce
identical bytes for the same data — the property content addressing
depends on.

## Generating

The cases are written in glyph form in `gen.py` and the JSON files are its
output. Edit `gen.py`, run `python3 vectors/gen.py`, commit both.

## Encoding conventions

- **Buffers** (`bytes`, `canonical`, `blocks[]`, `tail`) are lowercase hex
  strings of compact-form bytes.
- **Values** are the **logical** value: the inside of a text with its DLE
  escapes decoded, or the plain value with layout trimmed. A value is a
  JSON string (UTF-8; control characters as `\u001f`-style escapes),
  `{"hex": "..."}` for bytes that are not valid UTF-8, or
  `{"level": {"headers": [...] | null, "records": [...]}}` for a nested
  level (DLE … CAN) holding records, `{"level": {"files": [...]}}` for one
  holding files and groups (same shape as a decode case's `files`), or
  `{"ref": "group"}` for a group reference (ENQ plain) or
  `{"ref": {"level": ...}}` for a path (ENQ level), the pattern reported
  as the level it is written as.
- **Records** are a JSON array (positional) or `{"keys": [[k, v], ...]}`
  (keyed, SOH units, in written order). A record's units are the **result**
  after supersession: a superseded unit (`old␚␟new`) is not listed, nor is
  a superseded record, group, file or keyed unit; the cases under
  `supersede-*` fix this.
- **Headers** come from a header row, `SOH RS`.
- A **heading** is `[[key, value], ...]` in written order; absent means no
  SYN.
- Every file has a `version` (2) and a `cases` array; every case has a
  unique `name` and a human `desc`.

## Files

### decode.json

Compact bytes → expected structure. Case shape:

```json
{
  "name": "...", "desc": "...",
  "bytes": "<hex>",
  "file": "dbname" | null,
  "heading": [["shape", "stream"], ...],      // optional
  "groups": [
    {"name": "users", "headers": ["a", "b"] | null,
     "records": [["field", {"hex": "00"}], {"keys": [["k", "v"]]}, ...]}
  ],
  "files": [{"name": "a", "groups": [...]}, ...],   // optional: several FS files
  "documents": [{"heading": [...], "file": ..., "groups": [...]}, ...],
                                               // optional: a multi-document container
  "tail": "<hex>"                              // optional: raw bytes after EM
}
```

A group may carry `"sections": [...]`, its GS-repeated subsections, each
of the same shape. A section with `"name": null` is a skipped depth: no
group stands there and a reader reports none; the harness descends into
its `sections` without expecting a group. When `files` or `documents` is present, `file` and
`groups` describe the first file of the first document (and are empty
when `documents` is given).

A single group with `"name": ""` and `"file": null` means the buffer is
a bare record stream. Expected records follow the contract exactly: N
separators = N+1 fields; an empty record is one empty field; whitespace
touching a code is layout and never appears in a value; ETB, EOT, SYN
and BEL notes and dead elements are framing and never appear in names, headers, or
fields; a keyed record reports its units as written, duplicates
included (a map lookup resolves last-wins with a warning).

### encode.json

Logical structure → expected canonical bytes. Case shape:

```json
{
  "name": "...", "desc": "...",
  "build": {"file": "db" | null, "heading": [[k, v], ...] | absent,
            "groups": [{"name": "g", "headers": [...] | null,
                        "records": [[...] | {"keys": [[k, v], ...]}]}]},
  "canonical": "<hex>",
  "bytes": "<hex>"        // only with a heading: the whole file, SYN … EOT
}
```

A conforming encoder MUST produce exactly `canonical`: a value is plain
when it has no byte below 0x20 and no edge whitespace, otherwise text
with only STX, ETX, DLE, ETB, EOT, SYN and EM escaped; order preserved
exactly, keyed entries included; no layout, no framing. A `build` with a
`heading` also specifies `bytes`, the file as written: SYN, the heading
in the order given, the body, EOT.

### canonical.json

Canonicality classification. Case shape:

```json
{"name": "...", "desc": "...", "bytes": "<hex>",
 "wellformed": true, "canonical": false}
```

`wellformed` — the bytes tokenize without error. `canonical` — the
bytes are a canonical document unit (well-formed, one spelling per
value, keys unique within a keyed record, no layout, no framing, no
comments). Key order is never a canonicality question.

### invalid.json

Bytes that MUST be rejected by a document reader: `{"name", "desc",
"bytes"}` — parsing raises (unassigned code, DLE before the wrong byte
inside or outside text, layout code inside a plain value, unbalanced
text or level, framing inside open text or a level, a mixed record, a
key without a value, a name written as text, SUB before anything but a
separator or opener or with nothing to supersede, bytes
after EOT, BEL before a non-element). A stream reader reports the same
shapes in an uncommitted tail as torn rather than as errors.

### stream.json

Stream-mode (ETB commit) semantics. Case shape:

```json
{"name": "...", "desc": "...", "bytes": "<hex>",
 "committed_end": 6, "torn": false,
 "blocks": ["<hex>", ...],
 "damaged": [0],          // optional: blocks cut by an ETB inside open text or a level
 "records": [[...]] }
```

`committed_end` — offset just past the last ETB and its payload. `torn`
— data trails the last commit (a tail of layout, notes, EOT or EM alone is
not torn), including a tail that leaves text or a level open or ends in a
lone DLE. `blocks` — each committed
block's bytes (previous commit to ETB, marker and payload excluded).
An unescaped ETB is always a commit, inside text or a level too. A
committed block that is not well-formed, whether cut by its ETB inside
open text or holding any other error, is listed by index in `damaged`.
`records` (optional) — logical records of the committed region, headings,
header rows and damaged blocks excluded; a reader reports a damaged block
and continues past it only when asked, which the harness does.

### diff.json

C0DIFF application (`DIFF.md`): a diff parses under the base grammar;
these cases exercise its meaning and its constraint list. Case shape:

```json
{"name": "...", "desc": "...",
 "files": {"path": "contents before", ...},
 "diff": "<hex>",
 "result": {"path": "contents after", ...}   // or
 "error": true}
```

`files` and `result` are UTF-8 strings (the cases use text files). A
conforming diff tool given `files` and `diff` produces exactly `result`,
or refuses without writing when `error` is true. The cases are generated
by a reference applier in `gen.py` that follows `DIFF.md` literally.

### nested.json

Nested levels (DLE … CAN) in a single record, and the list convenience. Case shape:

```json
{"name": "...", "desc": "...", "bytes": "<hex>",
 "record": ["scalar", {"list": ["item", ...]}, {"level": {...}}, ...],
 "canonical": true}
```

`bytes` is a bare record stream holding one record. `record` is its
expected logical fields: `{"list": [...]}` is a level holding at most
one positional record (an empty level is the empty list), read with the list accessor (`Record#list` or its
equivalent) and written with the builder's list-field writer;
`{"level": ...}` is any other level, read with the general accessor
(the list accessor rejects it). `canonical` — when true, building the
record MUST produce exactly `bytes`. When false the case is decode-only.
