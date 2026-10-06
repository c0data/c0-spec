# Proposal: Document Start and Heading (SYN)

**Status:** Draft — direction agreed in discussion, details open
**Date:** 2026-10-05

## Summary

A C0DATA document begins with **SYN (0x16)**. Text directly after SYN is
the document's **heading**: keyed units, each SOH, key, US, value
(`PROPOSAL-KEYS.md`), holding what a reader must know *before* reading. A bare SYN is a complete
header. Readers still parse input that lacks SYN when they can, but warn
loudly.

This assigns a thirteenth control code. Nothing else changes: strip the
SYN and its heading and what remains is exactly today's document.

Three separate documents, in pretty form (SYN is `␖`):

    ␖␜mydb␝users␁name␟amount␞Alice␟100

    ␖␁shape␟stream␞alice␟100␗␞bob␟200␗

    ␖␁shape␟diff␜foo.txt␝Hello ␟world␚universe

The first has no heading. The second declares itself a stream log, the
third a C0-DIFF. Each has exactly one SYN.

## Motivation

The start of a document is open today. DESIGN.md defines a document as
running "from FS (or start of content)", and the reference reader accepts
a buffer beginning with FS, GS, RS, SOH, US, or plain text, and calls all
of them canonical. EOT ends a document; nothing begins one.

What a start marker and heading are for:

1. **Identification.** It says "C0DATA follows", which is what file-type
   and MIME detection need.
2. **Version.** A place for a version, should one ever be needed.
3. **Reading instructions.** A schema reference or a manifest changes how
   the data must be read, so it has to arrive before the data, the same
   rule references already follow (defined before use).
4. **Telling the shapes apart.** A C0-DIFF and a C0DATA database both
   begin with FS followed by text. Nothing at the front says which one a
   reader is holding; it finds out only by meeting a SUB. The same holds
   for a stream log versus a plain record file.
5. **Safe concatenation.** Joining two bare record files yields one longer
   table with no trace of the seam. With a start marker the result is a
   sequence of two documents.
6. **Detecting a lost head.** EOT and ETB reveal a truncated tail; nothing
   reveals a truncated front. A file that lost its first bytes and resumes
   at an RS parses cleanly as bare records.
7. **Clear failure on the wrong input.** The reference reader accepts
   plain text as a record. A marker lets every tool say "this is not
   C0DATA" at the first byte.

Reasons 1, 5, 6 and 7 need only the marker byte. Reasons 2, 3 and 4 need
content behind it. Hence both halves: a required opening and a heading.

## Design Principles

1. **One byte that says one thing.** A bare SYN asserts only "C0DATA
   starts here". Putting it in front of any existing file is always
   truthful.
2. **A prefix.** The marker precedes everything; the body is unchanged.
3. **No second syntax.** The heading is ordinary C0DATA (fields, escaping,
   nesting), not a separate directive language.
4. **Reader instructions only.** The heading holds what the format's own
   reader and tools act on. What the application acts on is data and
   belongs in the data.
5. **Absent means unspecified, or the one true default.** The format never
   asserts what it cannot know.

## Proposal

### The marker

A document begins with a single SYN. A raw SYN can occur nowhere else:
every value byte below 0x20 is DLE-escaped and names may not contain
control bytes at all. So an unescaped SYN is always a document start, and
a reader can find document starts from any offset (with the usual
one-byte DLE lookbehind).

One SYN, never two. The historical doubling solved bit-level
synchronisation, which byte-aligned media do not need; doubling already
means depth elsewhere (GS GS); and one form keeps the encoding unique.

The marker must be a prefix, ahead of FS, because FS is not always the
top level: in a C0-DIFF, FS repeats once per file, so anything placed
after the first FS label would belong to that file, not to the document.

### The heading

The heading is the text after SYN, up to the first FS, GS, RS, EOT, ETB,
or BEL. It is a record with SYN in place of RS, written entirely in
keyed units: SOH, a key, US, a value (`PROPOSAL-KEYS.md`). Values may be
plain, literal regions, or nested levels.

    [SYN][SOH]shape[US]stream[RS]alice[US]100[ETB]

    [SYN][SOH]version[US]2[SOH]shape[US]diff[FS]foo.txt[GS]…

