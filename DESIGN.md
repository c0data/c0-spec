# C0DATA Specification (Draft)

C0DATA is a data system built on ASCII C0 control codes. It provides concise,
structured representation for common data forms — tabular data, hierarchical
documents, diffs, configuration, logs — using single-byte control codes as
delimiters and UTF-8 text for values.

It sits between human-readable text formats (JSON, YAML, TOML) and opaque
binary formats (protobuf, msgpack). Values remain plain text. Structure is
expressed through control bytes — compact, zero-copy friendly, and inspectable
with minimal tooling.

This revision (2026-10) is the pre-1.0 redesign. Its reasoning is recorded in
`notes/PROPOSAL-*.md`; this document is the normative result.


## Design Principles

- **Preserve the original semantics of C0 control codes.** Each assigned code
  does what its ASCII name says, or the nearest thing the name allows.
- **One meaning per code.** No code's meaning depends on its contents, and no
  mechanism is shared between two jobs.
- **Only assign codes that earn their place.** The rest stay reserved.
- **Start-delimited.** A code introduces what follows it and owns the text up
  to the next code. Nothing is closed except text and nested levels.
- **Outside text, a control code is never data.** Every byte below 0x20 belongs
  to the format: structure, framing, layout, or an error. Data that must hold
  such a byte is text.
- **Metadata is out of line.** What a reader must know before reading goes in
  the heading before the data; what can only be known after writing goes in
  the commit payload after a block. Declare before, attest after. Nothing is
  annotated in line.
- **Structure is determinable with bounded lookbehind outside text, and
  framing is determinable everywhere.** Chunked scanning, SIMD acceleration
  and mid-buffer resynchronisation depend on this.
- **Both self-describing and positional usage.** Keys and headers are
  optional; positional data pays nothing for them.
- **One vocabulary, many shapes.** Table, document, map, diff, log, container.
- **Versions are additive** (adopted at 1.0). A later version may add forms
  but may never change the meaning of bytes valid under an earlier one.


## Assigned Control Codes

| Hex  | Abbr | Glyph | C0DATA Role                                              |
|------|------|-------|----------------------------------------------------------|
| 0x01 | SOH  | ␁     | Heading: a key for the value that follows, or a header row |
| 0x02 | STX  | ␂     | Start of text (a literal value)                          |
| 0x03 | ETX  | ␃     | End of text                                              |
| 0x04 | EOT  | ␄     | End of document                                          |
| 0x05 | ENQ  | ␅     | Reference (look up named data)                           |
| 0x07 | BEL  | ␇     | Comment                                                  |
| 0x0F | SI   | ␏     | Open a nested level                                      |
| 0x10 | DLE  | ␐     | Escape, inside text only                                 |
| 0x16 | SYN  | ␖     | Start of document, followed by the heading               |
| 0x17 | ETB  | ␗     | Commit marker (stream mode block terminator)             |
| 0x18 | CAN  | ␘     | Close a nested level                                     |
| 0x19 | EM   | ␙     | End of medium: a raw blob follows to end of container    |
| 0x1A | SUB  | ␚     | Substitution (old → new, in C0-DIFF)                     |
| 0x1C | FS   | ␜     | File / database separator                                |
| 0x1D | GS   | ␝     | Group / table / section separator                        |
| 0x1E | RS   | ␞     | Record / row separator                                   |
| 0x1F | US   | ␟     | Unit / field separator                                   |

Seventeen codes. HT (0x09), LF (0x0A) and CR (0x0D) are **layout** codes
outside text (see Two Forms). Every other C0 code is **unassigned**: a
reader rejects it outside text. SO (0x0E) is permanently unassigned, since a
raw SO switches many terminals into a line-drawing character set.

Pretty form shows each code as its Unicode Control Picture (U+2400 block),
listed above.


## Structural Hierarchy

The four separator codes form a fixed hierarchy:

    FS  >  GS  >  RS  >  US
    file   group  record  field

- **FS (0x1C)** — Top-level container. A database, a file, a document.
- **GS (0x1D)** — A group within a file. A table, a collection, a section.
- **RS (0x1E)** — A record within a group. A row, an entry, a block.
- **US (0x1F)** — A unit within a record. A field, a property, an element.

