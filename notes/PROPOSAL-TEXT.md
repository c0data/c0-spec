# Proposal: Text (STX … ETX) and Whitespace

**Status:** Superseded by `PROPOSAL-LITERAL.md` (2026-10-05). Kept for the
reasoning and the defect list; the design below put text on STX/ETX and
removed nesting, which later discussion rejected.
**Date:** 2026-10-05

## Summary

**STX and ETX mean what their names say: start of text, end of text.**
What lies between them is a string, taken literally. That is their only
meaning. They do not create nested structure.

1. **Outside text, a control code is never data.** It is structure or
   framing, with no exceptions.
2. **Inside text, every byte is data**, separators and whitespace
   included, except six codes that must be preceded by DLE to be literal:
   the delimiters **STX** and **ETX**, **DLE** itself, and the framing
   codes **ETB**, **EOT**, and **SYN**.
3. **DLE has no role outside text.**
4. **Whitespace that touches a control code is layout, not data**, in
   both compact and pretty form. Text is how a value keeps whitespace at
   its edges.
5. *(Proposed, not yet confirmed.)* **Whitespace inside a value is data,
   exactly as written**: spaces, tabs, and newlines, unescaped.

In pretty form:

    ␞greeting␟␂  hello  ␃
    ␞payload␟␂␞Admin␟Editor␃
    ␞note␟line one
    line two

The first value is the string `  hello  `, spaces kept. The second is the
string `␞Admin␟Editor`: fourteen characters, two of which happen to be RS
and US. It is not a list. The third is a two-line value; its newline is
interior and is data.

## Motivation

### The brackets had two meanings

Since the first commit the spec has given STX/ETX two jobs. The code
table calls them "open/close nested sub-structure"; a section "Nested
Structures (STX/ETX)" says "arrays are simply US-separated values inside
STX/ETX"; and the pretty-form rules say content inside them is "preserved
verbatim … to serve as quoting". Code followed the first reading:
`list_field`, the list reader, the list vectors, and the JSON converter's
arrays and objects all treat bracketed content as structure.

The two readings disagree about the same bytes. `␂count␃` is a quoted
word under one and a one-item list under the other.

How the second meaning arose can be reconstructed. If control codes
inside the brackets must be DLE-escaped to be literal, exactly as they
are outside, then the brackets protect only whitespace, and a *raw* code
inside them is left with no meaning. Structure moved into that vacancy.
It was not designed in.

### The two forms disagree about whitespace

|                          | Compact form     | Pretty form            |
|--------------------------|------------------|------------------------|
| Spaces at a value's edge | data, kept       | trimmed                |
| Newline inside a value   | must be escaped  | dropped unless escaped |
| Tab inside a value       | must be escaped  | passed through raw     |

That disagreement produces real defects, all verified against the
reference implementation:

1. A value `"  padded  "` survives compact form but comes back from
   pretty form as `"padded"`. The round trip called lossless is not.
2. `␂  leading spaces  ␃` stores the brackets in the value.
3. A newline inside `␂…␃` in pretty form yields compact bytes with a raw
   line feed, which the tokenizer rejects.
4. A C0-DIFF loses whitespace anchors in pretty form (`"  "` becomes
   empty). Serious for patches to code.
5. A raw tab inside a value passes into compact form unescaped: invalid.
6. DLE before a space does not protect it; the space is trimmed and the
   orphaned DLE corrupts what follows.
7. Two incompatible list encodings exist: the spec and `list_field`
   separate items with US; the JSON converter prefixes each item with US.
   Exporting `list_field` output to JSON drops the first item.
8. With separated items, a list of exactly one empty string cannot be
   written.
9. The JSON export turns a bracketed string into an empty array.

Also, a line break in the middle of a value is dropped entirely in pretty
form, gluing the words on either side together.

## Proposal

### Text

STX opens text and the next unescaped ETX closes it. Text does not nest:
an STX inside text is a character and must be escaped like any other of
the six.

Inside text a DLE makes the next byte literal. It is required before
STX, ETX, DLE, ETB, EOT, and SYN, and used nowhere else.

### Why the framing codes are included

**Framing cuts through text.** An unescaped ETB is always a commit, an
unescaped EOT always ends a document, an unescaped SYN always starts one,
wherever they appear.

The reference log reader already treats an ETB inside brackets as
content, and so a bracket that never closes swallows everything after it:
a writer that crashes inside brackets, followed by an append that skips
repair, hides every later block, and a repair at that point truncates
them away. With framing absolute:

