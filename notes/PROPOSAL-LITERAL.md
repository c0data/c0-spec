# Proposal: Literal Regions (DLE Transparent Text)

**Status:** Draft — direction agreed in discussion; details open
**Date:** 2026-10-05
**Supersedes:** `PROPOSAL-TEXT.md`

## Summary

C0DATA gets two kinds of brackets, each with one meaning:

- **STX … ETX is structure.** A nested level. Inside it the hierarchy
  starts over: RS, US, SOH and the rest mean what they mean at the top,
  and whitespace is layout, as everywhere.
- **DLE STX … DLE ETX is a literal region.** A string, taken literally.
  Inside it every byte is data except four, which take a DLE in front:
  DLE itself, and the framing codes ETB, EOT and SYN. DLE ETX closes the
  region. DLE DLE is a DLE byte.

In Lisp terms: `( … )` against `" … "`. One is read, the other is quoted.

Outside a literal region a control code is never data, and DLE never
stands alone: DLE STX opens a literal, DLE SOH opens an optional heading
for one (its size), and every other DLE sequence is reserved.
Per-byte escaping goes away. No new codes are assigned.

In pretty form:

    ␞greeting␟␐␂  hello  ␐␃
    ␞note␟␐␂line one
    line two␐␃
    ␞Alice␟␂
      ␁street␟city
      ␞1 Main␟Springfield
    ␃
    ␞roles␟␂␞Admin␟Editor␃

The first two values are literal: spaces and line breaks kept. The third
is a nested table, laid out over indented lines because inside structure
that whitespace is layout. The fourth is a list: a record inside a nested
level.

## Motivation

Two needs drove this. Values must be able to carry whitespace, line
breaks and control codes exactly, and read back without a copy. And
fields must be able to hold nested data: lists, tables, objects.

The shipped design served both with one pair of brackets. That rested on
sound reasoning: control codes cannot be values outside brackets, so a
raw code inside the brackets is free to mean structure, and an escaped
one is a character. But the same pair was also claimed as quoting in
pretty form, which the implementation never delivered, and every control
code in a string, tabs and newlines included, needed an escape, which
forces a copy on every multi-line value and inflates binary by about
twelve percent. Nine defects in the reference implementation trace back
to this (listed under "What this resolves").

A second pair fixes it, and candidates were weighed: SO and SI (their
names fit, but a raw SO flips tmux, screen and the Linux console into
line-drawing characters once a full-screen program has primed the pane;
raw dumps are the first thing people judge a format by) and DC2 and DC4
(inert, but the names say nothing). Then ASCII's own answer turned up.

## History

ASCII defines DLE, data link escape, as a character that "changes the
meaning of a limited number of contiguously following characters", used
exclusively to add control functions to a data link. It was a prefix for
building new controls out of existing characters. In IBM's BISYNC it had
two uses: link controls spelled DLE plus an ordinary character (the
alternating acknowledgements were DLE `0` and DLE `1`), and **transparent
text**:

- DLE STX opened a transparent block.
- Inside it every byte was data, control characters included.
- A data byte equal to DLE was sent as DLE DLE.
- DLE ETB or DLE ETX ended the block. A plain ETX inside was data.

That is the literal region, spelled with two codes C0DATA already has.

**One deliberate departure.** In BISYNC a raw ETB inside transparent
text was data and the block ended with DLE ETB. C0DATA inverts that: a
raw ETB, EOT or SYN inside a literal region is framing and cuts through,
and a data byte with one of those values takes the DLE. The reason is
the torn log: a crash that leaves a region open, followed by an append
that commits on top of it, must not let the open region swallow the
later commits (verified against the reference log reader, which today
would hide them). Framing cuts through everything.

## Proposal

### Structure brackets

STX opens a nested level and the matching ETX closes it. Inside, the
separator hierarchy starts over. Whitespace touching a control code is
layout, so nested structure may be laid out across lines. A value inside
a nested level that needs exactness is itself a literal region.