Every opener owns the text after it, up to the next control code. The
openers are of two kinds:

- **Container codes take a label, and their contents begin at the next
  code.** FS takes a file name, GS a group name, SI a level label (reserved,
  see Nested Levels). A label may be empty.
- **Leaf codes take the thing itself.** RS and US take a value, ENQ a name,
  BEL a comment, ETB a payload.

SOH takes a key, then its value after a US (see Records); SYN takes the
heading (see Documents). A record has no label of its own: by convention its
first field is its name.


## Documents

### Start: SYN and the heading

A document begins with **SYN (0x16)**. The text after SYN is the document's
**heading**: keyed units, each SOH, key, US, value (see Records), holding
what a reader must know before reading. The heading ends at the first code
that is not inside a keyed unit: FS, GS, RS, a header row, EOT, ETB, or BEL.
A SYN followed directly by one of those is the empty heading.

    ␖␜mydb␝users␁␞name␟amount␞Alice␟100␞Bob␟200␄        empty heading

    ␖␁shape␟stream␞alice␟100␗␞bob␟200␗                   a log

    ␖␁shape␟diff␜foo.txt␝Hello ␟world␚universe␄          a C0-DIFF

Heading keys belong to the spec. Defined keys:

| Key       | Meaning | Absent means |
|-----------|---------|--------------|
| `shape`   | which rules read the body: `diff` (C0-DIFF) or `stream` (ETB log). `tabular`, `document` and `key-value` may be given as hints; converters may use them, nothing else may act on them | unspecified; the application decides from context |
| `version` | the spec revision the document was written under | 1, permanently |
| `blob`    | the trailing blob table (see Trailing Blob) | no blob |

Heading values follow the ordinary value rules: plain, text, or a nested
level. In canonical form keys are unique and sorted bytewise; readers accept
any order.

The heading is **not** a general metadata mechanism. It holds reader
instructions only. Titles, authors, media types and the like are data and
belong in the data.

**Detection.** SYN is 0x16, which is also the first byte of a TLS record; a
TLS record continues with 0x03, which in C0DATA is ETX and can never follow
SYN. File-type and MIME detectors must therefore match two bytes.

### End: EOT

**EOT (0x04)** ends a document. In a file or message holding several
documents, each begins with its own SYN, normally after the previous
document's EOT. A reader can find document starts from any offset, since an
unescaped SYN is always a start (see Text).

### Where the markers are required

| Marker | Required | Exception |
|--------|----------|-----------|
| SYN | at the start of every file and message, logs included | none |
| EOT | at the end of every document in a file or message | logs, which have no end |

A log starts with SYN and its heading, committed with the first ETB; ETB
answers completeness block by block, so no end marker exists for a log.
Records and groups hashed on their own are slices, not files or messages,
and carry neither marker. EM implies EOT (EM is an end of input); end of
input never implies EM.

### Warnings

Readers distinguish two levels:

- A **warning** means the input is legal but not what a careful writer
  produces: layout where canonical form has none, an empty text, heading keys
  out of canonical order, a duplicate key.
- A **loud warning** means the input may not be what it claims to be: no SYN
  at the start of a file, no EOT at its end, a heading key or a `shape` or
  `version` value the reader does not know, a `blob` key in a later heading.

A library never fails on either; it parses and exposes the warning. A
command-line tool prints it. A **strict mode**, off by default, turns loud
warnings into errors and leaves ordinary warnings alone. Nothing in the
heading causes a refusal by itself: under additive versions an older reader
reads what it understands, and what it cannot read becomes an error at the
byte where it occurs.


## Two Forms: Compact and Pretty

C0DATA has two representations of the same data, under one grammar: pretty
form is compact form plus layout plus glyphs.

**Whitespace touching a control code is layout; whitespace inside text is
data.** In both forms, outside text:

- space, HT, LF and CR directly before or after a control code are layout
  and are not part of any value;
- a space anywhere else in a plain value is data (`Alice Smith` keeps its
  space);
