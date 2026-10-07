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
| 0x07 | BEL | ␇ | Comment |
| 0x0F | SI  | ␏ | Open a nested level |
| 0x10 | DLE | ␐ | Escape, inside text only |
| 0x16 | SYN | ␖ | Start of document, then the heading |
| 0x17 | ETB | ␗ | Commit marker (stream mode) |
| 0x18 | CAN | ␘ | Close a nested level |
| 0x19 | EM  | ␙ | End of medium: raw blob follows |
| 0x1A | SUB | ␚ | Substitution (C0DIFF) |
| 0x1C | FS  | ␜ | File / Database separator |
| 0x1D | GS  | ␝ | Group / Table / Section separator |
| 0x1E | RS  | ␞ | Record / Row separator |
| 0x1F | US  | ␟ | Unit / Field separator |

HT, LF and CR are layout outside text. Every other C0 code is unassigned
and a parser rejects it outside text. Inside text every code is a plain
byte except six (see Text).

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
Every code owns the text after it, up to the next code.

### Documents

A document starts with SYN and ends with EOT. The text after SYN is the
**heading**, keyed units the reader must know before reading. An empty
heading is just `␖`.

```
␖␜mydb␝users␁␞name␟amount␞Alice␟100␄          empty heading
␖␁shape␟stream␞alice␟100␗␞bob␟200␗             a log (no EOT: logs have no end)
␖␁shape␟diff␜foo.txt␝Hello ␟world␚universe␄    a C0DIFF
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

- space, HT, LF, CR directly before or after a control code are layout;
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
| Nested     | SI/CAN, any inner codes    | JSON objects, arrays |
| Text       | STX/ETX                    | quoted strings       |
| Reference  | ENQ, text for paths        | foreign keys, links  |
| Diff       | FS, GS, US, SUB            | unified diff, patches|
| Stream     | RS, US, ETB                | NDJSON, SSE, WAL     |
| Container  | SYN heading, EM            | tar, zip             |

### Tabular (header row present)

`␁␞` at the start of a group is a header row: it declares field names, and
the records after it are positional against them, like a CSV header.

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
positional or keyed, never mixed. Keys in canonical form are unique and
sorted.

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
written as text. Inside text every byte is data except six, which take a
DLE in front: STX, ETX, DLE, ETB, EOT, SYN. Text does not nest.

```
␞Alice␟␂  padded  ␃
␞script␟␂#!/bin/sh
echo "a	b"␃
```

### Nested values (SI/CAN)

When a field value is itself structured, wrap it in SI/CAN. Inside the
brackets, the hierarchy starts over. Levels nest for arbitrary depth. A list
is one record; a table is several; a map is a keyed record.

```
␝users
  ␁␞name␟roles␟address
  ␞Alice␟␏␞Admin␟Editor␘␟␏␁␞street␟city␞123 Main␟Springfield␘
```

`␏␘` is an empty list; `␏␞␘` is a list holding one empty string. The text
position directly after `␏` is reserved and must be empty.

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

BEL begins a comment that runs to the end of the enclosing element (the next
FS, GS, RS, SOH, SYN, EOT, ETB, BEL, or the closing CAN). A code directly
after the BEL belongs to the comment, so a BEL in front of a record, group
line, header row or nested value comments it out.

```
␇ settings for staging
␝server
  ␇␞␁host␟old.example.com
  ␞␁host␟0.0.0.0␁port␟8080
```

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
␖␁blob␟␏␁␞name␟offset␟length␟hash␞lamp␟0␟3072000␟sha256:cd34…␘
␜catalogue␝items␁␞name␟photo␞Lamp␟lamp␄
␙…raw bytes…
```


---

## C0DIFF

C0DIFF provides atomic multi-file edits using **anchored patterns**. Instead
of line numbers (which shift), you provide literal context text as anchors
surrounding the parts you want to change.

### How It Works

A section is a sequence of **units** separated by US. Each unit is either:

- **Anchor text** -- literal content that must match exactly (provides context)
- **Substitution** -- `old[SUB]new` (the part that actually changes)

Units are concatenated to build a search pattern. The pattern must match
**exactly once** in the file. Then only the SUB-marked parts are replaced.
Each anchor, old and new is an ordinary value: plain, or text when it holds
a line break, a tab, edge whitespace or a control code.

### Example

Given a file `greeting.txt` containing `Hello world!`:

```
␖␁shape␟diff
␜greeting.txt
  ␝Hello ␟world␚universe␟!
␄
```

This breaks down as:

