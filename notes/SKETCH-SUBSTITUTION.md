# Sketch: Substitution Blocks (C0-DIFF inside the base grammar)

**Status:** Sketch — direction agreed in discussion, nothing decided, nothing built
**Date:** 2026-11-06
**Replaces, if adopted:** the `diff-body` grammar in `GRAMMAR.md` and the
Structure section of `DIFF.md`. The semantics of `DIFF.md` (anchors,
cursor, scope, validate-then-write, atomicity) are kept.

## The problem

C0DATA is a framework: the base rules say how the pieces fit, and a
*shape* is a structure built inside those rules. A reader that knows no
shape still gets files, groups, records and units right; the shape says
what they mean. Tabular, key-value, document and stream all pass that
test.

C0-DIFF does not. It is a second grammar, `diff-body`, selected by the
heading's `shape`. In data, GS is followed by a name; in a diff, by a
pattern of units. RS is followed by one `old␚new` substitution, not a
record of units. So a generic reader cannot read a diff, every validator
and builder forks on the shape, and SUB lives inside values.

The test this sketch holds to: **every shape parses under the base
grammar. A shape gives meaning and adds constraints; it never changes
what follows a code.**

Nothing is wrong with what C0-DIFF *does*. Only the spelling is off.

## The sketch

### SUB as a prefix on GS

The format already changes an opener's meaning with a prefix: `DLE GS`
opens a level, `BEL GS` kills a group, `SOH RS` is a header row. In the
same way:

    SUB GS [name]        a substitution block

A substitution block is an ordinary group to the grammar: a name (may be
empty), then records of units. Only the prefix is new. SUB does not occur
inside values and has no other role.

A block may stand under a file line (`FS path`) or without one, when the
target is given by context: one document, standard input, the text a
markup is attached to.

    ␖␁shape␟diff
    ␜greeting.txt
    ␚␝
    ␞␂Hello ␃␟world␟universe␟!
    ␄

### Two kinds of record

Inside a block a record is one of:

- **Boundary** — one unit, no US. An anchor on its own. It must match
  exactly once after the cursor; the cursor moves to the end of its
  match. The stretch between one boundary's match and the next is a
  **scope**.
- **Substitution** — two to four units, fixed columns:

      before ␟ old ␟ new ␟ after

  Any column may be empty; trailing empties are omitted. At least one of
  `before` and `after` must be non-empty: a substitution is always
  anchored. `before + old + after` must match exactly once **within the
  current scope**, and `old` is replaced by `new`. Empty `old` is an
  insertion; empty `new` a deletion.

    ␚␝
    ␞def tally(items)                boundary; scope opens
    ␞␂  ␃␟count␟total␟␂ = 0␃          substitution, anchored both sides
    ␞␂  ␃␟␂# TODO␃␟                   deletion of "# TODO", anchored by its indent
    ␞end                             boundary; scope closes

Two substitutions that today share one pattern line become two records;
the cursor rule makes them sequential:

    ␞␂x = ␃␟10␟20␟␂ + ␃
    ␞␟5␟15␟                          (needs an anchor — see Open)

Uniqueness is measured inside the scope, not across the file. That is
what makes short anchors practical, and it is the same scope `DIFF.md`
already defines for RS lines.

A block could carry a header row, `␁␞before␟old␟new␟after`, like any
table. Boundaries are then one-column rows; whether a header row should
be allowed or required is open.

### What stays from DIFF.md

Anchors are values under the ordinary rules (plain, or text when they
carry a line break, tab, edge whitespace or a control code). The cursor,
exact-once matching, insertion and deletion, validate everything before
writing anything, atomic writes, the error list. All unchanged.

### What goes

- `diff-body`, `section`, `replace`, `dpre`, `pattern`, `dunit`,
  `dvalue` leave `GRAMMAR.md`. The base grammar gains `SUB` as a
  permitted prefix before GS.
- SUB inside a unit.
- The pattern on the GS line.
- `shape␟diff` stops selecting a grammar. It stays as what every shape's
  name is: a statement of what the document is for.

## Open

1. **Placement of SUB.** `SUB GS` is the sketch. The user is not yet sure
   of it. Alternatives raised: `SUB FS` ("every section in this file is a
   block", saves a byte per block, nothing else); both.
2. **Replace-all.** Left out of the original design on purpose: a
   replace-all with no constraints is how a diff makes mistakes. The
   current `DIFF.md` bounds it to a section's scope and forbids an empty
   `old`, but under fixed columns an unanchored `␞␟count␟total` is
   illegal, so replace-all cannot be spelled by omission. If it exists it
   needs a mark of its own and an explicit range rule. **Settle the
   constraints before the spelling.**
3. **Anchoring the second of two substitutions on one line.** With the
   cursor at the end of the first match, `␞␟5␟15` has no anchor and is
   illegal by the rule above. Either the rule relaxes to "anchored *or*
   immediately after a substitution", or the writer anchors it
   (`␞␂ + ␃␟5␟15`), re-using text the first substitution consumed. Needs
   a decision.
4. **Header row** in a block: allowed, required, or neither.
5. **Name.** Code patch and editorial markup are the same structure.
   "diff" names one use. "substitution" or "markup" may be the better
   shape name.

## Use cases

- **Code patch** — what `DIFF.md` was written for.
- **Editor markup** — a document is preserved as it is; a second C0DATA
  document carries corrections and annotations against it. Boundaries and
  substitutions are the corrections; BEL notes are the annotator's
  remarks. The structure is identical to a patch.

## What SUB meant

In ASCII (1963, 1967) SUB, 0x1A, is *Substitute*: "a character that may
be substituted for a character which is determined to be invalid or in
error." Receiving equipment that detected a garbled character replaced it
with SUB so the record kept its length and the error stayed visible. ISO
2022 and ANSI X3.41 kept that sense and added one: a SUB inside an escape
sequence cancels the sequence and shows an error glyph. CP/M, and DOS
after it, used ^Z as the end-of-file mark in text files because their
file systems counted size in 128-byte records; Unix gave the same key to
job suspension. The original meaning, a stand-in for something known to
be wrong, is the one this sketch leans on: a substitution block says
"this is what the text should have been".

## Consequences for the implementations, if adopted

Validator: the diff branch is deleted; one base grammar. `Group` gains a
`substitution?` flag beside `dead?`. The general Builder writes a block
with its existing primitives plus `sub` before `gs`; `DiffBuilder` becomes
a thin composed layer or goes. `Diff.parse`/`apply` read ordinary groups
and records. `vectors/diff.json` (32 cases) regenerated. Ports with diff:
Crystal, JavaScript, Rust, Go, C. Editor grammar: one new prefix.
