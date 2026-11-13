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
`notes/PROPOSAL-*.md`; this document is the normative result, and
`GRAMMAR.md` is its formal grammar.


## Design Principles

- **Preserve the original semantics of C0 control codes.** Each assigned code
  does what its ASCII name says, or the nearest thing the name allows.
- **One meaning per code.** No code's meaning depends on its contents, and no
  mechanism is shared between two jobs. The one code with two jobs is DLE,
  told apart by position alone: a level opener outside text, an escape
  inside it, and in both the next byte is not what it looks like.
- **Only assign codes that earn their place.** The rest stay reserved.
- **Start-delimited.** A code introduces what follows it and owns the text up
  to the next code. Nothing is closed except text and nested levels.
- **Outside text, a control code is never data.** Every byte below 0x20 belongs
  to the format: structure, framing (SYN with the heading, EOT, ETB with its
  payload, EM with its blob), layout, or an error. Data that must hold
  such a byte is text.
- **Metadata is out of line.** What a reader must know before reading goes in
  the heading before the data; what can only be known after writing goes in
  the commit payload after a block. Declare before, attest after. No
  metadata is annotated in line; a BEL note or dead mark is commentary,
  not metadata, and canonical form removes it.
- **Structure is determinable with bounded lookbehind outside text, and
  framing is determinable everywhere before EM.** Chunked scanning, SIMD
  acceleration and mid-buffer resynchronisation depend on this.
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
| 0x07 | BEL  | ␇     | Comment: a note, or marks the next element dead          |
| 0x10 | DLE  | ␐     | Recurse: open a nested level (outside text); escape (inside text) |
| 0x16 | SYN  | ␖     | Start of document, followed by the heading               |
| 0x17 | ETB  | ␗     | Commit marker (stream mode block terminator)             |
| 0x18 | CAN  | ␘     | Close a nested level                                     |
| 0x19 | EM   | ␙     | End of medium: a raw blob follows to end of container    |
| 0x1A | SUB  | ␚     | Supersede: the element before the next separator is replaced by the one after |
| 0x1C | FS   | ␜     | File separator                                           |
| 0x1D | GS   | ␝     | Group / table / section separator                        |
| 0x1E | RS   | ␞     | Record / row separator                                   |
| 0x1F | US   | ␟     | Unit / field separator                                   |

Sixteen codes. HT (0x09), LF (0x0A) and CR (0x0D) are **layout** codes
outside text (see Two Forms). Every other C0 code is **unassigned**: a
reader rejects it outside text. SO (0x0E) is permanently unassigned, since a
raw SO switches many terminals into a line-drawing character set.

Pretty form shows each code as its Unicode Control Picture (U+2400 block),
listed above.


## Structural Hierarchy

The four separator codes form a fixed hierarchy:

    FS  >  GS  >  RS  >  US
    file   group  record  field

- **FS (0x1C)** — A file within a document. A database, a bundle member.
- **GS (0x1D)** — A group within a file. A table, a collection, a section.
- **RS (0x1E)** — A record within a group. A row, an entry, a block.
- **US (0x1F)** — A unit within a record. A field, a property, an element.

Every opener owns the text after it, up to the next control code or the end
of input. The openers are of two kinds:

- **Container codes take a label, and their contents begin at the next
  code.** FS takes a file name, GS a group name. A label may be empty.
- **Leaf codes take the thing itself.** RS and US take a value, ENQ a name,
  ETB a payload, BEL a note (see Comments).

SOH takes a key, then its value after a US (see Records); SYN takes the
heading (see Documents); DLE takes nothing, the code after it is the first
code of a nested level (see Nested Levels). A record has no label of its
own: by convention its first field is its name.

A document may hold several files, each introduced by FS; records and groups
before the first FS belong to an unnamed file, and records before the first
GS of a file belong to an unnamed group.


## Documents

### Start: SYN and the heading

A document begins with **SYN (0x16)**. The text after SYN is the document's
**heading**: keyed units, each SOH, key, US, value (see Records), holding
what a reader must know before reading. The heading ends at the first code
that is neither part of a keyed unit nor a note nor a dead keyed unit: FS,
GS, RS, a header row (live or dead), EOT, ETB, EM, or SYN. A SYN followed directly by one of those is the
empty heading. A plain byte directly after SYN is an error.

    ␖␜mydb␝users␁␞name␟amount␞Alice␟100␞Bob␟200␄        empty heading

    ␖␁shape␟stream␞alice␟100␗␞bob␟200␗                   a log

    ␖␁shape␟diff␜foo.txt␞␂Hello ␃␟world␚␟universe␟!␄    a C0DIFF

Heading keys belong to the spec. Defined keys:

| Key       | Meaning | Absent means |
|-----------|---------|--------------|
| `shape`   | which rules read the body: `diff` (C0DIFF) or `stream` (ETB log); any other value is a loud warning | an ordinary document; the application decides from context |
| `schema`  | the schema the body claims to conform to: a name, or a keyed record of `name`, `url`, `hash` (see below) | unspecified |
| `version` | the spec revision the document was written under, a decimal integer | 1, permanently |
| `blob`    | the trailing blob table (see Trailing Blob) | no blob |