| Unit | Type | Search contributes | Replacement contributes |
|------|------|-------------------|------------------------|
| `Hello ` | anchor | `Hello ` | `Hello ` |
| `world␚universe` | substitution | `world` | `universe` |
| `!` | anchor | `!` | `!` |

Search pattern: `Hello world!` (must match exactly once).
Replacement: `Hello universe!` (only `world` → `universe` changes).

### Anchors

You can anchor on one side, both sides, or use multiple substitutions:

```
# Anchor before only (enough if "def run" is unique in context)
␝␂class App
  def ␃␟run␚start

# Anchors before and after (more precise)
␝Hello ␟world␚universe␟!

# Multiple substitutions in one section
␝x = ␟10␚20␟ + ␟5␚15
# Finds "x = 10 + 5", produces "x = 20 + 15"
```

Note that `Hello ` keeps its trailing space only because it is followed by
US, where the space is data: whitespace next to a code is layout, so an
anchor that begins or ends with whitespace, or spans lines, is written as
text, as in the first example.

### Atomicity Guarantee

1. **Validate first** -- every section's search pattern is checked against
   every target file. Each pattern must match **exactly once**. Zero
   matches → error. Multiple matches → error.
2. **Apply only if all pass** -- if any pattern in any file fails validation,
   **nothing is modified**. No partial writes, no half-applied diffs.
3. **Then write** -- all replacements are applied and files are written.

A C0DIFF document is an all-or-nothing transaction across multiple files.

### Relationship to C0DATA

C0DIFF shares the same control code vocabulary. FS and GS retain their
structural meanings (file boundary, section/group boundary). US retains
its role as a unit-level separator. Text is the same mechanism. SUB takes
on a diff-specific role that aligns with its original C0 semantic --
substitution. A diff should carry `shape␟diff` in its heading.


---

## Escaping (DLE)

DLE (0x10) exists only inside text, where it precedes one of six codes to
make it a data byte: STX, ETX, DLE, ETB, EOT, SYN. Outside text no control
code is data, and a DLE is an error.

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
  ␞Alice␟␏␞Admin␟Editor␘␟␏␞␁street␟123 Main␁city␟Springfield␘
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

Command-line tool for converting and inspecting C0DATA.

### Build

```sh
crystal build src/c0fmt.cr -o bin/c0fmt --release
```

### Commands

#### import

```
c0fmt import [format] [file]
```

Import CSV, JSON, or YAML into C0DATA compact format.

- **format** -- `csv`, `json`, or `yaml`. Optional: auto-detected from file
  extension (`.csv`, `.json`, `.yaml`, `.yml`) or content sniffing.
- **file** -- input file. Reads stdin if omitted.
- **-o FILE** -- write output to file instead of stdout.
- **-g NAME** -- group name (defaults to filename stem or `data`).

```sh
c0fmt import data.csv                      # auto-detect from extension
c0fmt import csv data.csv                  # explicit format
echo '{"a":1}' | c0fmt import              # sniff stdin (detects JSON)
cat data.csv | c0fmt import csv            # explicit format, stdin
c0fmt import data.json -g mydata           # custom group name
```

#### export

```
c0fmt export <format> [file]
```

Export C0DATA to CSV, JSON, or YAML.

- **format** -- `csv`, `json`, or `yaml`. Required.
- **file** -- input C0DATA file. Reads stdin if omitted.
- **-o FILE** -- write output to file.

```sh
c0fmt import data.csv | c0fmt export json
c0fmt export yaml data.c0
c0fmt export csv data.c0 -o data.csv
```

#### pretty

```
c0fmt pretty [file]
```

Convert C0DATA to pretty-printed Unicode form. Auto-detects whether
input is already pretty or compact.

- **-o FILE** -- write output to file.

```sh
c0fmt pretty data.c0
cat data.c0 | c0fmt pretty
```

#### compact

```
c0fmt compact [file]
```

Convert C0DATA to compact binary form.

- **-o FILE** -- write output to file.

```sh
c0fmt compact pretty.c0 -o data.c0
```

#### validate

```
c0fmt validate [file]
```

Check well-formedness of a C0DATA document. Prints `valid` to stderr
and exits 0, or prints the error and exits 1.

```sh
c0fmt validate data.c0
```

### Pipelines

Commands compose via stdin/stdout:

```sh
# CSV to JSON
c0fmt import data.csv | c0fmt export json

# JSON to pretty C0DATA
c0fmt import config.json | c0fmt pretty

# YAML to compact C0DATA file
c0fmt import settings.yml | c0fmt compact -o data.c0

# Round-trip: CSV → C0DATA → CSV
c0fmt import csv users.csv | c0fmt export csv
```


---

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