A SYN followed immediately by a structural code is the empty heading.
Keys are names. In canonical form they are unique and sorted bytewise;
readers accept any order.

The SOH after SYN is a key mark, not a hoisted header: a hoisted header
follows a group label or opens a log, and a heading is neither. After
the heading, a standalone SOH keeps its meaning for a log:

    [SYN][SOH]shape[US]stream[SOH]name[US]amount[RS]alice[US]100[ETB]

An earlier draft spelled the pairs as alternating fields with no mark,
because an RS in the heading would be mistaken for the body's first
record. Keyed units remove the need.

### Keys

The key set belongs to the spec. Proposed for the first version:

- **`shape`** — which rules read the body. Values `diff` (C0-DIFF) and
  `stream` (ETB-committed log). **Absent means unspecified**: the
  application decides from context, as it does today. A tool accepts an
  unspecified shape and rejects only a declaration that contradicts what
  it is for. The other shapes in DESIGN.md's table (tabular, document,
  key-value, nested) parse identically and differ only in what the
  application makes of them, so they need no declaration.
- **`version`** — **absent means 1**, permanently. Every document without
  a version is version 1 by definition, so a stable format never pays for
  the field. Only an incompatible future revision must announce itself.

- **`blob`** — present only when a trailing blob follows EM
  (`PROPOSAL-EM.md`). Its value is a nested table, keys hoisted, one row
  per blob: `name`, `offset`, `length`, and an optional `hash`.

Reserved for later design: a schema reference and a manifest.

A reader that meets a key it does not know **warns loudly**: an
instruction it cannot follow means it may be misreading. This keeps
forward compatibility and keeps the heading from becoming a home for
titles, authors, and other application metadata. Those are data.

### What the heading is not

It is not a general metadata mechanism. Only two kinds of information are
forced outside the data: instructions needed before reading, and
attestations about the bytes that are known only after writing. The
heading is the first kind; the ETB payload is the second. Declare before,
attest after. The same pattern already exists one level down (SOH before a
group's records, ETB after a block). Annotations attachable anywhere were
considered and rejected: XML's attribute-versus-element problem, a skip
path in every tool, and a canonical-form ruling for each.

### Reader policy

Parse headerless input if it is otherwise parsable, and warn loudly. This
is stricter than YAML, where a document without `---` is a fully valid
"bare document" and loaders say nothing; the reasons above justify the
difference. Exact behaviour is an open question below.

### Detection, and the TLS distinction

SYN is 0x16, which TLS also uses as the first byte of a handshake record.
A TLS record continues with 0x03 (its protocol version; DTLS continues
with 0xFE). In C0DATA the byte after SYN can never be 0x03: that value is
ETX, and a closing bracket cannot directly follow SYN. **File-type and
MIME detectors must therefore match two bytes, not one.**

### Sequences

In a sequence of documents each begins with its own SYN, normally after
the previous document's EOT. `EOT` followed by `ENQ` remains reserved (see
`PROPOSAL-APPENDIX.md`).

## What it costs

- A thirteenth assigned code: every tokenizer, the assigned table, the
  invalid vectors, pretty glyphs, and the editor grammar.
- Existing files have no SYN and draw the warning until regenerated.
- Readers written before this change reject SYN as an unassigned code.
  That is a loud failure, not a misreading.

No valid existing value changes meaning: the escape set is frozen at "all
bytes below 0x20", so raw SYN never appeared in conforming data. C0DATA is
pre-1.0 and unadopted; this is the moment to make such a change.

## History

ASCII defines SYN, "synchronous idle", as the character a synchronous
link sends to achieve and keep character synchronisation. In IBM's BISYNC
every block began with it:

    SYN SYN SOH heading STX text ETX check

SYN says "lock on, a block starts here". C0DATA already uses seven of
ASCII's ten transmission-control characters (SOH, STX, ETX, EOT, ENQ, DLE,
ETB); SYN is the eighth. The remaining two, ACK and NAK, are replies in a
dialogue and have no role in a document at rest.

## Alternatives considered

