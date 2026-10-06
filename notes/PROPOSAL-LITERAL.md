# Proposal: Text and Nesting (STX … ETX, SI … CAN)

**Status:** Draft — core agreed in discussion; whitespace rule and one
detail open
**Date:** 2026-10-06 (revision 3)
**Supersedes:** `PROPOSAL-TEXT.md`; and revision 2 of this file, which
put literal regions on DLE STX … DLE ETX

## Summary

C0DATA gets two kinds of brackets, each with one meaning, each one byte
at either end, and each with the name it ought to have:

- **STX … ETX is text.** A string, taken literally. Inside it every byte
  is data except six, which take a DLE in front: STX, ETX, DLE itself,
  and the framing codes ETB, EOT, SYN.
- **SI … CAN is a nested level.** Shift in to a new level, cancel it to
  return. Inside, the hierarchy starts over: RS, US, SOH and the rest
  mean what they mean at the top, and whitespace is layout, as
  everywhere.

In Lisp terms: `" … "` and `( … )`.

Outside text a control code is never data, and DLE never stands alone:
it begins one of a few two-byte sequences. Per-byte escaping goes away.
Two codes are newly assigned, SI and CAN; SO is struck from the list for
good.

In pretty form:

    ␞greeting␟␂  hello  ␃
    ␞note␟␂line one
    line two␃
    ␞Alice␟␏
      ␁street␟city
      ␞1 Main␟Springfield
    ␘
    ␞roles␟␏␞Admin␟Editor␘

The first two values are text: spaces and line breaks kept, and the
glyphs read as the quotation marks they are. The third is a nested
table, laid out over indented lines. The fourth is a list: a record
inside a nested level.

## Motivation

Two needs drove this. Values must be able to carry whitespace, line
breaks and control codes exactly, and read back without a copy. And
fields must be able to hold nested data: lists, tables, objects.

The shipped design served both with one pair of brackets, STX and ETX,
on sound reasoning: control codes cannot be values outside brackets, so
a raw code inside them is free to mean structure. But the same pair was
also claimed as quoting in pretty form, which the implementation never
delivered; every control code in a string, tabs and newlines included,
needed an escape, which forces a copy on every multi-line value and
inflates binary by about twelve percent; and nine defects in the
reference implementation trace back to the double meaning (listed under
"What this resolves").

A second pair was needed. The candidates and why each fell:

- **SO and SI** had the right names, but a raw SO switches tmux, screen
  and the Linux console into their line-drawing character set once any
  full-screen program has primed the pane, and a raw dump of a file is
  the first thing people judge a format by.
- **DC2 and DC4** are inert everywhere but their names say nothing.
- **DLE STX … DLE ETX**, BISYNC's transparent text, is historically
  exact and needs no new code, but it is two bytes at each end, and it
  was ASCII's own after-the-fact patch for a case the original set had
  not anticipated. Adopting it meant inheriting the patch rather than
  the design.

The answer was to take one step further than the ancestors did. SO is
unusable, but nothing stops SI from standing alone, and "shift in" is a
fair name for entering a level. CAN closes it. That frees STX and ETX to
mean exactly what they say.

## History

