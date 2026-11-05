---
title: C0DATA Technical Reference
---

# C0DATA Technical Reference

## Format Overview

C0DATA uses ASCII C0 control codes (0x00--0x1F) as structural delimiters
with UTF-8 text values. It sits between human-readable text formats (JSON,
YAML, TOML) and opaque binary formats (protobuf, msgpack). Values are plain
text. Structure is expressed through single-byte control codes.

See [DESIGN.md](DESIGN.md) for the
full specification and future directions.

### Assigned Control Codes

| Byte | Abbr | Glyph | Role |
|------|------|-------|------|
| 0x01 | SOH | ␁ | Heading: a key for the value after it, or `␁␞` a header row |
| 0x02 | STX | ␂ | Start of text (literal value) |
| 0x03 | ETX | ␃ | End of text |
| 0x04 | EOT | ␄ | End of document |
| 0x05 | ENQ | ␅ | Reference (look up named data) |
| 0x07 | BEL | ␇ | Comment: a note, or marks the next element dead |
| 0x10 | DLE | ␐ | Recurse: open a nested level (outside text); escape (inside text) |
| 0x16 | SYN | ␖ | Start of document, then the heading |
| 0x17 | ETB | ␗ | Commit marker (stream mode) |
| 0x18 | CAN | ␘ | Close a nested level |
| 0x19 | EM  | ␙ | End of medium: raw blob follows |
| 0x1A | SUB | ␚ | Substitution (C0DIFF) |
| 0x1C | FS  | ␜ | File separator |
| 0x1D | GS  | ␝ | Group / Table / Section separator |
| 0x1E | RS  | ␞ | Record / Row separator |
| 0x1F | US  | ␟ | Unit / Field separator |

Sixteen codes. HT, LF and CR are layout outside text. Every other C0
code is unassigned and a parser rejects it outside text. Inside text
every code is a plain byte except seven (see Text).

### Structural Hierarchy

The four separator codes form a fixed hierarchy:

```
FS  >  GS  >  RS  >  US
file   group  record  field
```

- **FS (0x1C)** -- Top-level container. A database, a file, a document.
- **GS (0x1D)** -- A group within a file. A table, a collection, a section.
- **RS (0x1E)** -- A record within a group. A row, an entry, a block.
- **US (0x1F)** -- A unit within a record. A field, a property, an element.

Text immediately following FS or GS is the **label** (name) for that scope.
Every code owns the text after it, up to the next code. A document may hold
several FS files.

### Documents

A document starts with SYN and ends with EOT. The text after SYN is the
**heading**, keyed units the reader must know before reading. An empty
heading is just `␖`.

```
␖␜mydb␝users␁␞name␟amount␞Alice␟100␄          empty heading
␖␁shape␟stream␞alice␟100␗␞bob␟200␗             a log (no EOT: logs have no end)
␖␁shape␟diff␜foo.txt␝␂Hello ␃␟world␚universe␄  a C0DIFF
```

Heading keys: `shape` (`diff`, `stream`; absent means the application
decides), `version` (absent means 1), `blob` (see Trailing Blob). An
unknown key is a loud warning. SYN is required at the start of every file
and message; EOT at the end of every document except a log. A missing one
is a loud warning; strict mode makes loud warnings errors.


---

## Two Forms: Compact and Pretty

C0DATA has two representations of the same data under one grammar: pretty
form is compact form plus layout plus glyphs.

**Whitespace touching a control code is layout; whitespace inside text is
data.** Outside text, in both forms:

- space, HT, LF, CR directly before or after a control code, or at the
  start or end of input, are layout;
- a space elsewhere in a plain value is data ("Alice Smith" keeps its space);
- HT, LF or CR elsewhere in a plain value is an error: use text.

### Compact Form (Canonical)

The wire/storage format: a continuous byte stream with no layout.

```
␖␜mydb␝users␁␞name␟amount␞Alice Smith␟1502.30␞Bob␟340.00␄
```

### Pretty Form (Human-Readable)

Unicode Control Pictures (U+2400 block) for the codes, line breaks and
indentation for layout:

```
␖␜mydb
  ␝users
    ␁␞name␟amount
    ␞Alice Smith␟1502.30
    ␞Bob␟340.00
␄
```

A value with edge spaces, a tab, or a line break is text, in both forms:

```
␞␂  leading spaces  ␃␟normal value
␞note␟␂line one
line two␃
```


---

## Data Shapes

C0DATA is a system, not a single format. The same control code vocabulary
expresses multiple common data shapes.