- **Require FS at the start.** Without enforcement it is today's
  situation under a new name; and FS cannot mean "document start" because
  it repeats within a C0-DIFF.
- **A doubled SOH** (`[SOH][SOH]heading`). No new code, and repetition
  already means level for GS. But it is degenerate rather than undefined
  today (an empty header name followed by a second header), the same kind
  of flaw as the schema proposal's `[GS][SOH]` marker.
- **SYN then SOH heading.** Ambiguous with field names for bare records,
  as above.
- **ENQ first.** In BISYNC a station sent ENQ to bid for the line, which
  suggests ENQ as an opener. But the bid was part of the dialogue, not of
  the message; a recorded message began with SYN. And ENQ asks ("who are
  you?") where a header declares.
- **SO … SI as a meta-level shift.** A pair can open anywhere, so it marks
  no start; the format is start-delimited and needs no closing bracket
  here; and a bracket pair invites general meta attributes.
- **A closed positional heading** (`[SYN]diff`). More compact and
  impossible to misuse, but optional fields need empty placeholders and
  new fields must be appended in a fixed order forever.

## Relationship to other proposals

- **Schema** (`PROPOSAL-SCHEMA.md`, Open Question 7): the heading is the
  free, front-of-document position a schema reference was waiting for.
- **Manifest** (`PROPOSAL-APPENDIX.md`, "A forward manifest"): a manifest
  is a heading entry that also states an extent.
- **Comments** (`PROPOSAL-COMMENTS.md`): BEL ends the heading like any
  other record-level code.

## Decided (2026-10-06)

- **SYN and the whole heading are outside the hash.** The canonical
  document unit is unchanged: the body, from its first byte to its last.
  SYN is framing like EOT, and the heading's keys are metadata, with no
  exceptions: `shape` says how to read the bytes, not what they are; a
  schema says how to interpret them. The same stream transmitted without
  its schema is still the same stream.
- **`version` is outside too,** which rests on a principle to be adopted
  at 1.0: **versions are additive.** A later version may add forms but
  may never change the meaning of bytes that were valid under an earlier
  one, so identical bytes mean identical data under any version and one
  id suffices. Before 1.0 that promise cannot be made, and hashes may
  change between revisions.

- **Where the markers are required** (2026-10-06):

  | Marker | Required | Exception |
  |---|---|---|
  | SYN | at the start of every file and message, logs included | none |
  | EOT | at the end of every document in a file or message | logs, which have no end |

  A log starts with SYN and its heading, committed with the first ETB
  like everything else; ETB answers completeness block by block, so no
  end marker exists for a log. Records and groups hashed on their own are
  slices, not files or messages, and carry neither marker. A missing
  marker draws the loud warning in both cases, so a file that stops
  without EOT is suspect rather than silently taken as complete. EOT
  before EM is implied, since EM is an end of input; end of input never
  implies EM. (Noted, not designed: a long-lived log may emit a fresh SYN
  and heading periodically as a resynchronisation point, as BISYNC did.)

## Decided (2026-10-06, second pass)

- **Two levels of warning.** A *warning* means the input is legal but not
  what a careful writer produces: layout where canonical form has none,
  an empty literal region, heading keys out of canonical order. A *loud
  warning* means the input may not be what it claims to be: no SYN at
  the start of a file, no EOT at its end, a heading key or a `shape` or
  `version` value the reader does not know. A library never fails on
  either; it parses and exposes the warning. A command-line tool prints
  it. A strict mode, off by default, turns loud warnings into errors and
  leaves ordinary warnings alone.
- **Nothing in the heading causes a refusal by itself.** An unknown
  `shape` or `version` value is a loud warning, not a refusal: under
  additive versions an older reader reads what it understands, and what
  it cannot becomes an error at the byte where it occurs.
- **First keys:** `shape` and `version` as proposed. The other shapes
  (tabular, document, key-value) may be given as hints; converters may
  use them, nothing else may act on them.
- **Diffs** should carry `shape␟diff`, not must. A diff tool accepts an
  unspecified shape and refuses a contradicting one.

## Feedback

Discussion in progress. Nothing here is adopted until it appears in
DESIGN.md.