- HT, LF or CR anywhere else in a plain value is an error: the value must be
  text.

So a plain value never carries edge whitespace, `␞Alice ␟Bob` is `Alice` and
`Bob`, and a value whose edge spaces matter, or that holds any control code,
is text (see Text). Inside a nested level the same rule applies, so nested
structure can be laid out over indented lines.

### Compact form (canonical)

The wire and storage form: a continuous byte stream with no layout bytes.
Edge whitespace on a plain value is legal, is not canonical, and draws the
ordinary warning like any other layout.

    ␖␜mydb␝users␁␞name␟amount␞Alice Smith␟1502.30␞Bob␟340.00␄

### Pretty form (human-readable)

For inspection and documentation. Uses the Control Picture glyphs, one per
code, with line breaks and indentation as layout:

    ␖␜mydb
      ␝users
        ␁␞name␟amount
        ␞Alice Smith␟1502.30
        ␞Bob␟340.00
    ␄

Text is shown exactly, including its line breaks:

    ␞note␟␂line one
    line two␃

A formatter aligns table columns and, for keyed records, aligns on the US so
that keys form one column. `c0fmt` converts between the forms.


## Records

A record is RS followed by units. A record is **positional** or **keyed**,
never mixed.

### Positional records

Units separated by US. N separators delimit N+1 units: `Alice␟` is two
fields, the second empty, and differs from `Alice`. An empty record (RS
directly followed by a structural code) is one empty field.

    ␞Alice␟1502.30␟DEPOSIT

### Keyed records (SOH)

**SOH (0x01)** introduces a keyed unit: SOH, a key, US, a value. The key is a
name (see Names). No US precedes an SOH; the next SOH ends the previous
unit by beginning another. US is the only true separator in the format and
keeps that role here: it divides the key from the value.

    ␞␁host␟localhost␁port␟5432

A keyed record is a map. In canonical form its keys are unique and sorted
bytewise. In non-canonical input a duplicate key means last wins, with a
warning. A keyed record is also legal inside the heading and inside nested
levels.

### The header row (SOH RS)

**SOH directly followed by RS** marks a record as a heading for the records
that follow it: it declares their field names, like a CSV header row.
Records under a header row are positional.

    ␝users
    ␁␞name␟amount␟type
    ␞Alice␟1502.30␟DEPOSIT
    ␞Bob␟340.00␟WITHDRAWAL

A header row may appear directly after a group label or at the top of a log.
Without one, data is positional, with the schema known to both sides:

    ␝
    ␞Alice␟1502.30␟DEPOSIT

SOH thus means one thing everywhere: **what follows is a heading for what
comes after it.** `␖␁shape␟stream` is a key heading its value in the
document heading; `␞␁host␟localhost` is a key heading its value in a record;
`␁␞name␟amount` is a record heading the records after it.

**Convention:** when no schema is provided, the first field of a positional
record is its `id`.

### Names

Labels (file and group names), keys and header names are identifiers, not
values: they contain no byte below 0x20 and no edge spaces, and are never
text.


## Text (STX … ETX)

**STX (0x02) … ETX (0x03)** is text: a string, taken literally.

    ␞greeting␟␂  hello  ␃
    ␞note␟␂line one
    line two␃

Inside text:

| Bytes | Meaning |
|-------|---------|
| any byte other than STX, ETX, DLE, ETB, EOT, SYN | that byte, as data |
| DLE followed by one of those six | that byte, as data |
| ETX, unescaped | end of the text |
| STX, unescaped | an error (text does not nest) |
| ETB, EOT, SYN, unescaped | framing: the text was cut |
| DLE followed by anything else | an error |

Every other control code is a plain byte inside text: RS, US, SI, CAN, SOH,
HT, LF, the lot. Text is needed for a value with edge whitespace, a tab, a
line break, or any control code, and for nothing else. Binary inflates by
about 2.3 percent and is read as a slice of the buffer unless it holds one
of the six.

Text is a whole value. It cannot be part of a plain value (`abc␂ x ␃def` is
malformed). An empty text, `␂␃`, is the empty string and is not canonical,
since the empty string is written as nothing.

