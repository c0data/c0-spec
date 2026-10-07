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
  level (SI … CAN).
- **Records** are a JSON array (positional) or `{"keys": [[k, v], ...]}`
  (keyed, SOH units, in written order).
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
  "tail": "<hex>"                              // optional: raw bytes after EM
}
```

A single group with `"name": ""` and `"file": null` means the buffer is
a bare record stream. Expected records follow the contract exactly: N
separators = N+1 fields; an empty record is one empty field; whitespace
touching a code is layout and never appears in a value; ETB, EOT, SYN
and BEL comments are framing and never appear in names, headers, or
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
with only STX, ETX, DLE, ETB, EOT and SYN escaped; keyed records sorted
bytewise by key; order otherwise preserved; no layout, no framing. A
`build` with a `heading` also specifies `bytes`, the file as written:
SYN, the heading with sorted keys, the body, EOT.

### canonical.json

Canonicality classification. Case shape:

```json
{"name": "...", "desc": "...", "bytes": "<hex>",
 "wellformed": true, "canonical": false}
```

`wellformed` — the bytes tokenize without error. `canonical` — the
bytes are a canonical document unit (well-formed, one spelling per
value, keyed records sorted and unique, no layout, no framing, no
comments).

### map-canonical.json

Producer-level canonicalization of maps. Case shape:

```json
{
  "name": "...", "desc": "...",
  "group": "database" | null,
  "map": [["key", "value"], ...],
  "canonical": "<hex>"
}
```

A `key` is a name (a JSON string). A `value` is a JSON string,
`{"hex": "..."}`, or `{"map": [[k, v], ...]}` for a nested map. Entries
are given in **input (pre-sort) order**; a conforming producer MUST emit
exactly `canonical`: one keyed record, keys sorted bytewise, a nested
map as a level holding one keyed record, values plain or text per the
encode rules. Since a keyed record is the format's own map, this is now
checkable by the codec as well as by the JSON object ↔ C0 mapping.

### invalid.json

Bytes that MUST be rejected: `{"name", "desc", "bytes"}` — tokenizing
raises (unassigned code, DLE outside text or before the wrong byte,
layout code inside a plain value, unbalanced text or level, a label
after SI, a mixed record, a key without a value, a name written as
text).

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
— uncommitted bytes trail the last commit, including a tail that leaves
text or a level open or ends in a lone DLE. `blocks` — each committed
block's bytes (previous commit to ETB, marker and payload excluded).
An unescaped ETB is always a commit, inside text or a level too; a block
so cut is listed in `damaged`. `records` (optional) — logical records of
the committed region, headings and header rows excluded.

### nested.json

Nested levels in a single record, and the list convenience. Case shape:

```json
{"name": "...", "desc": "...", "bytes": "<hex>",
 "record": ["scalar", {"list": ["item", ...]}, {"level": {...}}, ...],
 "canonical": true}
```

`bytes` is a bare record stream holding one record. `record` is its
expected logical fields: `{"list": [...]}` is a level holding exactly
one positional record, read with the list accessor (`Record#list` or its
equivalent) and written with the builder's list-field writer;
`{"level": ...}` is any other level, read with the general accessor
(the list accessor rejects it). `canonical` — when true, building the
record MUST produce exactly `bytes`. When false the case is decode-only.