Text directly after STX, before the first structural code, is reserved
(every other opening code is followed by its own label; this position is
kept for the same purpose). An empty level, `␂␃`, holds nothing.

### Literal regions

    [DLE][STX] bytes… [DLE][ETX]

Inside the region:

| Bytes | Meaning |
|---|---|
| any byte other than DLE, ETB, EOT, SYN | that byte, as data |
| DLE DLE | a DLE byte |
| DLE ETB, DLE EOT, DLE SYN | that byte, as data |
| DLE ETX | end of the region |
| raw ETB, EOT, SYN | framing: the region was cut (torn) |
| DLE followed by anything else | an error |

Raw STX and ETX inside a region are ordinary data. Regions do not nest;
there is no need, since nothing inside is interpreted.

A literal region is a whole value. It cannot be part of a plain value
(`abc␐␂ x ␐␃def` is malformed).

### Literal heading: the size

ASCII's message shape was heading, then text: SOH, STX, ETX. A literal
region may carry the same shape, with one reserved DLE sequence:

    [DLE][SOH] size [DLE][STX] bytes… [DLE][ETX]

    ␐␁3072000␐␂ … ␐␃

DLE SOH opens the heading, which holds one thing, the **size**: the
encoded length on the wire, from the byte after DLE STX to the byte
before DLE ETX, escapes included, in canonical decimal. It is optional.

The size is a **hint**: a reader may jump to that offset and must find
DLE ETX there. If it does not, the hint is wrong and the reader scans
instead. Nothing depends on the number, so the scan rule is untouched.
The writer counts the four escaped values in one pass over bytes it
already holds; a streaming writer that does not have the whole value
omits the heading.

**The heading is metadata, outside the hash** (decided 2026-10-06). Like
an ETB payload or a comment, it says something about the value rather
than being part of it, so the canonical unit is extracted with the
heading left out: DLE SOH up to DLE STX is skipped, with the other
framing. A producer may add or omit it and the value hashes the same.

**No hash here** (decided 2026-10-06). In a log the block's ETB digest
already covers the value; at rest the document's content hash does. A
hash that identifies the value for the application is data, and in a
neighbouring field it makes the record commit to the value's content.
The rule that falls out: a hash belongs in a heading only where nothing
else covers the bytes, which is the trailing blob and not this.

The heading pays only for large values: it lets a reader reach a small
field that sits after a large one without scanning the large one (a
3 MB image costs about 4 ms to scan), allocate the decoded buffer once,
and detect truncation before reading.

### Outside both

Every byte below 0x20 belongs to the format:

- the assigned codes are structure or framing;
- tab, line feed and carriage return are **layout codes**: legal next to
  a control code, never data, and an error in the middle of a plain
  value (such a value must be literal);
- DLE begins a sequence. DLE STX opens a literal region; DLE SOH opens a
  literal heading. All other DLE sequences are reserved for supplementary
  controls, which is what ASCII designed DLE for, and are errors until
  a spec revision defines them;
- any other code is unassigned and rejected.

A space is data inside a value and layout at its edges. So a plain value
holds only bytes from 0x20 up and never begins or ends with a space.

### Reserved DLE sequences (decided 2026-10-06)

A DLE sequence is exactly two bytes. The defined ones are DLE STX and
DLE SOH. Any other DLE sequence is an error, everywhere, including
inside a literal region. New sequences come only with a spec revision,
announced by the heading's `version` key, so a reader built for an
older spec refuses at the heading with a clear message rather than
guessing at bytes it cannot read.

An earlier draft classed unknown sequences as skippable or not by their
second byte. It was dropped: skipping inside a value breaks the
contiguous slice, canonical form would need a rule for it, every
implementation would carry logic nothing exercises, and the version key
already does the job.

### Lists and nested data

Inside a nested level the format's own shapes apply, and nothing new is
needed:

| Nested content | Written as |
|---|---|
| a list | `␂␞Admin␟Editor␃`, one record |
| an empty list | `␂␃`, no record |
| a list holding one empty string | `␂␞␃`, one record with one empty field |
| a list of lists, or a table | `␂␞1␟2␞3␟4␃`, several records |
| a table with named columns | `␂␁street␟city␞1 Main␟Springfield␃` |

A nested map is a record of keyed units (`PROPOSAL-KEYS.md`):
`␂␞␁street␟1 Main␁city␟Springfield␃`.

**The RS is written, never assumed** (decided 2026-10-05). Three reasons:
every other opening code owns the text that follows it, so the bare
position after STX is kept for a label; an assumed RS would make the
empty list and a list of one empty string the same bytes; and one list
would have two spellings. The cost is one byte per list.

The ordinary table reader reads every row of the table above unchanged,
which is the test that matters.

### References (decided 2026-10-06, revised the same day)

A reference is ENQ followed by its own text. A plain name is a group:

    ␅tags

A path is the segments separated by US. Because a reference sits inside
a field, where a US would end the field, the text is fenced in STX … ETX:

    ␅␂tags␟001␟label␃

That is the form the spec has always had. A bracket directly after ENQ
is ENQ's text; a bracket at the start of a field is a nested level. The
two positions never coincide, so no rule is bent (see "The code-and-text
rule" in `PROPOSAL-KEYS.md`). A draft that made the path a nested record
with an RS was dropped for adding a byte to every reference for no gain.

A reference is hashed as the bytes it is written in, the pointer and not
the thing pointed at. Chaining ENQs (`␅tags␅001`) was rejected: the same
bytes could mean one path or two references in one field.

### Framing cuts through

An unescaped ETB is always a commit, an unescaped EOT always ends a
document, an unescaped SYN always begins one, whether inside a literal
region, inside a nested level, or at the top. A reader that meets one
while a region or level is open knows that block is damaged. The last
commit in a log can be found by scanning backward from the end.

### Canonical form

One spelling per value:

- plain, when the value has no byte below 0x20 and no edge space;
- a literal region otherwise, with DLE only before the four codes.

A canonical unit contains no layout, no empty literal region, and no
literal region around a value that could be plain. The old rule that the
escape set is frozen survives in a new form: any byte below 0x20 in a
value requires a literal region, assigned or not, so a future assignment
cannot change what is canonical.

### Names

Labels and header names are plain only: no bytes below 0x20 and no edge
spaces. They are never literal regions.

## Scanning

- **Outside literal regions the hot test is unchanged:** `byte < 0x20`.
  On a hit the reader looks at which code it is; for DLE it looks at the
  next byte. Bounded lookbehind holds exactly as before.
- **Inside a literal region** the reader looks for four byte values
  (DLE, ETB, EOT, SYN). Measured in a simple loop, that costs nothing for
  ordinary text and about ten percent either way on random binary.
- **A scanner inside structure must skip literal regions whole.** A raw
  ETX inside a region does not close a bracket. This is the one rule an
  implementation could get wrong, and the conformance vectors must cover
  it.
- **From an arbitrary position,** the first DLE sequence a reader meets
  says where it was: DLE ETX means inside a region, DLE STX means
  outside. Inside a region nothing can be classified without that; the
  design principle becomes "outside literal regions, structure is
  determinable with bounded lookbehind; framing is determinable
  everywhere". This is not a new weakness: today a reader entering a
  nested level mid-way already misreads its contents.

## What it gives

1. One meaning per mechanism, and no "content decides" rule.
2. Thirty-two escapes become four. A literal region is read as a slice
   of the buffer unless it contains one of the four; binary inflates by
   about 1.5 percent instead of 12.
3. No new control codes; the pool is untouched.
4. No terminal effect at all. DLE, STX and ETX are inert when printed
   raw, so a dump stays as readable as today.
5. Nested structure can be laid out in pretty form.
6. An extension space, the reserved DLE sequences, that costs no codes.

## What it costs

- Two bytes per delimiter instead of one.
- Every scanner treats DLE as the start of a sequence, and skips regions
  whole inside structure.
- Pretty form shows two glyphs at each end, `␐␂ … ␐␃`. An editor may
  render the pair as a single quotation glyph.
- One more sentence to explain than a dedicated pair would need.

## Where humans will see it

A literal region is needed only for a value with edge spaces, a tab, a
newline, or a control code. By use case:

| Use case | How often | Typical reason |
|---|---|---|
| Config files | a few values per file | a multi-line description, a script, a key |
| Tables | almost never | cells are single-line |
| Documents | one per code block | preformatted text |
| Logs | some records | a stack trace in a message |
| Patches (C0-DIFF) | nearly every unit | code has indentation and line breaks |

Where a region appears, a fence was expected anyway (Markdown's
backticks, TOML's triple quotes, YAML's block indicator), and it replaces
`␐␊` at the end of every line.

## What this resolves

Verified defects in the reference implementation, and how each ends:

1. Edge spaces lost in pretty round trip — such values become literal.
2. Brackets stored in a "quoted" value — quoting is now its own thing.
3. A newline inside brackets producing invalid compact bytes — inside a
   literal it is data; inside structure it is layout.
4. Diffs losing whitespace anchors — anchors become literal.
5. A raw tab passing through unescaped — a layout code outside, data
   inside a literal.
6. DLE before a space being trimmed — DLE no longer escapes bytes.
7. Two incompatible list encodings — one form, a record.
8. A list of one empty string unwritable — `␂␞␃`.
9. JSON export turning a quoted string into an empty array — a literal
   region is unambiguously a string.

## What this replaces

- DESIGN.md: "Escaping (DLE)", "Nested Structures (STX/ETX)", the
  pretty-form whitespace rules, and "every value byte below 0x20 is
  escaped" in Canonical Form.
- `Builder#list_field` / `Record#list` semantics (separated items) and
  `vectors/list.json`; the JSON converter's nested array form (prefixed
  items). Both move to the record form.