**Framing cuts through.** An unescaped ETB is always a commit, an unescaped
EOT always ends a document, an unescaped SYN always begins one, whether
inside text, inside a nested level, or at the top. A reader that meets one
while text or a level is open knows that block is damaged. (This inverts
BISYNC's transparent mode, where a raw ETB inside text was data; the reason
is the torn log, where an open text must not swallow later commits.)

**DLE (0x10)** occurs only inside text, and only before one of the six
codes. DLE anywhere else, inside or outside text, is an error. New uses come
only with a spec revision, announced by the heading's `version`.

**Scanning.** Outside text the hot test is `byte < 0x20`. Inside text the
reader looks for six byte values. A scanner inside a nested level must skip
text whole: a raw SI, CAN, RS or US inside text is a character. A reader
entering at an arbitrary position learns where it is from the first bracket
it meets: ETX first means inside text, STX first means outside.

There is no inline size or other annotation on a text. A value large enough
to want a size, a hash, or a jump is declared in the heading's `blob` table
and carried after EM (see Trailing Blob).


## Nested Levels (SI … CAN)

**SI (0x0F) … CAN (0x18)** is a nested level: shift in, and cancel the shift
to return. Inside, the hierarchy starts over: RS, US, SOH and the rest mean
what they mean at the top, and whitespace is layout as everywhere. Levels
nest to any depth.

    ␝users
    ␁␞name␟amount␟address
    ␞Alice␟1502.30␟␏
      ␁␞street␟city
      ␞123 Main␟Springfield
    ␘
    ␞Bob␟340.00␟␏␁␞street␟city␞456 Elm␟Shelbyville␘

The format's own shapes apply inside, and nothing new is needed:

| Nested content | Written as |
|----------------|------------|
| a list | `␏␞Admin␟Editor␘`, one record |
| an empty list | `␏␘`, no record |
| a list holding one empty string | `␏␞␘` |
| a list of lists, or a table | `␏␞1␟2␞3␟4␘` |
| a table with named columns | `␏␁␞street␟city␞1 Main␟Springfield␘` |
| a map | `␏␞␁street␟1 Main␁city␟Springfield␘` |

The RS of a list is written, never assumed. A value inside a level that
needs exactness is itself text.

**Label.** Text directly after SI, before the first structural code, is the
level's label, in the same position as a file name after FS. It is
**reserved** and must be empty; a non-empty label is an error. The intended
use is a type tag, `␏rgb␞255␟0␟0␘`, should a type registry be defined. Text
after CAN belongs to no unit and is malformed, like text after ETX.

Neither SI nor CAN has any effect when printed raw on a terminal, and SI
restores a pane that a stray SO has switched to line drawing.


## References (ENQ)

**ENQ (0x05)** marks a field value as a reference to data defined elsewhere.
Referenced material must be defined **before** any reference to it, so a
single pass with no backtracking resolves every reference.

A plain name is a group:

    ␅tags

A path is the segments separated by US, fenced as text because a US would
otherwise end the field; ENQ reads its text as a path:

    ␅␂tags␟001␟label␃

group → record id → field name. A reference is hashed as the bytes it is
written in: the pointer, not the thing pointed at.

    ␝tags
    ␁␞id␟label
    ␞001␟Admin
    ␞002␟Editor

    ␝articles
    ␁␞title␟tags␟body
    ␞My Post␟␅tags␟␅␂article␟001␃


## Comments (BEL)

**BEL (0x07)** begins a comment, which runs to the end of the enclosing
element: in C0DATA the next FS, GS, RS, SOH, SYN, EOT, ETB or BEL, or the
CAN that closes the level it sits in; in a C0-DIFF the next FS or GS. A
structural code directly after the BEL belongs to the comment and has no
effect (`SOH RS`, the header-row introducer, counts as one), so a comment
is a prefix that neutralises what follows it:

    ␇␞port␟5432                 a commented-out record
    ␇␝server                    a commented-out group line
    ␇␁␞name␟amount              a commented-out header row
    ␇ see the runbook           a plain note
    ␞Alice␟␇␏␞Admin␟Editor␘     a commented-out nested value