Heading values are plain, text, or a nested level; never a reference. Keys
are unique and stay in the order written; a duplicate key means last
wins, with a loud warning, since a duplicated `shape` changes how the body
is read. A reader ignores a key it does not know, with a loud warning.

`schema` names an external contract, the way `shape` names one of the
spec's own grammars. Its value is a plain name, or a level holding one
keyed record whose keys are drawn from `name`, `url` and `hash`, at least
one present and no others:

    ␖␁schema␟ledger
    ␖␁schema␟␐␞␁name␟ledger␁url␟https://example.org/ledger/1␁hash␟sha256:9f86…␘
    ␖␁schema␟␐␞␁url␟https://example.org/ledger/1␁hash␟sha256:9f86…␘
    ␖␁schema␟␐␞␁hash␟sha256:9f86…␘

A name is what a schema layer matches against the schemas it already
has; a url is where it fetches one it lacks; a hash is what it checks
either way. The hash is the canonical body hash of the schema document,
spelled as in the blob table (`sha256:` and hex), so a schema reformatted
or commented still matches and one with a rule changed does not. The
format checks the value's form and reports it; a schema layer resolves
however it likes, hashes what it gets, and refuses on mismatch. A
document that names a hash is pinned; one that does not has chosen to
float. Any other value under `schema` (an empty one, a level with more
than one record, a positional record, an unknown key, a value that is not
a name) is an error. There are no shape hints: a document that wants to
say what its body is names a schema.

The heading is **not** a general metadata mechanism. It holds reader
instructions only. Titles, authors, media types and the like are data and
belong in the data.

**Detection.** SYN is 0x16, which is also the first byte of a TLS record; a
TLS record continues with 0x03, which in C0DATA is ETX and can never follow
SYN. File-type and MIME detectors must therefore match two bytes.

### End: EOT

**EOT (0x04)** ends a document. After EOT only layout, another document's
SYN, or EM may follow; anything else is an error, a second document
without SYN included. In a file or message
holding several documents, each begins with its own SYN. A reader can find
document starts from any offset before EM, since an unescaped SYN is always
a start (see Text).

### Where the markers are required

| Marker | Required | Exception |
|--------|----------|-----------|
| SYN | at the start of every file and message, logs included | none |
| EOT | at the end of every document in a file or message | logs, which need no end |

"Required" binds writers: a conforming writer always emits them. A reader
accepts their absence with the loud warning below, which is how a slice is
read on its own.

A **log** is a document whose heading declares `shape` `stream`. It starts
with SYN and its heading, committed with the first ETB; ETB answers
completeness block by block, so no end marker is needed. A log may still end
with EOT after its last commit, when its writer closes it. Records and
groups hashed on their own are slices, not files or messages, and carry
neither marker. EM implies EOT (EM is an end of input); end of input never
implies EM.

### Warnings

Readers distinguish two severities:

- A **warning** means the input is legal but not what a careful writer
  produces: layout where canonical form has none, an empty text, a duplicate
  key, text around a value that could be plain.
- A **loud warning** means the input may not be what it claims to be: no SYN
  at the start of a file, no EOT at the end of a document that is not a log,
  a heading key or a `shape` or `version` value the reader does not know, a
  `blob` key in a later heading, EM with no `blob` table.

A library never fails on either; it parses and exposes the warning. A
command-line tool prints it. A **strict mode**, off by default, turns loud
warnings into errors and leaves ordinary warnings alone. Nothing in the
heading causes a refusal by itself: under additive versions an older reader
reads what it understands, and what it cannot read becomes an error at the
byte where it occurs.

A slice without SYN, such as a group or a record handled on its own, is
read by the same rules; the loud warning applies to files and messages.


## Two Forms: Compact and Pretty

C0DATA has two representations of the same data, under one grammar: pretty
form is compact form plus layout plus glyphs.

Whitespace means the four bytes space, HT, LF and CR. **Whitespace touching
a control code is layout; whitespace inside text is data.** In both forms,
outside text:

- whitespace directly before or after a control code, or at the start or
  end of input, is layout and is not part of any value;
- a space anywhere else in a plain value is data (`Alice Smith` keeps its
  space);
- HT, LF or CR anywhere else in a plain value is an error: the value must be
  text.

So a plain value never carries edge whitespace, `␞Alice ␟Bob` is `Alice` and
`Bob`, and a value whose edge spaces matter, or that holds any control code,
is text (see Text). Layout never changes the meaning of the codes around
it: `␁ ␞` is still a header row and `␝ ␝` is still depth two. Inside a
nested level the same rule applies, so nested structure can be laid out over
indented lines. Bytes at or above 0x80, non-breaking spaces included, are
data.

### Compact form

The wire and storage form: a continuous byte stream, normally with no
layout bytes. Canonical form (see Canonical Form) is a subset of compact
form; compact input may carry layout, comments and framing that canonical
form excludes.

    ␖␜mydb␝users␁␞name␟amount␞Alice Smith␟1502.30␞Bob␟340.00␄

### Pretty form

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