ASCII's message shape was heading, then text: `SOH heading STX text
ETX`. Text was the body, and it could not contain ETX. When binary had
to cross the link, BISYNC added transparent mode, `DLE STX … DLE ETX`,
with DLE DLE for a data DLE. The two bracket meanings C0DATA needed,
recursion and literal data, were the two things the 1963 set lacked;
the first it never had, the second it bolted on later.

**Departure from BISYNC.** In transparent text a raw ETB was data and
the block ended with DLE ETB. C0DATA inverts that: a raw ETB, EOT or
SYN inside text is framing and cuts through, and a data byte with one
of those values takes a DLE. The reason is the torn log: a crash that
leaves text open, followed by an append that commits on top of it, must
not let the open text swallow later commits (verified against the
reference log reader, which today would hide them).

## Proposal

### Text

    [STX] bytes… [ETX]

Inside:

| Bytes | Meaning |
|---|---|
| any byte other than STX, ETX, DLE, ETB, EOT, SYN | that byte, as data |
| DLE followed by one of those six | that byte, as data |
| ETX, unescaped | end of the text |
| STX, unescaped | an error (text does not nest) |
| ETB, EOT, SYN, unescaped | framing: the text was cut |
| DLE followed by anything else | an error |

Text is a whole value. It cannot be part of a plain value
(`abc␂ x ␃def` is malformed). An empty text, `␂␃`, is the empty string
and is not canonical, since the empty string is written as nothing.

### Text heading: the size

A text may carry a heading in front of its opener, one reserved DLE
sequence:

    [DLE][SOH] size [STX] bytes… [ETX]

    ␐␁3072000␂ … ␃

The heading holds one thing, the **size**: the encoded length on the
wire, from the byte after STX to the byte before ETX, escapes included,
in canonical decimal. It is optional, and it is a **hint**: a reader may
jump to that offset and must find ETX there; if it does not, it scans
instead. Nothing depends on the number. The writer counts the six
escaped values in one pass over bytes it already holds.

The heading is metadata, outside the hash: the canonical unit is
extracted with it left out, as with other framing. No hash goes here:
in a log the block's ETB digest covers the value, at rest the content
hash does, and a hash that identifies the value for the application is
data and belongs in a neighbouring field. A hash belongs in a heading
only where nothing else covers the bytes, which is the trailing blob
(`PROPOSAL-EM.md`).

### Nested levels

    [SI] … [CAN]

The hierarchy starts over inside. Nested levels nest. A value inside a
nested level that needs exactness is itself text. Whitespace inside a
nested level follows whatever rule applies at the top (see "Whitespace",
open).

Text directly after SI, before the first structural code, is reserved
(open question 1). An empty level, `␏␘`, holds nothing.

### Lists and nested data

Inside a nested level the format's own shapes apply, and nothing new is
needed:

| Nested content | Written as |
|---|---|
| a list | `␏␞Admin␟Editor␘`, one record |
| an empty list | `␏␘`, no record |
| a list holding one empty string | `␏␞␘`, one record with one empty field |
| a list of lists, or a table | `␏␞1␟2␞3␟4␘`, several records |
| a table with named columns | `␏␁street␟city␞1 Main␟Springfield␘` |
| a map | `␏␞␁street␟1 Main␁city␟Springfield␘` (`PROPOSAL-KEYS.md`) |

**The RS is written, never assumed** (decided 2026-10-05): every other
opening code owns the text that follows it, so the position after SI is
kept for a label; an assumed RS would make the empty list and a list of
one empty string the same bytes; and one list would have two spellings.
The ordinary table reader reads every row of the table above unchanged.

### References (decided 2026-10-06)

A reference is ENQ followed by its own text. A plain name is a group:

    ␅tags

A path is the segments separated by US. Because a reference sits inside
a field, where a US would end the field, the path is fenced as text:

    ␅␂tags␟001␟label␃

The brackets are ENQ's text, which ENQ reads as a path; a US inside text
is a character, and ENQ is what splits on it. A reference is hashed as
the bytes it is written in, the pointer and not the thing pointed at.
Chaining ENQs (`␅tags␅001`) was rejected: the same bytes could mean one
path or two references in one field.

### Outside both

Every byte below 0x20 belongs to the format:

- the assigned codes are structure or framing;
- DLE begins a sequence. DLE SOH opens a text heading. All other DLE
  sequences are reserved and are errors until a spec revision defines
  them, announced by the heading's `version` key;
- tab, line feed and carriage return: see "Whitespace", open;
- any other code is unassigned and rejected.

### Reserved DLE sequences (decided 2026-10-06)

A DLE sequence is exactly two bytes. The defined one is DLE SOH. Any
other DLE sequence is an error, everywhere, including inside text. New
sequences come only with a spec revision, so a reader built for an
older spec refuses at the heading rather than guessing at bytes it
cannot read. (A draft that classed unknown sequences as skippable by
their second byte was dropped: skipping inside a value breaks the
contiguous slice, canonical form would need a rule for it, and the
version key already does the job.)

### Framing cuts through

An unescaped ETB is always a commit, an unescaped EOT always ends a
document, an unescaped SYN always begins one, whether inside text,
inside a nested level, or at the top. A reader that meets one while text
or a level is open knows that block is damaged. The last commit in a log
can be found by scanning backward from the end.

### Whitespace (OPEN)

Agreed: inside text every byte is data. Not yet decided, for plain
values and the space between codes, which of two rules applies:

- **Layout in both forms.** Whitespace touching a control code is
  layout in compact and pretty form alike; tab, LF and CR are layout
  codes outside text, an error in the middle of a plain value. One
  grammar, but a value with edge spaces or a line break must be text
  even in compact form.
- **Compact is pure data.** Every byte between separators is the value,
  edge spaces included, as the original spec said; a raw tab, LF or CR
  in a compact value is an error, needing text. Layout and trimming
  exist only in pretty form, and the pretty converter strips what
  compact does not need. Readers never trim. Compact never bloats.

The second was proposed after the bloat of the first became visible.

### Canonical form

One spelling per value: plain when it can be, text when it must be,
with DLE only before the six codes. Which values "can be plain" depends
on the whitespace rule above; under either, a value holding a control
code is text. A canonical unit contains no layout, no empty text, and no
text around a value that could be plain. The old rule that the escape
set is frozen survives: any byte below 0x20 in a value requires text,
assigned or not, so a future assignment cannot change what is
canonical.

### Names

Labels, header names and keys are plain only: no bytes below 0x20 and
no edge spaces. They are never text.

## Scanning

- **Outside text the hot test is unchanged:** `byte < 0x20`. On a hit
  the reader looks at which code it is. Bounded lookbehind holds as
  before.
- **Inside text** the reader looks for six byte values. Measured in a
  simple loop, that costs nothing on ordinary text and about ten percent
  either way on random binary.
- **A scanner inside a nested level must skip text whole.** A raw SI,
  CAN, RS or US inside text is a character and does not open, close or
  separate anything.
- **From an arbitrary position,** the first bracket a reader meets says
  where it was: ETX first means inside text, STX first means outside.
  Inside text nothing can be classified without that; the design
  principle becomes "outside text, structure is determinable with
  bounded lookbehind; framing is determinable everywhere". Not a new
  weakness: today a reader entering a nested level mid-way already
  misreads its contents.

## What it gives

1. One meaning per mechanism, and no "content decides" rule.
2. Thirty-two escapes become six. Text is read as a slice of the buffer
   unless it contains one of the six; binary inflates by about 2.3
   percent instead of 12.
3. Single-byte delimiters with the right names and the right glyphs.
   No prefix rule to explain and no special glyph needed to read it.
4. No terminal effect anywhere: STX, ETX, SI and CAN are inert when
   printed raw, and SI even repairs a pane a stray SO has garbled.
5. Nested structure can be laid out in pretty form.

## What it costs

- Two newly assigned codes, SI and CAN, in every tokenizer, the assigned
  table, the invalid vectors, pretty glyphs and the editor grammar.
- The shipped nesting changes its bytes, from STX/ETX to SI/CAN, in all
  seven implementations and in data written by `keep` and `transfs`.
  C0DATA is pre-1.0 and this is the moment to pay it.
- CAN was being held for "discard what precedes"; nothing was built on
  it.
- "Cancel" is a stretch for a closing bracket. It is the one of the four
  names that needs a sentence.

## Where humans will see it

Text is needed only for a value with edge spaces, a tab, a newline, or
a control code. By use case:

| Use case | How often | Typical reason |
|---|---|---|
| Config files | a few values per file | a multi-line description, a script, a key |
| Tables | almost never | cells are single-line |
| Documents | one per code block | preformatted text |
| Logs | some records | a stack trace in a message |
| Patches (C0-DIFF) | nearly every unit | code has indentation and line breaks |

Where text appears, a fence was expected anyway (Markdown's backticks,
TOML's triple quotes, YAML's block indicator), and `␂…␃` replaces `␐␊`
at the end of every line.

## What this resolves

Verified defects in the reference implementation, and how each ends:

1. Edge spaces lost in pretty round trip — such values become text.
2. Brackets stored in a "quoted" value — quoting is its own pair.
3. A newline inside brackets producing invalid compact bytes — inside
   text it is data; inside a level it is layout.
4. Diffs losing whitespace anchors — anchors become text.
5. A raw tab passing through unescaped — never data outside text.
6. DLE before a space being trimmed — DLE no longer escapes bytes.
7. Two incompatible list encodings — one form, a record.
8. A list of one empty string unwritable — `␏␞␘`.
9. JSON export turning a quoted string into an empty array — text is
   unambiguously a string.

## What this replaces

- DESIGN.md: "Escaping (DLE)", "Nested Structures (STX/ETX)", the
  pretty-form whitespace rules, and "every value byte below 0x20 is
  escaped" in Canonical Form; the code table entries for STX and ETX.
- `Builder#list_field` / `Record#list` semantics (separated items) and
  `vectors/list.json`; the JSON converter's nested array form (prefixed
  items). Both move to the record form inside SI … CAN.