US, text and nested levels inside a comment are content; to mention a
control code in a note, the note uses text. Framing (SYN, EOT, ETB, EM)
cannot be commented out. Comments are allowed inside nested levels and
inside committed log blocks: the ETB digest covers them, the content hash
does not. Stripping comments is a tool option, not a reader rule.


## Document Mode (Depth via GS Repetition)

For hierarchical documents (like Markdown headings), GS is repeated to
indicate depth:

    ␝         = level 1   (like #)
    ␝␝        = level 2   (like ##)
    ␝␝␝       = level 3   (like ###)

Within a section, RS marks a content block (paragraph) and US marks
sub-elements (list items) within that block.

    ␖␜My Document
    ␝Chapter 1
    ␞First paragraph of chapter one.
    ␞Second paragraph.
    ␝␝Section 1.1
    ␞A list of items:␟First item␟Second item␟Third item
    ␝␝␝Subsection 1.1.1
    ␞Deep content, kept exactly:␟␂    indented
      code␃
    ␝Chapter 2
    ␞And so on.
    ␄


## Key-Value Configuration

For configuration data (like TOML or INI), a section is a group holding one
keyed record:

    ␝database
    ␞␁host␟localhost␁port␟5432
    ␝server
    ␞␁host␟0.0.0.0␁port␟8080␁allowed_origins␟␏␞localhost␟example.com␘

A group of two-field positional records, `␞host␟localhost`, remains legal and
is a table of pairs; converters treat it as such and do not guess.


## Consistent Roles Across Shapes

| Shape      | RS means          | US means                  |
|------------|-------------------|---------------------------|
| Tabular    | row               | field / column            |
| Document   | paragraph / block | list item / element       |
| Key-Value  | the section's map | key → value (after SOH)   |
| Diff       | —                 | anchor ↔ replacement unit |


## Canonical Form (Content Addressing)

The compact form is canonical in the strong sense: **the same logical value
encodes to exactly one byte sequence**, reproducible by any conforming
encoder in any language. Two conforming encoders given the same data MUST
emit identical bytes, so the bytes may be hashed and equal hashes mean equal
values. The pretty form is presentation, never hashed. The rules:

### One Spelling per Value

A value is **plain** when it can be and **text** when it must be: a value is
plain if and only if it has no byte below 0x20 and no edge whitespace.
Inside text, DLE appears only before the six codes. Gratuitous text
(`␂only␃` for `only`), empty text, and layout bytes are non-canonical. Any
byte below 0x20 in a value requires text, assigned or not, so a future
assignment can never change what is canonical.

### Fields Are Counted by Separators

N separators delimit N+1 units. There is no "absent" field, only empty, and
arity is always significant.

### Values Are Byte Sequences

Field values are byte-transparent: conventionally UTF-8 text, but any bytes
are legal (as text where they hold a control code). A canonical encoder
performs **no Unicode normalization** and no other transformation of value
bytes. "Same logical value" means "same bytes, field by field."

### Names Are Identifiers

Labels, keys and header names contain no byte below 0x20 and no edge spaces.

### Order Is Significant

C0DATA defines **no unordered constructs** except the keyed record. Records
appear in order; positional fields and header columns are positional.
Conforming codecs MUST preserve order exactly and MUST NOT reorder.

A **keyed record** is a map, and its canonical order is defined by the
format: keys unique, sorted by ascending bytewise comparison. A codec can
check this. Other logically unordered data, a set's members or a directory's
entries encoded as positional records, is canonicalised **by the producer**
above the format (compare git tree objects, or RFC 8785 for JSON): where the
producer has no domain order and no schema, the recommended default is to
sort records bytewise by first field. This cannot be verified by the
byte-level suite; it is a contract on producers, checked at the layer that
knows the data is unordered.

### Framing and Metadata Are Outside the Hash

SYN and the whole heading, EOT, ETB markers and their payloads, BEL comments,
and EM with its blob are never part of any canonical unit's bytes. `shape`
says how to read the bytes, not what they are; the same stream transmitted
without its heading is the same stream.

### Canonical Units

- **Record** — the content bytes after its RS, up to the next structural
  code or framing byte, text and nested levels included, the RS itself
  excluded.
- **Group** — from its GS through its records (name and header row
  included), up to the next top-level GS, FS, or EOT.
- **Document** — the body: from the first byte after the heading to the
  last content byte, containing no framing bytes.

For stream logs, the hashed span of a **block** is defined in Stream Mode
and equals the framing block exactly.

The contract is only credible across implementations with shared golden
fixtures; the language-agnostic conformance suite is the normative companion
to this section.


## Stream Mode (ETB Commits)

C0DATA records are start-delimited: RS begins a record, and nothing marks its
end except the next control code or end of input. For an append-only log, a
process can crash mid-append, and a truncated final record is
indistinguishable from a complete one. Stream mode closes this gap with
**ETB (0x17)** as an explicit commit marker.

### The Commit Rule

ETB commits the **block** of bytes appended since the previous ETB (or the
start of the stream). A block is typically one record, but may be several;
committing N records with a single trailing ETB makes the batch atomic.

    ␖␁shape␟stream␁␞op␟id␟at␗
    ␞create␟a1b2c3␟1718208000␗
    ␞name␟draft-2␟1718208042␗
    ␞tag␟alpha␟17182080             ← torn tail: no ETB, skipped

- A block is **complete** if and only if it is terminated by ETB.
- **Readers** MUST treat a trailing block with no terminating ETB as torn
  and skip it. A tail that leaves text or a level open, or ends in a lone
  DLE, is torn in the same way.
- **Writers** MUST verify the stream ends at an ETB before appending, by
  truncating an uncommitted tail or by appending from the last ETB position.
  Appending after an unrepaired tail is non-conforming: an open text in the
  tail would fuse the fragment with the new block into one committed,
  corrupt block.
- A block and its ETB SHOULD be issued as a single append.

Because framing cuts through text and levels, an unescaped ETB is always a
commit: a torn text cannot hide later commits, damage is confined to one
block, and the last commit can be found by scanning backward from the end.
The commit rule applies to every appended unit, the heading and a header row
included.

### ETB Payload

ETB may be followed by an **integrity payload**, terminated by the next
control code. An empty payload means the ETB is framing-only. Payload
semantics (a checkpoint hash of the preceding block; see Speculations) are
not yet specified, but the grammar is fixed so that framing-only readers
remain forward-compatible.

When payload semantics are specified, the hashed **span** is the block
exactly as framing defines it: every byte after the previous ETB's payload
(or from the start of the stream) up to but not including this ETB, the
marker and payload excluded.

### Relationship to the Rest of C0DATA

ETB is framing, not data. Outside stream mode, parsers MUST tolerate a
framing-only ETB as a no-op at any record boundary, so a log is readable by
ordinary tooling. Stream mode gives **crash consistency**; it does not give
durability (the application's fsync discipline) or integrity (until
checkpoint payloads are specified).


## Trailing Blob (EM)

**EM (0x19)** is the end of all C0DATA on the medium. Every byte after it,
to the end of the container, is one raw region: no escapes, no framing, no
scanning. A reader stops at EM. There is one EM per container, since a
second would be a byte inside the raw region.

The region is declared in the **first document's heading** under the key
`blob`, a nested table with one row per blob: `name`, `offset`, `length`,
and an optional `hash` (`<alg>:<hex>`, the ETB payload form). Offsets are
relative to the first byte after EM. Rows may overlap, may leave gaps for
alignment, and may be zero length.

    ␖␁blob␟␏␁␞name␟offset␟length␟hash
      ␞lamp␟0␟3072000␟sha256:cd34…
      ␞desk␟3072000␟1900000␟sha256:ef56…␘␄
    ␖␜catalogue␝items␁␞name␟photo␞Lamp␟lamp␞Desk␟desk␄
    ␙…raw…

Blobs belong to the container, not to a document: any document may reference
any blob by name, and a reference is data resolved by the library. For a
container of several documents the recommended form is a heading-only first
document, as above; a single document writes the table into its own heading.
A `blob` key in a later heading is a loud warning. Alignment is the writer's
choice.

Before trusting a blob byte a reader checks that the container holds at
least the largest offset plus length past EM, and that each row's hash, if
present, matches. The blob is outside every canonical unit; the container is
write-once, since nothing can be appended after EM. EM implies EOT.

Inline text and the trailing blob are complementary: text for data in
transit, consumed whole; EM for packaging; files beside the data for a
store (see Speculations, sidecar pattern).


## C0-DIFF (Atomic Multi-File Edits)

C0-DIFF is a control-code markup format for atomic multi-file edits. It uses
sequential anchored patterns: literal text acts as anchors that must match
exactly once, and SUB-delimited units mark the replacements.

### Format

    ␖␁shape␟diff
    ␜<filepath>␝<anchor>␟<old>␚<new>␟<anchor>
    ␄

US separates the units of the pattern, anchor text from replacement units.
**SUB (0x1A)** is the substitution operator within a unit: old, SUB, new.
Each anchor, old and new is a value under the ordinary rules: plain, or text
where it holds a line break, a tab, edge whitespace or a control code.

    ␖␁shape␟diff
    ␜foo.txt
    ␝Hello ␟world␚universe␟!
    ␜main.cr
    ␝␂  def run
    ␃␟␂    return 0␃␚␂    return 1␃
    ␄

The first means: in `foo.txt`, find `Hello world!` and replace `world` with
`universe`. Sections within a file are sequential anchored patterns.
Multiple files can be edited in one document. All files are validated before
any writes happen (atomic rollback).

A diff SHOULD carry `shape␟diff`; a diff tool accepts an unspecified shape
and refuses a contradicting one. A comment in a diff ends at the next FS or
GS.

### Relationship to C0DATA

FS and GS keep their structural meanings, US its unit role, text its
meaning. SUB takes a diff-specific role aligned with its original C0
semantic, substitution. A replace-all form is not yet defined; it must not
reuse the text or level brackets.


## A Full Example (Database)

    ␖␜mydb
    ␝users
    ␁␞name␟amount␟type
    ␞Alice␟1502.30␟DEPOSIT
    ␞Bob␟340.00␟WITHDRAWAL
    ␝products
    ␁␞id␟product␟qty
    ␞01␟Widget␟100
    ␞02␟Gadget␟250
    ␄


## Data Shapes

C0DATA is a system, not a single format. The same vocabulary expresses:

| Shape      | Primary Codes Used              | Analogous To          |
|------------|---------------------------------|-----------------------|
| Tabular    | FS, GS, SOH RS, RS, US          | CSV, SQL results      |
| Document   | FS, GS×N, RS, US                | Markdown, outlines    |
| Key-Value  | GS, RS, SOH                     | TOML, INI             |
| Nested     | SI/CAN, any inner codes         | JSON objects, arrays  |
| Text       | STX/ETX                         | quoted strings, blobs in transit |
| Reference  | ENQ, text for paths             | foreign keys, links   |
| Diff       | FS, GS, US, SUB                 | unified diff, patches |
| Stream     | RS, US, ETB                     | NDJSON, SSE, WAL      |
| Container  | SYN heading, EM                 | tar, zip, PDF streams |


## Open Questions

- **Replace-all in C0-DIFF:** a notation for replacing every match within a
  bounded scope. Must not reuse brackets.
- **Level labels:** what a type tag after SI would mean, and whether a
  registry of tags belongs to the spec.
- **Inline metadata:** none exists by design; whether any mechanism could
  carry it without the costs that rejected annotations.


## Speculations

The following ideas are not part of the spec.

### Checkpoint Hashes (Integrity Verification)

The ETB payload could carry a **hash of the preceding block**, so a receiver
verifies integrity at each checkpoint, not just truncation at the tail.

    ␝users␁␞name␟amount␞Alice␟1502.30␞Bob␟340.00␗<hash>

Constraints settled with a real consumer (transfs): integrity, not security
(tamper-evidence belongs above); algorithm-tagged (`<alg>:<hex>`,
multihash-style); blocks independent, no chaining (a consumer that wants a
chain includes the previous hash in its own records); span is the framing
block. The payload is text, not raw digest bytes, to keep "payload
terminated by the next control code".

### Blob Sidecar Pattern

For a store of many or large blobs, keep each in its own file or
content-addressed object and describe it with ordinary rows:

    ␝blobs␁␞name␟location␟length␟hash
    ␞image-001␟sha256:ab12…␟4096␟sha256:ab12…
    ␞audio␟media/audio.opus␟18000␟sha256:cd34…

Fields point at a blob with an ordinary path reference,
`␅␂blobs␟image-001␃`. Each blob is independently memory-mappable, cacheable
and deduplicated, and every existing tool handles it. The columns match the
heading's `blob` table, so a sidecar row becomes a trailing-blob row by
replacing `location` with `offset`.

### Type Discrimination (Numbers vs Text)

All values are text. If type information is ever needed, the reserved label
after SI (`␏rgb␞255␟0␟0␘`) is the position held for it; a header-level
convention (`␁␞name:s␟amount:n`) is the alternative. Today the application
decides, as JSON numbers are simply unquoted text.


## Original C0 Control Code Reference

| Dec | Hex  | Abbr | Name                 | Original Purpose                                    |
|-----|------|------|----------------------|-----------------------------------------------------|
| 0   | 0x00 | NUL  | Null                 | Filler / do nothing                                 |
| 1   | 0x01 | SOH  | Start of Heading     | Beginning of message header                         |
| 2   | 0x02 | STX  | Start of Text        | End of header, start of body                        |
| 3   | 0x03 | ETX  | End of Text          | End of message body                                 |
| 4   | 0x04 | EOT  | End of Transmission  | Transmission complete                               |
| 5   | 0x05 | ENQ  | Enquiry              | Request identification / status                     |
| 6   | 0x06 | ACK  | Acknowledge          | Confirm correct receipt                             |
| 7   | 0x07 | BEL  | Bell                 | Alert the operator                                  |
| 8   | 0x08 | BS   | Backspace            | Move cursor back one space                          |
| 9   | 0x09 | HT   | Horizontal Tab       | Move to next tab stop                               |
| 10  | 0x0A | LF   | Line Feed            | Advance to next line                                |
| 11  | 0x0B | VT   | Vertical Tab         | Move to next vertical tab stop                      |
| 12  | 0x0C | FF   | Form Feed            | Eject page / start new page                         |
| 13  | 0x0D | CR   | Carriage Return      | Return to beginning of line                         |
| 14  | 0x0E | SO   | Shift Out            | Switch to alternate character set                   |
| 15  | 0x0F | SI   | Shift In             | Switch back to standard character set               |
| 16  | 0x10 | DLE  | Data Link Escape     | Next character is data, not control                 |
| 17  | 0x11 | DC1  | Device Control 1     | XON (resume transmission)                           |
| 18  | 0x12 | DC2  | Device Control 2     | Device-specific                                     |
| 19  | 0x13 | DC3  | Device Control 3     | XOFF (pause transmission)                           |
| 20  | 0x14 | DC4  | Device Control 4     | Device-specific                                     |
| 21  | 0x15 | NAK  | Negative Acknowledge | Report receive error                                |
| 22  | 0x16 | SYN  | Synchronous Idle     | Maintain timing sync                                |
| 23  | 0x17 | ETB  | End Trans. Block     | End of data block                                   |
| 24  | 0x18 | CAN  | Cancel               | Preceding data invalid                              |
| 25  | 0x19 | EM   | End of Medium        | Physical end of storage                             |
| 26  | 0x1A | SUB  | Substitute           | Replacement for invalid character                   |
| 27  | 0x1B | ESC  | Escape               | Introduces escape sequence                          |
| 28  | 0x1C | FS   | File Separator       | Highest-level data separator                        |
| 29  | 0x1D | GS   | Group Separator      | Second-level data separator                         |
| 30  | 0x1E | RS   | Record Separator     | Third-level data separator                          |
| 31  | 0x1F | US   | Unit Separator       | Lowest-level data separator                         |
| 127 | 0x7F | DEL  | Delete               | Erase character (punch all holes)                   |