**Limitation.** Pretty form substitutes a glyph for each code, so a value
that itself contains one of the glyph characters (U+2400 to U+241F, or the
characters of whatever glyph set is in use) cannot be shown in that glyph
set without ambiguity. A formatter refuses such a value or chooses a glyph
set the data does not use; it never emits an ambiguous rendering.


## Records

A record is RS followed by units. A record is **positional** or **keyed**,
never mixed. A unit holds at most one value; a unit with none is empty
(`␞a␟␟b` has three units). Two values side by side with
no US between them (`␞a␂b␃`, `␞␐␞x␘y`) are malformed.

### Positional records

Units separated by US. N separators delimit N+1 units: `Alice␟` is two
fields, the second empty, and differs from `Alice`. An empty record (RS
directly followed by a structural code or the end of input) is one empty
field.

    ␞Alice␟1502.30␟DEPOSIT

### Keyed records (SOH)

**SOH (0x01)** introduces a keyed unit: SOH, a key, US, a value. The key is a
name (see Names). No US precedes an SOH, and no US follows a keyed value:
the next SOH ends the previous unit by beginning another, and `␞␁a␟1␟2` is
a mixed record. US is the only true separator in the format and keeps that
role here: it divides the key from the value.

    ␞␁host␟localhost␁port␟5432

A record is keyed when it holds at least one keyed unit, live or dead;
a record holding nothing but notes (`␞␇n`) is positional, one empty unit.
A keyed record is a map whose entries stay in the order written; the
format does not sort them. In canonical form its keys are unique. A
duplicate key means last wins, with a warning. A keyed record is also legal
inside the heading and inside nested levels.

### The header row (SOH RS)

**SOH followed by RS**, with only layout between them, marks a record as a
heading for the records that follow it: it declares their field names, like
a CSV header row.

    ␝users
    ␁␞name␟amount␟type
    ␞Alice␟1502.30␟DEPOSIT
    ␞Bob␟340.00␟WITHDRAWAL

A header row is the first live item of its group, which may be the unnamed
group at the start of a file or of a nested level, after any notes, dead
elements or commits; a header row anywhere else, live or dead, is an
error. A header row is a record of names and admits notes as any record
does: `␁␞name␇n␟amount` names two fields. It names
the fields of the positional records of its own group; a GS-repeated
subsection inherits nothing and names its own fields with its own header
row, or has none. A keyed record under a
header row is legal and names its own. The format does not check that a
record has as many fields as the header names; that is the schema layer's
business. Without a header row, data is positional, with the schema known to
both sides:

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
values: they contain no byte below 0x20 and no edge whitespace, and are
never text. A name may be empty.


## Text (STX … ETX)

**STX (0x02) … ETX (0x03)** is text: a string, taken literally.

    ␞greeting␟␂  hello  ␃
    ␞note␟␂line one
    line two␃

Inside text:

| Bytes | Meaning |
|-------|---------|
| any byte other than STX, ETX, DLE, ETB, EOT, SYN, EM | that byte, as data |
| DLE followed by one of those seven | that byte, as data |
| ETX, unescaped | end of the text |
| STX, unescaped | an error (text does not nest) |
| ETB, EOT, SYN, EM, unescaped | framing: the text was cut |
| DLE followed by anything else | an error |

Every other control code is a plain byte inside text: RS, US, CAN, SOH, BEL,
HT, LF, the lot. Text is needed for a value with edge whitespace, a tab, a
line break, or any control code, and for nothing else. Binary inflates by
about 2.7 percent and is read as a slice of the buffer unless it holds one
of the seven.

Text is a whole value. It cannot be part of a plain value (`abc␂ x ␃def` is
malformed), and it cannot stand where a name is expected. An empty text,
`␂␃`, is the empty string and is not canonical, since the empty string is
written as nothing.

**Framing cuts through.** An unescaped ETB is always a commit, an unescaped
EOT always ends a document, an unescaped SYN always begins one, an
unescaped EM always ends the medium, whether inside text, inside a nested
level, or at the top. A document reader that
meets one while text or a level is open rejects the input as malformed; a
stream reader treats the block as damaged (see Stream Mode). This inverts
BISYNC's transparent mode, where a raw ETB inside text was data; the reason
is the torn log, where an open text must not swallow later commits.

**DLE (0x10) inside text** occurs only before one of the seven codes; before
anything else it is an error. (Outside text DLE opens a nested level; see
Nested Levels.)

**Scanning.** Outside text the hot test is `byte < 0x20`. Inside text the
reader looks for seven byte values; the lookbehind needed to classify one of
them is the run of DLEs before it, whose parity says whether it is escaped,
and is bounded by the run's length. A scanner inside a nested level must
skip text whole: a raw RS, US or CAN inside text is a character. A reader
entering at an arbitrary position before EM learns where it is from the
first unescaped bracket it meets: ETX first means inside text, STX first
means outside.

There is no inline size or other annotation on a text. A value large enough
to want a size, a hash, or a jump is declared in the heading's `blob` table
and carried after EM (see Trailing Blob).


## Nested Levels (DLE … CAN)