- The landing page's "no escaping" and the Crystal README's "no
  escaping" (there is escaping; it is now four bytes inside a literal).
- `PROPOSAL-TEXT.md`, which put text on STX/ETX and removed nesting.

## Relationship to other proposals

- **Start marker** (`PROPOSAL-START.md`): heading values are values and
  may be literal or nested. SYN is one of the four, so a raw SYN is a
  document start everywhere.
- **Comments** (`PROPOSAL-COMMENTS.md`): a note that must mention a
  control code uses a literal region. BEL inside a literal is a byte.
- **C0-DIFF**: anchors and replacement text that need exactness become
  literal regions. The undecided replace-all notation must not reuse
  either bracket; a reserved DLE sequence is one possible home.
- **Trailing blob** (`PROPOSAL-EM.md`): literal regions carry binary
  inline, with escapes and one pass; a trailing blob after EM carries it
  raw and zero-copy. They are complementary: transit versus packaging.
- **Keyed units** (`PROPOSAL-KEYS.md`): maps inside a nested level, and
  the rule that a bracket after ENQ is ENQ's text.
- **Schema**: the enum example `␞enum␟␂␟admin␟editor␟viewer␃` becomes
  `␞enum␟␂␞admin␟editor␟viewer␃`.

## Open Questions

1. **The reserved position after STX.** Reserved for a label; confirm
   that bare text there is an error for now.
2. **Pretty rendering.** Whether `c0fmt` and the editor show the pair as
   two glyphs or as one quotation glyph.
3. **Torn tails ending in a lone DLE.** The stream repair rule already
   covers a tail torn between a DLE and its escaped byte; restate it for
   sequences.
4. **The shipped list API.** Keep `list_field` / `list` with the record
   form, or drop them in favour of ordinary nested tables.
5. **Rollout.** Whether this replaces the earlier two-stage plan with a
   single change; it needs no new codes, so the canonical-form concern
   that motivated two stages does not arise.

## Feedback

Discussion in progress. Nothing here is adopted until it appears in
DESIGN.md.