- a torn bracket cannot hide a later commit; damage stops at one block;
- the last commit in a large log can be found by scanning backward from
  the end, without reading the whole file;
- a commit met while text is open marks that block as damaged.

Detection of an ordinary torn tail is unchanged and was tested (torn in a
plain record, torn inside brackets, torn inside brackets containing an
ETB byte).

### Whitespace

Whitespace is space, tab, line feed, carriage return.

- **Touching a control code:** layout, ignored. Pretty form is therefore
  compact form plus glyphs and layout, one grammar. Canonical compact
  form contains no layout.
- **Inside a value** *(proposed)*: data, as written. A reader trims the
  two ends and touches nothing else, so a value is still a contiguous
  slice of the buffer. Not collapsed as HTML does; that is lossy.
- **Inside text:** data, all of it.

### Canonical form

One way to write each value. A value is written as text exactly when it
contains a control code or begins or ends with whitespace. Inside text,
DLE appears only before the six codes. `␂x␃` and `x` are the same value;
the canonical form is `x`.

The rule that the escape set is fixed for all time is preserved in a new
shape: *any* control code in a value requires text, whether or not the
code is assigned, so a future assignment cannot change what is canonical.

### Zero-copy

Text is read as a slice of the buffer unless it contains a DLE. Today a
value holding any control code must be copied to remove its escapes, and
because tabs and newlines count, so must any multi-line value. Binary in
text inflates by about 2% (six byte values in 256) instead of about 12%.

### Reading from an arbitrary position

Text must be traced. But a reader that lands anywhere can find its
footing by looking forward to the next unescaped bracket: ETX first means
it was inside text, STX first means it was outside. That is exact, and
simpler than the same problem in CSV or JSON, where opening and closing
quotes are the same character. A chunked scanner carries one bit, "inside
text", between chunks.

The design principle becomes: *outside text, structure is determinable
with bounded lookbehind; framing is determinable everywhere.* This is not
a new weakness. Today, reading `␞a␟␂x␞y␟z␃␟b␞c` from the inner RS yields
a bogus record `y`, `z`.

## The trade-off behind this

A format can have any two of three properties:

| Mechanism                       | Any byte in a value | Never copy          | Read from any position |
|---------------------------------|---------------------|---------------------|------------------------|
| Escape each byte (DLE)          | yes                 | no                  | yes                    |
| Quote a region (text)           | yes                 | yes                 | no, must trace         |
| Forbid control codes in values  | no                  | yes                 | yes                    |

This proposal takes the second row and, through the framing rule and the
forward-look test, keeps most of what the first offered.

## What this replaces

- DESIGN.md "Nested Structures (STX/ETX)" and the arrays sentence.
- "Every value byte below 0x20 is escaped" as the canonical rule.
- DLE outside text.
- `list_field` and the list reader as format features, and
  `vectors/list.json`.
- The JSON converter's mapping of bracketed content to arrays and objects.
- The landing page's "no braces, no quotes, no escaping" and the Crystal
  README's "no escaping", which overclaim in any case.

## Open Questions

1. **Interior whitespace.** Confirm that it is data as written.
2. **Structure inside a field.** The format no longer has it. An
   application that wants a list or table in a field stores text and
   parses it (`␂␞Admin␟Editor␃` needs no escaping for its separators and
   can be handed to the ordinary reader), or uses an ENQ reference to
   another group. Deep nesting pays: each level must escape the brackets
   of the level inside it. Is that acceptable, and what does the JSON
   converter do with nested input?
3. **The list work.** `list_field`, the list reader, and `list.json`
   shipped in seven implementations last week. Remove them, or keep them
   as a library convenience over text.
4. **Partly bracketed values.** Must text span a whole value, or may a
   value mix plain and bracketed parts (`abc␂ x ␃def`)?
5. **Reference paths.** `␅␂tags␟001␟label␃` reads naturally as ENQ
   followed by text that the reference splits on US. Confirm.
6. **Comments and headings.** Their content follows the same rules. BEL
   inside text is a character, which settles Open Question 3 of
   `PROPOSAL-COMMENTS.md`.
7. **C0-DIFF.** Anchors and replacement text that need edge whitespace
   become text, which repairs defect 4. The replace-all notation is still
   undecided and must not reuse the brackets.
8. **Unassigned codes inside text** are plain characters. Outside text
   the tokenizer still rejects them.

## Feedback

Discussion in progress. Nothing here is adopted until it appears in
DESIGN.md.