**DLE (0x10)** outside text means *recurse*: the code after it is the first
code of a nested level, and **CAN (0x18)** closes the level. Inside, the
hierarchy starts over: the contents of a level are a document body, so
records, header rows, groups and files all mean what they mean at the top,
and whitespace is layout as everywhere. Levels nest to any depth. The DLE
is on the opener only; the codes inside carry none.

    ␝users
    ␁␞name␟amount␟address
    ␞Alice␟1502.30␟␐
      ␁␞street␟city
      ␞123 Main␟Springfield
    ␘
    ␞Bob␟340.00␟␐␁␞street␟city␞456 Elm␟Shelbyville␘

The opener says what is being recursed into, and the format's own shapes
apply inside; nothing new is needed:

| Nested content | Written as |
|----------------|------------|
| a list | `␐␞Admin␟Editor␘`, one record |
| a list holding one empty string | `␐␞␘` |
| an empty level | `␐␘`, no body |
| a list of lists, or a table | `␐␞1␟2␞3␟4␘` |
| a table with named columns | `␐␁␞street␟city␞1 Main␟Springfield␘` |
| a map | `␐␞␁street␟1 Main␁city␟Springfield␘` |
| a whole document | `␐␜name␝g␞a␘` |

DLE must be followed by FS, GS, RS, SOH, BEL (a comment) or CAN; `␐x`,
`␐␟` and `␐␗` are errors. An SOH there is a header row; a keyed unit
outside a record (`␐␁k␟v␘`) is an error. Commits (ETB) do not occur inside
a level. The RS of a list is written, never assumed. A value inside a level
that needs exactness is itself text. An unmatched CAN, or a level open at
the end of input, is an error.

CAN has no effect when printed raw on a terminal, and DLE none.


## References (ENQ)

**ENQ (0x05)** marks a field value as a reference to data defined elsewhere
in the same document. The target may come before or after the reference; a
record may refer to the group it sits in.

A plain name is a group:

    ␅tags

Anything finer is a **pattern**: a level whose body is the target with its
values left out, written in the document's own codes. A reader parses it
as it parses any level and reads the tree as a path:

    ␅␐␝tags␞001␟label␘

group `tags`, the positional record whose **record id**, its first
field, is `001`, that record's field under the header name `label`. Each line of the pattern is
one step, and the steps are the openers a reader meets walking into the
target:

| Step | Written | Names |
|---|---|---|
| file | `␜a` | the file `a` |
| group | `␝tags`, `␝␝intro` | a group; GS repetition is depth, as in the document |
| record | `␞001` | the positional record whose record id is `001` |
| field | `␞001␟label` | that record's field under the header name `label` |
| keyed unit | `␞␁host␟` | the keyed unit `host`; its value is left empty |
| level | `␞001␟children␟␐…␘` | continue into the level in field `children`; the inner pattern follows the same rules |

    ␅␐␝tags␘                       the group tags; legal, not canonical (␅tags)
    ␅␐␜b␝tags␞001␘                 record 001 of tags in file b
    ␅␐␝docs␝␝intro␞3␘              record 3 of docs' subsection intro
    ␅␐␝server␞␁host␟␘              the keyed unit host in server
    ␅␐␝tags␞001␟children␟␐␞2␘␘     record 2 inside the level in field children of record 001

A pattern is one branch: at most one file line, then group lines, then at
most one record. A positional record in a pattern holds one to three
units: the record id, then a field name, then a level that continues the
pattern. A keyed record in a pattern holds one keyed unit with an empty
value; it is spelled `␞␁host␟` because `␝server␁host` would be a header
row. Every name is a name as elsewhere (non-empty, no edge whitespace, no
control bytes) and is written plain. Anything else is an error: an empty
level, a pattern with no group, two groups or two records at one depth, a
file or group after a record, a fourth unit, a third unit that is not a
level, a keyed unit with a value or a second keyed unit, a header row, a
dead element, text, or a reference with nothing after the ENQ. Notes are
allowed as everywhere and are not part of the path. ENQ followed by text
(`␅␂…␃`) is an error: every step is a name, and a name is plain, so text
has no spelling to offer.

A field in a record with no header row, a record whose record id is not
a name, a keyed record as a whole, the heading and notes cannot be
addressed; such things are reached by a group reference and a lookup in
the application.

The format checks a reference's form only. Resolution is the library's. A
reference resolves to the **nearest** target that matches the whole
pattern before it in the document, measured from the target's opener to
the ENQ; if none precedes it, to the first that follows. Nearest makes a
resolved reference stable: nothing written after a reference can change
what it means, so a log may restate a target and references after the
restatement take it. A bare group reference matches a top-level group of
that name in any file; a level's contents are not a namespace and are
reached only by a pattern that enters the level through its field. A
document reader keeps, per name, the offsets of the targets it has seen
and searches them; a stream consumer keeps the most recent. A reference
whose target does not exist is an error when the library is asked to
resolve it. A reference is hashed as the bytes it is written in: the
pointer, not the thing pointed at; resolution never changes a byte.

