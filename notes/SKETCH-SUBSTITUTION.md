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

## Second target: a C0DATA file

**Status:** proposed, from a thought experiment on 2026-11-06. Nothing here
is decided.

The challenge: write a diff against a C0DATA file rather than a text
file. It tests whether the block shape above is the format's shape or an
artefact of text patching.

Target for every example, `accounts.c0`:

    ␖␁shape␟tabular
    ␝users
    ␁␞name␟amount
    ␞Alice␟1502.30
    ␞Bob␟340.00
    ␄

### It already works, as bytes

Inside `␂…␃` only seven codes are escaped; FS GS RS US SOH are raw, so an
anchor can spell structure as bytes:

    ␚␝
    ␞␂␞Bob␟␃␟340.00␟350.00␟␂
    ␃

That is a diff of a file that happens to hold C0DATA. Anything in the
target that is not data breaks it: a reformat, a value re-spelled, a note,
a header row. A reader sees bytes, not a change to Bob's amount. The one
good thing about it is that the block shape needed no change to express it.

### Matching elements instead of bytes

Two moves, both with machinery the format already has. **Locating is a
reference:** a boundary record's one unit may be `ENQ`, and the path
ladder (group, record by id, field by header name) is the one a diff
needs. **Old and new are values, and a record or group quoted as a value
is a level** `␐…␘`.

Change one field (the boundary narrows the scope to one element, so no
anchor is needed):

    ␚␝
    ␞␅␂users␟Bob␟amount␃
    ␞␟340.00␟350.00

Change a field anchored by its neighbouring unit (the keyed-record case,
which paths cannot reach):

    ␞␅users
    ␞Bob␟340.00␟350.00

Replace a record; insert a record after Alice; delete Bob:

    ␞␅users
    ␞␟␐␞Bob␟340.00␘␟␐␞Bob␟350.00␘
    ␞␐␞Alice␟1502.30␘␟␟␐␞Carol␟12.00␘
    ␞␟␐␞Bob␟340.00␘␟

Same four columns as the text diff; insertion has a position because
record order is data. Exact-once in scope, cursor, validate-then-write
and atomicity carry over unchanged.

The mirror spelling, the target record with the change inline
(`␞Bob␟340.00␚350.00`), reads well for one field and is ruled out: it
cannot insert or delete a record, cannot touch a group, puts SUB back
inside a record, and gives a substitution record a second column rule.

### Bytes and elements: what differs

A column of a substitution record is either a byte string or a sequence
of elements. That is the whole difference, and everything below follows.

| | text (bytes) | data (elements) |
|---|---|---|
| a column | a byte string | plain/text value = one unit; level = records (or a group) |
| search | `before old after` concatenated, once in scope | adjacent sibling elements, once in scope |
| compared as | bytes as written | values after parsing; spelling does not count |
| scope, cursor | byte offsets | tree positions; an ENQ boundary's scope is the element it names |
| layout, notes, header rows in target | break anchors that span them | invisible |
| insertion | at a byte offset; can produce an ill-formed file | between elements; well-formed by construction |
| replace-all | every occurrence, overlaps counted | every equal element in scope |
| can edit | anything, including half a value | elements only; old is a whole unit |
| needs | nothing | a parser and serialiser of the target |

`␞Bob␟340.00␟350.00` shows the gap: as bytes it searches `Bob340.00`,
contiguous, and does not match the file (there is a US between); as
elements it is unit `Bob` then unit `340.00` in one record, and matches.
The bytes form of the same edit is `␞␂Bob␟␃␟340.00␟350.00`.

Two rules the element grain needs that bytes never did:

1. **One grain per substitution record.** All non-empty columns are the
   same kind of element: all units, or all record levels. Mixed is an
   error.
2. **Adjacency means siblings.** Unit before and unit old are consecutive
   units of one record; record before and record old are consecutive
   records of one group.

Because `Bob` is a legal column in both grains and means different
things, the grain is declared in the heading, not inferred. Proposed key:
`match`, values `text` (default; every existing diff: the target is read
as text) and `data` (the target is parsed as C0DATA). "Text" is the word
`DIFF.md` already uses for the target. The key's name is open; see below.

### What the experiment settles, if adopted

- **The block shape holds** under a change of target with no new grammar.
- **The anchor rule is a proxy.** `␞␟340.00␟350.00` after a field
  boundary has no anchor and is safe, because the scope is one element.
  The rule is: `before old after` matches exactly once in the current
  scope. Anchors and boundaries are two ways to make that true. An
  unanchored substitution is forbidden only in the leading scope, before
  any boundary. This also answers Open 3: the second of two
  substitutions on one line is legal when it is unique in the scope.
- **Replace-all's constraint is statable:** legal only inside a scope a
  boundary opened, never in the leading scope, never with an empty old.
  Its spelling is still open.