| Shape      | Primary Codes Used          | Analogous To         |
|------------|-----------------------------|----------------------|
| Tabular    | FS, GS, SOH RS, RS, US     | CSV, SQL results     |
| Document   | FS, GS×N, RS, US           | Markdown, outlines   |
| Key-Value  | GS, RS, SOH                | TOML, INI            |
| Nested     | DLE … CAN, any inner codes | JSON objects, arrays |
| Text       | STX/ETX                    | quoted strings       |
| Reference  | ENQ, text for paths        | foreign keys, links  |
| Diff       | FS, GS, US, SUB            | unified diff, patches|
| Stream     | RS, US, ETB                | NDJSON, SSE, WAL     |
| Container  | SYN heading, EM            | tar, zip             |

### Tabular (header row present)

`␁␞` as the first item of a group is a header row: it declares field
names, and the positional records after it are read against them, like a
CSV header.

```
␝users
  ␁␞name␟amount
  ␞Alice␟100
  ␞Bob␟200
```

Without a header row, data is purely positional (schema known by both
sides). By convention the first field is the record's id.

### Keyed records (maps)

SOH inside a record introduces a keyed unit: `␁key␟value`. A record is
positional or keyed, never mixed. Keys are unique in canonical form and
stay in the order written; sorting is the producer's choice.

```
␝database
  ␞␁host␟localhost␁port␟5432
```

Two-field positional records, `␞host␟localhost`, remain legal and are a
table of pairs.

### Multi-field records (no header, N fields)

```
␝data
  ␞a␟b␟c
  ␞d␟e␟f
```

### Text (STX/ETX)

A value with edge whitespace, a line break, a tab, or any control code is
written as text. Inside text every byte is data except seven, which take
a DLE in front: STX, ETX, DLE, ETB, EOT, SYN, EM. Text does not nest.

```
␞Alice␟␂  padded  ␃
␞script␟␂#!/bin/sh
echo "a	b"␃
```

### Nested values (DLE … CAN)

When a field value is itself structured, open a nested level with DLE and
close it with CAN. DLE means *recurse*: the code after it is the first code
of a nested body, in which the hierarchy starts over. Levels nest for
arbitrary depth. A list is one record; a table is several; a map is a keyed
record; a level may even hold groups and files.

```
␝users
  ␁␞name␟roles␟address
  ␞Alice␟␐␞Admin␟Editor␘␟␐␁␞street␟city␞123 Main␟Springfield␘
```

`␐␘` is an empty level; `␐␞␘` is a list holding one empty string. DLE is
on the opener only, and must be followed by a code.

### Document (FS wrapper, depth via GS repetition)

GS repeated indicates depth level (like # in Markdown). Within a section,
RS marks a content block (paragraph) and US marks sub-elements (list items).

```
␖␜My Document
  ␝Chapter 1
    ␞First paragraph.
    ␞A list:␟Item one␟Item two
    ␝␝Section 1.1
      ␞Nested content.
  ␝Chapter 2
    ␞And so on.
␄
```

### References (ENQ)

ENQ marks a value as a reference to data defined elsewhere. Referenced
material must be defined **before** any reference to it (enabling single-pass
parsing).

Simple reference (entire group):

```
␅tags
```

Path reference (record or field within a group), fenced as text because the
US would otherwise end the field:

```
␅␂tags␟001␟label␃
```

US separates path segments: group → record id → field name.

### Comments (BEL)

BEL marks the next thing dead. BEL followed by text is a note, which ends
at the next control code like any other code's text. BEL followed by a
structural code marks that element dead: a record, group line, header row,
keyed unit, file line or nested level is parsed as written and then
discarded. A note that must hold control codes is text: `␇␂…␃`.

```
␇ settings for staging
␝server
  ␇␞␁host␟old.example.com
  ␞␁host␟0.0.0.0␁port␟8080␇ was 9090
```

Layout after the BEL is layout, so `␇␊␞x` is a dead record. BEL before
US, ETX, CAN or a framing code is an error.

### Stream logs (ETB)

ETB commits the bytes appended since the previous ETB. A trailing block
without ETB is torn and skipped; writers repair the tail before appending.
An unescaped ETB is always a commit, even inside text, so a torn text cannot
hide later commits.

```
␖␁shape␟stream␁␞op␟id␗
␞create␟a1b2␗
␞name␟draft␗
```

### Trailing Blob (EM)

Everything after EM to the end of the container is one raw region, declared
in the first document's heading under `blob` as a table of name, offset,
length and optional hash. A reader stops at EM; any document may reference
a blob by name.

```
␖␁blob␟␐␁␞name␟offset␟length␟hash␞lamp␟0␟3072000␟sha256:cd34…␘
␜catalogue␝items␁␞name␟photo␞Lamp␟lamp␄
␙…raw bytes…
```


---

## C0DIFF

C0DIFF provides atomic multi-file edits using **anchored patterns**: literal
context text surrounding the parts to change, instead of line numbers. It
is a profile of C0DATA (`shape␟diff`), specified in full in
[DIFF.md](DIFF.md).

```
␖␁shape␟diff
␜greeting.txt
  ␝␂Hello ␃␟world␚universe␟!
␜tally.rb
  ␝def tally(items)
  ␞count␚total
  ␝end
␄
```

- `␝` begins a section: a pattern of US-separated units, each an anchor or
  an `old␚new` substitution. The pattern must match exactly once after the
  previous section's match.
- `␞old␚new` after a section replaces **every** occurrence within that
  section's scope (to the next section's match, or end of file).