In a **stream log** a reader has only the blocks committed so far, and
that is the limit: a reference can be resolved only once its target has
been committed. Nobody expects the first record of a million-record log to
be resolvable against the last one. A log writer that wants a block to be
self-contained writes what the block refers to first; a log consumer that
indexes as it goes resolves a reference when its target lands.

    ␝tags
    ␁␞id␟label
    ␞001␟Admin
    ␞002␟Editor

    ␝articles
    ␁␞title␟tags␟primary
    ␞My Post␟␅tags␟␅␐␝tags␞001␘

A blob (see Trailing Blob) is referenced by its name as ordinary data, not
with ENQ.


## Comments (BEL)

**BEL (0x07)** marks the next thing dead. Like every other code it owns the
content after it, up to the next control code: BEL followed by a value,
plain or text, is a **note**, which a reader skips. BEL followed by a structural code marks that
element as **dead**: the reader parses the element exactly as if it were
live, with every scanning property intact, and then discards it. A record,
a group, a header row, a keyed unit, a nested level, a heading key or a
file may be dead. Dead means the element and everything it holds: a dead
group takes its header row, its records and its deeper subsections, a
dead file takes its groups, and each ends where it would end if live. To
comment out a label alone and let what follows fall through to the
element before, put the label in a note: `␇␂␝g2␃`.

    ␇ see the runbook           a note, ends at the next code
    ␇␞port␟5432                 a dead record
    ␇␝server                    a dead group; its records go with it
    ␇␂␝server␃                   the label alone; its records join the group before
    ␇␁␞name␟amount              a dead header row
    ␞Alice␟␇␐␞Admin␘␟100        a dead level; 100 is live
    ␖␁a␟1␇old␁b␟2               a note between heading keys
    ␇␂anything ␞ at all␃         a note holding control codes is text

Layout between the BEL and the code is layout, as everywhere: `␇␊␞port` is
a dead record. A note has content: a BEL directly followed by a code is
always the dead marker, so `␇␇␞x` is an error (BEL is not an element), and
a BEL at the end of input is an error. The codes that may follow a BEL are
FS, GS, RS, SOH, DLE and plain or text content; before any other code (US,
ETX, CAN, ENQ, SUB, ETB, EOT, SYN, EM) a BEL is an error: those are not
elements, and framing cannot be commented out.

**A note is never a unit.** Wherever a note sits, the reader skips it and
the structure around it is what the codes say: `␞Alice␟␇old␟100` has two
US and so three units, `Alice`, an empty unit holding only a note, and
`100`; `␞a␇n␟b` has one US and two units, `a` and `b`; `␞␁a␟1␇n␁b␟2` is
the map `a`=`1`, `b`=`2`. Stripping comments therefore never changes arity.
A keyed record whose every unit is dead is an empty map. Comments are allowed inside nested levels and inside committed log
blocks: the ETB digest covers them, the content hash does not. Stripping
comments is a tool option, not a reader rule; canonicalisation strips
notes and dead elements alike.


## Supersession (SUB)

**SUB (0x1A)** outside text, immediately before US, SOH, RS, GS or FS,
marks the element before that code as **superseded** by the element after
it, at the grain of that code:

    ␞old␚␟new          the unit before is superseded by the unit after
    ␞␁k␟v␚␁k␟w         the keyed unit before, by the keyed unit after
    ␞a␟b␚␞a␟c          the record before, by the record after
    ␝g␞x␚␝g␞y          the group before, at that depth, by the group after
    ␜f␝g␞x␚␜f␝g␞y      the file before, by the file after

The superseded element was wrong; the superseding one stands in its
place. This is SUB's 1963 meaning, "replace the character found to be
erroneous", lifted from the character to the element, and it pairs with
BEL: `␇␞` kills what follows, known before writing; `␚␞` replaces what
precedes, found out after. SUB before any other byte, at the end of input,
or next to BEL is an error, and the slot stays reserved.

**What a reader does.** It hands both elements on, in order, with the fact
that the second supersedes the first; it never takes anything back,
because it streams. What to do with the fact is the consumer's: a document
model drops the superseded node as it builds the tree, so `␞a␟b␚␟␟c` is
the record `a`, `""`, `c`; a diff applier keeps both as search and
replacement; a tool showing an edited copy shows both.

**Empty sides.** An empty unit is nothing between two codes, so no `␂␃`
is ever needed:

    ␞old␚␟new␞end      record 1 [old → new], record 2 [end]
    ␞old␚␟␞end         record 1 [old → ""], a deletion; record 2 [end]
    ␞␚␟new             record 1 ["" → new], an insertion
    ␞a␟b␚␟␟c           [a, b → "", c]: three units in the result

**Arity.** "N separators, N+1 units" counts what was written; the result
of a record omits its superseded units. Supersessions chain: `␞a␚␟b␚␟c` is
`[c]`, with `a` and `b` both handed on.

**Nothing to supersede.** A unit always has a predecessor, since the first
unit of a record exists even when empty. A record, group, file or keyed
unit does not: `␝g␚␞x` with no record before it in the group is an error,
as is `␚␝` with no earlier group at that depth, `␚␜` with no earlier file,
and `␚␁` as the first keyed unit of a record.