- **SUB placement is unmoved.** Making `␚␝users` mirror the target group
  was considered and rejected: the GS name would mean the block's own
  label in a text diff and the target's group in a data diff. Locators
  belong in boundary records.
- **Matching compares values after parsing**, so plain and text spellings
  of one value match. That is the point over the bytes form.

### Still open from this section

- Group-level edits: rename or delete a group means old and new are
  levels holding the whole group. Probably correct and rare.
- Paths cannot reach keyed records or anything inside a level (existing
  reference rule); such edits anchor by neighbouring units or quote the
  record. A limit, not a bug.
- The heading key's name and values.

## Third case: markup inside a document

**Status:** proposed, from discussion on 2026-11-07. The order `SUB DLE`
was agreed in discussion; nothing is normative yet.

This is not search and replace. An editor marks up a document in place:
the mark sits where the change is, so position is the anchor and nothing
is searched. The marks are part of the document.

### Where a mark goes

A marked span is an **island** inside a text value: a substitution level
opened in the text, holding a body, closed by CAN, with the text resuming
after it. The text stays one value.

    ␞␂Hello Mr. ␚␐␞Davis␟Davidson␇misremembered␘. How are you today?␃

Inside the island the grammar is body grammar: `␞Davis␟Davidson` is an
ordinary record, `␇misremembered` an ordinary note, `␘` the ordinary
closer. A CAN in the surrounding text is still a plain byte; the island,
not the text, is what the closer ends. A bare prose file is the content
of one text value, so the same notation applies to it unchanged.

Cutting the paragraph into units at each mark instead (run-split) is
ruled out: in the document shape a US in a block is a list item, every
run with edge whitespace would need a fence, and the paragraph stops being
one value.

### The marks

The island holds one record: the span as it was, then the span as it
should be. One unit is a comment on a span; two units are a change,
either side possibly empty. No omitted-column rule.

    substitute    Hello Mr. ␚␐␞Davis␟Davidson␇misremembered␘. How are you today?
    insert        Hello ␚␐␞␟Mr. ␘Davis.
    delete        Hello ␚␐␞Mr. ␟␘Davis.
    comment       Hello Mr. ␚␐␞Davis␇check spelling␘.

Because the island is a body, richer marks cost nothing new. Who and
when, as a keyed record when the remark is data rather than a note:

    ␚␐␞␁old␟Davis␁new␟Davidson␁by␟tom␁on␟2026-11-07␘

Two records in one island are two proposed readings. An island inside a
unit of another island is a reply to a mark.

### Three readings

*Original* takes the first unit everywhere; *clean* takes the second;
*marked* shows both with the remarks. The marks are content: hashed and
canonical. The editor's hand is part of the record.

### Whole paragraphs

A span cannot cross a record boundary and need not. Deleting a paragraph
already exists: bare BEL before RS marks the record dead. Inserting or
replacing one suggests the same prefix at record level,
`␚␞old paragraph␟new paragraph`, SUB saying "this record's units are old
and new". Not thought through; noted because it falls out of the same
idea.

### What it settles about SUB, if adopted

SUB goes **before** the opener it qualifies, the way `BEL GS`, `SOH RS`
and `BEL DLE` do: `␚␝name` opens a substitution block, `␚␐…␘` a
substitution level. One rule in every position. The alternative written
first, `␐␚`, would make DLE inside text mean "a code follows", the reverse
of its escape sense, and would put SUB on the other side of the opener
from the block form.

Consequence: inside text SUB becomes the **eighth escaped code**. A raw
SUB in text opens an island and a literal SUB is written `␐␚`. Values
already fence SUB, since any control code forces text spelling; what
changes is the tokenizer's escape set in every port and the text vectors.
Literal SUB in real text is rare (it is the DOS end-of-file mark). The
same bytes `␚␐…␘` also work as a substitution level in unit position
outside text.

## Open

1. **Placement of SUB.** `SUB GS` is the sketch. Alternatives raised:
   `SUB FS` ("every section in this file is a block", saves a byte per
   block, nothing else); both. The third section settles the *order*
   (SUB before the opener it qualifies) in discussion; which openers take
   it (GS, DLE, RS, FS) is still open.
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
6. **Anchor rule.** Keep "at least one of before/after non-empty", or
   replace it with "exactly once in the current scope, unanchored
   forbidden only in the leading scope" as the second section proposes.
7. **Grain key.** Whether the heading declares text versus data
   matching, and under what key (`match␟text` / `match␟data` proposed;
   the values are agreed in discussion, the key name is not).
8. **Element-grain rules** (one grain per record, adjacency means
   siblings) and group-level edits, from the second section.
9. **Inline islands.** Adopting `␚␐…␘` inside text makes SUB the eighth
   escaped code (tokenizer and text vectors change in every port). Needs
   a decision before any grammar text is written.
10. **Record-level SUB** (`␚␞old␟new`) for whole-paragraph marks: whether
    it exists.

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