- The landing page's "no braces, no quotes, no escaping" and the Crystal
  README's "no escaping".
- `PROPOSAL-TEXT.md`, which put text on STX/ETX and removed nesting; and
  revision 2 of this file (DLE STX … DLE ETX).

## Relationship to other proposals

- **Start marker** (`PROPOSAL-START.md`): heading values are values and
  may be text or nested. SYN is one of the six, so a raw SYN is a
  document start everywhere.
- **Comments** (`PROPOSAL-COMMENTS.md`): a note that must mention a
  control code uses text. A BEL before a nested value comments out that
  value through its CAN.
- **Keyed units** (`PROPOSAL-KEYS.md`): maps inside a nested level.
- **Trailing blob** (`PROPOSAL-EM.md`): text carries binary inline, with
  escapes and one pass; a trailing blob after EM carries it raw.
- **C0-DIFF**: anchors and replacement text that need exactness become
  text. The undecided replace-all notation must not reuse either pair.
- **Schema**: the enum example becomes `␞enum␟␏␞admin␟editor␟viewer␘`.

## Open Questions

1. **The reserved position after SI.** Held for a label; whether bare
   text there is an error for now, and what the ramifications are.
2. **The whitespace rule** above.
3. **Torn tails ending in a lone DLE.** Restate the existing repair rule
   for sequences. Confirmation only.
4. **The shipped list API.** Keep `list_field` / `list` with the record
   form, or drop them in favour of ordinary nested tables.
5. **Rollout.** One change rather than the earlier two-stage plan.

## Feedback

Discussion in progress. Nothing here is adopted until it appears in
DESIGN.md.