**Where it is legal.** Everywhere the grammar admits the code that follows
it, the heading included; a header row's names are not units and admit
none. The meaning is the base grammar's and does not vary by shape; a
shape says which grains it allows (C0DIFF: the unit grain only).

**Canonical form and hashing.** Supersession is content: a document that
says "this, superseded by that" is a different document from one that
says only "that". Canonical form keeps it and hashes it as written, each
side in its one spelling. The deciding case is the diff: a C0DIFF document
is made of supersessions, and if canonical form applied them,
canonicalising `␞␂Hello ␃␟world␚␟universe␟!` would leave
`␞␂Hello ␃␟universe␟!`, the replacement alone; the diff would be gone and
its content hash would be the hash of its output. The rule has one
meaning, so canonical form cannot apply it in one shape and keep it in
another. It therefore differs from BEL, which canonical form strips: a
note is outside the data, a supersession is a statement about it. The
cost falls on data documents: a log corrected in band (`␞Bob␟340.00␗`
then `␚␞Bob␟350.00␗`) and one written right the first time have different
content hashes. A tool that wants the corrected data, or its hash, takes
a reading, as it takes the live records of a document with dead ones. The
ETB digest is unaffected: it covers each block's bytes as written, so the
correction is covered by its own block and the block it corrects stays
verifiable.


## Document Mode (Depth via GS Repetition)