- Empty old inserts; empty new deletes; a section with no `␚` asserts.
- Anchors with edge whitespace or line breaks are text (`␂…␃`).
- All files are validated before any is written; any error anywhere means
  nothing is written.


---

## Escaping (DLE)

Inside text, DLE (0x10) precedes one of seven codes to make it a data
byte: STX, ETX, DLE, ETB, EOT, SYN, EM. Outside text no control code is
data, and DLE means recurse (see Nested values).

```
␞␂a␐␃b␃        the three bytes a, ETX, b
```


---

## Document Termination (EOT)

EOT (0x04) marks the end of a complete C0DATA document. Required at the end
of every document in a file or message, except a log; a missing EOT is a
loud warning. Several documents in one file or connection each begin with
their own SYN.


---

## Consistent Roles Across Shapes

The separator codes maintain consistent meaning across all data shapes:

| Shape      | RS means          | US means                  |
|------------|-------------------|---------------------------|
| Tabular    | row               | field / column            |
| Document   | paragraph / block | list item / element       |
| Key-Value  | the section's map | key → value (after SOH)   |
| Diff       | --                | anchor ↔ replacement unit |


---

## Data Shape Mapping

How C0DATA maps to and from JSON/YAML/CSV. A positional record is an array,
a keyed record is an object; nothing is guessed.

### Tabular → JSON

```
␝users
  ␁␞name␟amount
  ␞Alice␟100
  ␞Bob␟200
```

```json
{"users": [{"name": "Alice", "amount": "100"}, {"name": "Bob", "amount": "200"}]}
```

```csv
name,amount
Alice,100
Bob,200
```

### Key-Value → JSON

```
␝database
  ␞␁host␟localhost␁port␟5432
```

```json
{"database": {"host": "localhost", "port": "5432"}}
```

### Multi-field → JSON

```
␝data
  ␞a␟b␟c
  ␞d␟e␟f
```

```json
{"data": [["a", "b", "c"], ["d", "e", "f"]]}
```

### Nested → JSON

```
␝users
  ␁␞name␟roles␟address
  ␞Alice␟␐␞Admin␟Editor␘␟␐␞␁street␟123 Main␁city␟Springfield␘
```

```json
{"users": [{"name": "Alice", "roles": ["Admin", "Editor"], "address": {"street": "123 Main", "city": "Springfield"}}]}
```

### Document → JSON

```
␖␜mydb
  ␝users
    ␁␞name
    ␞Alice
  ␝products
    ␁␞id
    ␞01
␄
```

```json
{"mydb": {"users": [{"name": "Alice"}], "products": [{"id": "01"}]}}
```


---

## Performance

The tokenizer's hot loop is a single comparison: `byte < 0x20`. This makes
C0DATA inherently fast to parse -- single-byte delimiters, zero-copy
friendly, and SIMD-acceleratable.

Benchmark on 10 MB document (Crystal, --release):

```
avg         4.88 ms       2048.0 MB/s
best        4.09 ms       2447.7 MB/s
```


---

## c0fmt CLI

Command-line tool for converting and inspecting C0DATA, its own shard at
[c0data/c0-fmt](https://github.com/c0data/c0-fmt) (`shards build
--release`). Every command reads a file or stdin in either form, compact
or pretty.

```
c0fmt import [format] [file]   CSV, JSON or YAML → C0DATA (-g group name)
c0fmt export <format> [file]   C0DATA → csv (-g which group), json, yaml
c0fmt pretty [file]            compact → pretty (-a aligns table columns)
c0fmt compact [file]           pretty → compact
c0fmt validate [file]          well-formedness; -c also canonical form,
                               -s a stream log (torn tail, damaged blocks)
```

Export maps a header row to objects, a keyed record to an object, a nested
level to a list or table, and a reference to `{"$ref": "group/record"}`
(JSON, YAML) or its path (CSV). `validate` prints reader warnings (a
missing SYN heading, an unknown heading key) without failing; `-c` names
each reason a file is not canonical. Exit status is 0 when valid.

## Crystal API

For the Crystal library API documentation, see the generated
[API docs](../api/index.html).

### Installation

Add to your `shard.yml`:

```yaml
dependencies:
  c0:
    github: c0data/c0-cr
```

```crystal
require "c0"
```
