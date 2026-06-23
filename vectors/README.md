# C0DATA Conformance Vectors

Language-agnostic golden fixtures for the C0DATA spec, the normative
companion to DESIGN.md's "Canonical Form" section. Every implementation
(Crystal, Go, JS, Rust, …) should consume these files verbatim; a codec
that passes them is conforming, and two conforming codecs produce
identical bytes for the same data — the property content addressing
depends on.

## Encoding conventions

- **Buffers** (`bytes`, `canonical`, `blocks[]`) are lowercase hex
  strings of compact-form bytes.
- **Field values** are either a JSON string (the value's bytes are its
  UTF-8 encoding; control characters appear as ``-style escapes)
  or `{"hex": "..."}` for values that are not valid UTF-8. Either way
  the expected value is the **logical** value — DLE escapes decoded.
- Every file has a `version` and a `cases` array; every case has a
  unique `name` and a human `desc`.

## Files

### decode.json

Compact bytes → expected structure. Case shape:

```json
{
  "name": "...", "desc": "...",
  "bytes": "<hex>",
  "file": "dbname" | null,
  "groups": [
    {"name": "users", "headers": ["a", "b"] | null,
     "records": [["field", {"hex": "00"}], ...]}
  ]
}
```

A single group with `"name": ""` and `"file": null` means the buffer is
a bare record stream (no FS/GS preamble). Expected records follow the
contract exactly: N separators = N+1 fields; an empty record is one
empty field; ETB commit markers and payloads are tolerated framing and
never appear in names, headers, or fields.

### encode.json

Logical structure → expected canonical bytes. Case shape:

```json
{
  "name": "...", "desc": "...",
  "build": {"file": "db" | null,
            "groups": [{"name": "g", "headers": [...] | null,
                        "records": [[...]]}]},
  "canonical": "<hex>"
}
```

A conforming encoder MUST produce exactly `canonical`: minimal escaping
(every value byte < 0x20 escaped with DLE, nothing else escaped), order
preserved, no framing bytes.

### canonical.json

Canonicality classification. Case shape:

```json
{"name": "...", "desc": "...", "bytes": "<hex>",
 "wellformed": true, "canonical": false}
```

`wellformed` — the bytes tokenize without error. `canonical` — the
bytes are a canonical document unit (well-formed, minimally escaped,
no ETB/EOT framing).

### map-canonical.json

Producer-level canonicalization of logically-unordered **maps**. Case
shape:

```json
{
  "name": "...", "desc": "...",
  "group": "database" | null,
  "map": [["key", "value"], ...],
  "canonical": "<hex>"
}
```

A `key` or `value` is a JSON string (logical bytes), `{"hex": "..."}`
(binary), or — for a `value` only — `{"map": [[k, v], ...]}` for a
nested map. The `map` entries are given in **input (pre-sort) order**; a
conforming producer MUST emit exactly `canonical`: entries sorted by
ascending byte-lexicographic order of each key's **logical (unescaped)**
bytes, nested maps sorted recursively, value bytes minimally escaped.

Unlike the other files, **these are not codec tests.** Whether a group
is an unordered map or an ordered sequence is invisible in the bytes, so
the byte-level `canonical.json` suite cannot decide them (the same bytes
are canonical as a sequence and non-canonical as an unsorted map). The
map-sort rule is a contract on *producers* — the JSON object ↔ C0
mapping, a schema-driven encoder, an application such as transfs — and
these vectors are consumed there, not by the core tokenizer/codec.
Codec-only conformance harnesses should skip this file.

### invalid.json

Bytes that MUST be rejected: `{"name", "desc", "bytes"}` — tokenizing
raises (unassigned control code, or DLE at end of input).

### stream.json

Stream-mode (ETB commit) semantics. Case shape:

```json
{"name": "...", "desc": "...", "bytes": "<hex>",
 "committed_end": 6, "torn": false,
 "blocks": ["<hex>", ...],
 "records": [[...]] }
```

`committed_end` — offset just past the last ETB and its payload.
`torn` — uncommitted bytes trail the last commit. `blocks` — each
committed block's bytes (previous commit to ETB, marker and payload
excluded). `records` (optional) — logical records of the committed
region.