For hierarchical documents (like Markdown headings), GS is repeated to
indicate depth:

    ␝         = depth 1   (like #)
    ␝␝        = depth 2   (like ##)
    ␝␝␝       = depth 3   (like ###)

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

Repetition is read the same in every shape: `␝␝g` is group `g` at depth
two. A depth may be skipped (`␝a␝␝␝c`): `c` is at depth three and no
group stands at depth two; a reader reports what is written and invents
nothing. A header row belongs to the group line it follows, not to its
subsections (see The header row). **Limitation:** an empty-named group cannot be followed directly by
another group, since the bytes would read as depth; in a document with
several groups, name them. The limitation is on canonical bytes: `␝␇n␝b`
is two groups at depth one, with a note between the GS, and stripping the
note would leave `␝␝b`, one group at depth two. A canonicaliser or
encoder that would bring two GS together refuses, as a formatter refuses
a value that collides with its glyphs; it never changes depth.


## Key-Value Configuration

For configuration data (like TOML or INI), a section is a group holding one
keyed record:

    ␝database
    ␞␁host␟localhost␁port␟5432
    ␝server
    ␞␁host␟0.0.0.0␁port␟8080␁allowed_origins␟␐␞localhost␟example.com␘

A group of two-field positional records, `␞host␟localhost`, remains legal and
is a table of pairs; converters treat it as such and do not guess.


## Consistent Roles Across Shapes

| Shape      | RS means          | US means                  |
|------------|-------------------|---------------------------|
| Tabular    | row               | field / column            |
| Document   | paragraph / block | list item / element       |
| Key-Value  | the section's map | key → value (after SOH)   |
| Diff       | anchored pattern  | anchor or substitution    |


## Canonical Form (Content Addressing)

Canonical form is the subset of compact form in which **the same logical
value encodes to exactly one byte sequence**, reproducible by any conforming
encoder in any language. Two conforming encoders given the same data MUST
emit identical bytes, so the bytes may be hashed and equal hashes mean equal
values. The pretty form is presentation, never hashed. The rules:

### One Spelling per Value

A value is **plain** when it can be and **text** when it must be: a value is
plain if and only if it has no byte below 0x20 and no edge whitespace.
Inside text, DLE appears only before the seven codes. Gratuitous text
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

Labels, keys and header names contain no byte below 0x20 and no edge
whitespace.

### Order Is Significant

C0DATA defines **no unordered constructs**. Records appear in order;
positional fields and header columns are positional; the entries of a keyed
record stay in the order written. Conforming codecs MUST preserve order
exactly and MUST NOT reorder.

Canonical order for logically unordered data, a map's entries, a set's
members, a directory's entries, is the **producer's** job, above the format
(compare git tree objects, or RFC 8785 for JSON): the application builds
its C0DATA in its own canonical order and a library hands the bytes back in
that order. Where a producer has no domain order and no schema, the
recommended default is bytewise order: a map's entries by key, records by
first field. The byte-level suite cannot verify this; it is a contract on
producers, checked at the layer that knows the data is unordered. The one
thing the format does check is uniqueness: a duplicate key in a keyed
record is non-canonical, and a reader takes the last value with a warning.

### Framing and Metadata Are Outside the Hash

SYN and the whole heading, EOT, ETB markers and their payloads, BEL comments,
and EM with its blob are never part of any canonical span's bytes.
Canonicalising a unit removes them. `shape` says how to read the bytes, not
what they are; the same stream transmitted without its heading is the same
stream.

### Canonical Spans

A **canonical span** is the stretch of bytes a hash covers; three are
defined, and none is a unit of a record.

- **Record** — the content bytes after its RS, up to the next RS, GS, FS,
  dead record or header row, or framing byte at the record's own depth;
  text, nested levels and notes inside it included, the RS itself
  excluded.
- **Group** — from its GS through its records and deeper sections (name,
  header row and GS-repeated subsections included), up to the next GS at
  the group's own depth or shallower, FS, or framing byte.
- **Document** — the body: from the first byte after the heading to the
  last content byte.

A span is hashed over its **canonicalised** bytes: layout, comments, dead
elements and framing removed, values in their one spelling, order kept. A
span that is already canonical hashes as written.

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
**ETB (0x17)** as an explicit commit marker. A document is read in stream
mode when its heading declares `shape` `stream`, or when the reader is told
to.

### The Commit Rule

ETB commits the **block** of bytes appended since the previous commit (the
previous ETB and its payload) or the start of the stream. A block is
typically one record, but may be several; committing N records with a
single trailing ETB makes the batch atomic.

    ␖␁shape␟stream␁␞op␟id␟at␗
    ␞create␟a1b2c3␟1718208000␗
    ␞name␟draft-2␟1718208042␗
    ␞tag␟alpha␟17182080             ← torn tail: no ETB, skipped

- A block is **complete** if and only if it is terminated by ETB. ETB ends
  the record it follows, as RS would; whatever follows the ETB up to the
  next control code is its payload.
- **Readers** MUST treat a trailing block with no terminating ETB as torn
  and skip it, whatever it holds: a tail that leaves text or a level open,
  ends in a lone DLE, or is malformed, is torn and is not reported as an
  error. A tail holding only layout, notes, EOT or EM is not torn: those
  are not data. A dead element in the tail is data, and the tail is torn.
- A committed block that is not well-formed is **damaged** (see below):
  the reader delivers nothing from it and reports it.
- **Writers** MUST verify the stream ends at a commit (an ETB and its
  payload) before appending, by truncating an uncommitted tail or by
  appending from the last commit. Appending after an unrepaired tail is
  non-conforming: an open text in the tail would fuse the fragment with the
  new block into one committed, corrupt block. A log that ends in EOT is
  closed: a writer removes the EOT to append, or refuses.
- A block and its ETB SHOULD be issued as a single append.

Because framing cuts through text and levels, an unescaped ETB is always a
commit: a torn text cannot hide later commits, and damage is confined to
one block. Outside text a DLE is a level opener, so `␐␗` there is a commit
that cuts an open level (a damaged block), not an escape. The forward scan
is authoritative; a backward scan from the end of a container with no EM,
treating an ETB behind an odd run of DLEs as escaped, finds the last
commit in well-formed input and is a shortcut, not a definition. The
commit rule applies to every appended unit, the heading and a header row
included; a header row may follow the heading's commit. A SYN inside a
stream tears whatever uncommitted bytes precede it, reported as the torn
tail of the document they belong to, and begins a new document with its
own heading, shape and blocks; the ETB that follows commits the new
heading.

### Damaged Blocks

A committed block that is not well-formed is **damaged**: one cut by its
ETB inside open text or an open level, as above, or one holding any
other error (`␞b␟␇␅tags␗`, a header row after records). The block's
bounds are still known, because the ETB that closed it is a commit
whatever came before, so damage never spreads: the reader determines
every block, complete or torn, well-formed or damaged, with its offsets,
and delivers nothing from a damaged block, not even the sound records of
a batch, since the block is the atomic unit. A torn tail is what a crash
leaves and is skipped silently; a damaged block is what a non-conforming
writer or a corrupted medium leaves and is reported.

What follows the report is the consumer's choice, not the format's. A
write-ahead log stops at the first damaged block, since what follows is
suspect; an event log skips it, since its entries are independent. A
library therefore delivers records up to the first damaged block and then
an error naming the block and the offset after its ETB and payload, where
reading can resume; it continues past the block only when the consumer
asks, by an option or by reopening at that offset. A command-line tool
reports the block and exits non-zero. Stream mode is chosen by the
heading or by instruction, so a reader not told to use it that meets a
malformed heading has no heading and reads as a document, where the
error is an error.

    ␞a␗␞b␟␇␅tags␗␞c␗      three blocks; the second is damaged; a is delivered, then the error; c on request

### ETB Payload

ETB may be followed by an **integrity payload**, a plain value terminated by
the next control code. An empty payload means the ETB is framing-only.
Payload semantics (a checkpoint hash of the preceding block, `<alg>:<hex>`;
see Speculations) are not yet specified, but the grammar is fixed so that
framing-only readers remain forward-compatible.

When payload semantics are specified, the hashed **span** is the block
exactly as framing defines it: every byte after the previous commit (ETB and
payload) up to but not including this ETB, the marker and payload excluded,
layout bytes included as written. `committed_end` is the offset just past
the payload; layout after the payload belongs to the next block, and so does
whatever else follows: a block begins as a body part does, so STX or US
directly after a payload (`␗p␂x␃␗`) is an error in that block, which is
damaged.

### Relationship to the Rest of C0DATA

ETB is framing, not data. Outside stream mode, parsers MUST tolerate an ETB
and its payload as a no-op at any record boundary, so a log is readable by
ordinary tooling; an ETB inside open text or a level is malformed there.
Stream mode gives **crash consistency**; it does not give durability (the
application's fsync discipline) or integrity (until checkpoint payloads are
specified).


## Trailing Blob (EM)

**EM (0x19)** is the end of all C0DATA on the medium. Every byte after it,
to the end of the container, is one raw region: no escapes, no framing, no
scanning. A reader stops at EM. There is one EM per container, since a
second would be a byte inside the raw region. EM is framing and cuts
through text and levels like ETB; a document reader that meets it while
text or a level is open rejects the input.

The region is declared in the **first document's heading** under the key
`blob`, a nested table with a header row and one row per blob: `name`,
`offset`, `length`, and an optional `hash` (`<alg>:<hex>`). Offsets and
lengths are decimal integers relative to the first byte after EM. Rows may
overlap, may leave gaps for alignment, and may be zero length. A row
written as a keyed record (`␞␁name␟lamp␁offset␟0␁length␟3072000`) names
its own columns, as any keyed record under a header row does.

    ␖␁blob␟␐␁␞name␟offset␟length␟hash
      ␞lamp␟0␟3072000␟sha256:cd34…
      ␞desk␟3072000␟1900000␟sha256:ef56…␘␄
    ␖␜catalogue␝items␁␞name␟photo␞Lamp␟lamp␞Desk␟desk␄
    ␙…raw…

Blobs belong to the container, not to a document: any document may reference
any blob by name, and a reference is data resolved by the library. For a
container of several documents the recommended form is a heading-only first
document, as above; a single document writes the table into its own heading.
A `blob` key in a later heading is ignored with a loud warning; EM with no
`blob` table draws a loud warning, and the region is unaddressable.
Columns are matched by header name in any order; extra columns are ignored;
a row with a missing or non-integer offset or length, a `blob` value that is
not a level, or a table with no header row draws a loud warning and
declares nothing; a duplicate name means last wins, with a warning.
Alignment is the writer's choice.

Before trusting a blob byte a reader checks that the container holds at
least the largest offset plus length past EM, and that each row's hash, if
present, matches. The blob is outside every canonical span; the container is
write-once, since nothing can be appended after EM. EM implies EOT.

Inline text and the trailing blob are complementary: text for data in
transit, consumed whole; EM for packaging; files beside the data for a
store (see Speculations, sidecar pattern).


## C0DIFF (Atomic Multi-File Edits)

C0DIFF is a **profile** of C0DATA: a document whose heading declares
`shape` `diff`, holding anchored patterns that edit files atomically. It is
specified in `DIFF.md`; this section fixes only what the data format must
know.

    ␖␁shape␟diff
    ␜foo.txt
    ␞␂Hello ␃␟world␚␟universe␟!
    ␞␂  ␃␟count␚␟total␟␂ = 0␃
    ␄

A diff is files of records and parses under the base grammar like any
document. In it FS begins a file, RS a record that is one anchored
pattern, US separates its units, and supersession at the unit grain
(`old␚␟new`) is the substitution: the superseded unit is what the file
holds, the superseding unit what it will hold, and a unit that is neither
is an anchor. Anchors, olds and news are values under the ordinary rules,
plain or text; paths are names. Every slot the diff does not use (keyed
units, levels, references, header rows, GS, supersession at any other
grain, dead records and dead file lines) is an error in a diff, so each
stays free for a later meaning. Comments and framing apply as everywhere.
The matching, constraint and atomicity rules are in `DIFF.md`; the vectors
are `vectors/diff.json`.


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
| Nested     | DLE … CAN, any inner codes      | JSON objects, arrays  |
| Text       | STX/ETX                         | quoted strings, blobs in transit |
| Reference  | ENQ, a level pattern for paths  | foreign keys, links   |
| Diff       | FS, RS, US, SUB                 | unified diff, patches |
| Stream     | RS, US, ETB                     | NDJSON, SSE, WAL      |
| Container  | SYN heading, EM                 | tar, zip, PDF streams |


## Open Questions

None at present. Type tags are held under Speculations.


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
block. The payload is a plain value, not raw digest bytes, to keep "payload
terminated by the next control code".

### Blob Sidecar Pattern

For a store of many or large blobs, keep each in its own file or
content-addressed object and describe it with ordinary rows:

    ␝blobs␁␞name␟location␟length␟hash
    ␞image-001␟sha256:ab12…␟4096␟sha256:ab12…
    ␞audio␟media/audio.opus␟18000␟sha256:cd34…

Fields point at a blob with an ordinary path reference,
`␅␐␝blobs␞image-001␘`. Each blob is independently memory-mappable, cacheable
and deduplicated, and every existing tool handles it. The columns match the
heading's `blob` table, so a sidecar row becomes a trailing-blob row by
replacing `location` with `offset`.

### Type Discrimination (Numbers vs Text)

All values are text. If type information is ever needed, a nested level that
opens with a keyed unit (`␐␁type␟rgb␞255␟0␟0␘`) is the position **reserved**
for it: that form is an error today, so no file carries one, and a future
revision may define it under additive versions once a schema system gives
tags a meaning. A
header-level convention (`␁␞name:s␟amount:n`) is the alternative. Today the
application decides, as JSON numbers are simply unquoted text.


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
