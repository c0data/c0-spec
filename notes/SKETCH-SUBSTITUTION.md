# Sketch: Substitution (C0DIFF inside the base grammar)

**Status:** Sketch, rewritten 2026-11-07. Direction agreed in discussion;
nothing is normative, nothing is built. The 2026-11-06 text, with the
proposals this one discards, is in git history (`d02ca9b`).

**Decided 2026-11-08:** the pair is defined once, in the base grammar
(`GRAMMAR.md`, `DESIGN.md`); the two uses are separate specifications.
**C0DIFF** (`DIFF.md`) is the text diff, a document shape that finds its
place by matching; it gates 1.0. **C0MARK** (`MARK.md`, preliminary draft 2026-11-08) is
editorial marks inside a document, position-anchored, and is a 1.x
proposal that does not gate 1.0. Both use the pair with the same spelling
and the same empty side, which is why the pair lives in neither.

**Replaces, if adopted:** the `diff-body` grammar in `GRAMMAR.md` and the
Structure section of `DIFF.md`. The semantics of `DIFF.md` (search text,
exact-once match, cursor, insertion, deletion, assertion,
validate-then-write, atomicity) are kept word for word.

## The premise

In ASCII SUB is *Substitute* (named in the 1967 revision; the 1963 chart
had only a numbered separator at 0x1A): a receiver that found a garbled
character wrote SUB in its place, so the record kept its length and the
fault stayed visible where it occurred. SUB never pointed somewhere else.
It sat on the spot.

C0DATA keeps that. `old␚new` puts SUB where the fault is, with what was
there on its left and what should be there on its right. Everything below
is that mark at one grain or another.

The framework test every piece must pass: **every shape parses under the
base grammar. A shape gives meaning and adds constraints; it never changes
what follows a code.** What was wrong with the current C0-DIFF is only
that it put the pattern on the GS line, so GS stopped meaning "group".

## The pair: a unit kind

Proposed addition to `GRAMMAR.md`:

    unit  = value / level / reference / pair
    pair  = value SUB value                    value = plain / text

Both sides are always present; an empty side is spelled as empty text,
`␂␃`. SUB inside text stays a plain byte; a pair is spelled outside text,
each side in its one spelling:

    world␚universe        ␂Hello ␃␚␂Hi ␃        ␂␃␚new        old␚␂␃

Meaning: the left value is wrong, the right value replaces it. Empty left
is an insertion, empty right a deletion. A pair keeps the record's unit
count, as the 1963 SUB kept the record's length; that is why the change
is inside the unit and not a `SUB US` that would add one.

Why the sides are mandatory: with an optional side, `old␚␞end` reads
both as a deletion followed by a record and as a record followed by a
SUB-qualified one. With both sides present the byte after SUB decides
everything with no lookahead: a plain byte or STX is the right side; a
code is not a pair. `SUB` before an opener is therefore a free,
unambiguous slot (see Supersession below). Canonical form: `␂␃` is the
one spelling of an empty pair side, as text is the one spelling of a
value with edge whitespace. Two bytes per insertion or deletion is the
price.

A shape that does not define the pair rejects it, as SUB is rejected
outside a diff today. Two shapes define it: diff (below) and document
(markup, below). The pair is hashed as written.

The builder already writes it: `us("10").sub("20")` is `␟10␚20`.

## C0DIFF: the text diff

The name loses its hyphen to match C0DATA; the heading value stays
`shape␟diff`.

    ␖␁shape␟diff
    ␜greeting.txt
    ␞␂Hello ␃␟world␚universe␟!
    ␄

A diff is files of records. Nothing marks a record as a diff record; the
shape does.

- **FS path**, as in `DIFF.md`.
- **A record** is one anchored pattern. Its plain units are **anchors**,
  its pairs are **substitutions**. Its **search text** is the
  concatenation of its anchors and pair-lefts in order; its
  **replacement** is the same with each pair-right in place of its left.
  This is `DIFF.md`'s section, spelled RS instead of GS.
- A record with no pair is a **boundary**: an assertion that moves the
  cursor. A record with pairs is a **substitution record**.
- Rules carried over unchanged: the search text matches exactly once
  after the cursor; the cursor moves to the end of the match; empty
  search text is an error; a file with no records asserts existence; the
  same path twice is an error; BEL, ETB, EOT as everywhere.

    ␜tally.rb
    ␞def tally(items)                 boundary
    ␞␂  ␃␟count␚total␟␂ = 0␃          anchored both sides
    ␞␂  # TODO␃␚␂␃                    deletion, anchored by indent
    ␞␂x = ␃␟10␚20␟ + ␟5␚15            two substitutions, one record
    ␞end                              boundary

### What changes against DIFF.md

- Patterns move from the GS line to RS records. `diff-body`, `section`,
  `replace`, `dpre`, `pattern`, `dunit`, `dvalue` leave `GRAMMAR.md`; the
  base grammar gains `pair`.
- The replace-all RS line is gone, because RS is now a record. Replace-all
  has no spelling (see Open).
- `shape␟diff` no longer selects a grammar. It says what the document is
  for, as every shape does.
- GS has no role in a diff. Whether it is forbidden or tolerated as a label
  is open.

### Open, for C0DIFF

1. **Replace-all.** Left out of the original design on purpose: an
   unconstrained replace-all is how a diff makes mistakes. Constraints now
   statable: legal only in a scope opened by a boundary, never in the
   leading scope, never with an empty old, every match replaced. It needs
   a mark of its own; none is proposed. It is not needed for 1.0 and
   leaving it out is additive later.
2. **Where uniqueness is measured.** `DIFF.md`: exactly once from the
   cursor to the end of the file. Alternative: exactly once from the
   cursor to the next boundary's match, which makes short anchors
   practical but needs the next boundary matched first. Lean: keep
   `DIFF.md`'s rule for 1.0.
3. **GS in a diff:** forbidden, or an inert label.
4. **Shape name.** Decided 2026-11-08: `diff`. Marks (C0MARK) are not a
   shape; they sit inside text in any document.

## C0MARK: marks in a document

Named 2026-11-08: **C0MARK**, proposal in `MARK.md` (written from this
section the same day; `MARK.md` is now the fuller text). Editor's marks, as in proofreading: insertion, deletion,
substitution, comment. Not search and replace. An editor marks a document
in place; position is the anchor. Separate specification; does not gate
C0DIFF or 1.0.

A whole-unit mark is a pair in the record:

    ␞old paragraph␚new paragraph

A mark inside a text value is an **island**: a level opened in the text,
holding a record, closed by CAN, with the text resuming after it.

    ␞␂Hello Mr. ␐␞Davis␚Davidson␇misremembered␘. How are you today?␃

    substitute    Hello Mr. ␐␞Davis␚Davidson␘. How are you today?
    insert        Hello ␐␞␂␃␚Mr. ␘Davis.
    delete        Hello ␐␞Mr. ␚␂␃␘Davis.
    comment       Hello Mr. ␐␞Davis␇check spelling␘.

A record of one plain unit is a comment on a span. Richer marks cost
nothing new, since the island is a body: `␐␞␁old␟Davis␁new␟Davidson␁by␟tom␘`
for attribution; two records for two proposed readings; an island inside
a pair-right for a reply to a mark.

Three readings: *original* takes every pair's left, *clean* its right,
*marked* shows both with the notes (the marked copy, as in proofreading). Marks are content, hashed and
canonical; the editor's hand is part of the record. Deleting a paragraph
already exists: bare BEL before RS.

**Grammar needed:** inside text, DLE followed by a body opener (FS GS RS
SOH BEL) opens a level that CAN closes; DLE before one of the seven stays
an escape; DLE before anything else stays an error. No new escaped code.

    text   = STX *( tbyte / island ) ETX
    island = DLE lbody CAN

**Cost, stated:** a scanner that skips a text value whole must now count
DLE-opened levels inside it, and an unescaped STX may appear inside an
island inside text. A document without islands scans exactly as before.
Run-split (cutting the paragraph into units at each mark) was considered
and ruled out: a US in a block is a list item in the document shape.

**Compatibility, if adopted after 1.0:** under 1.0's text rule, DLE
followed by anything but the seven escaped codes is an error, so every
valid 1.0 document stays valid under C0MARK, and a 1.0 reader rejects a
marked document cleanly instead of misreading it. The heading's version
key says which rule applies. Whole-unit marks (a pair in a record) need
no new grammar at all and are legal the moment the pair is.

## Data: supersession (exploratory)

**Status:** exploratory only (2026-11-07). Not proposed for any version.
Kept because the idea is sound and the slot is reserved; not adopted
because of two problems below.

SUB before an opener would supersede the previous sibling of that kind:

    ␚␜name      the previous file
    ␚␝name      the previous group at that depth
    ␚␞…         the previous record in the group

This is the 1963 rule lifted a grain: the writer found the mistake right
after making it and fixes it in band, which is the one way to correct a
committed block in an append-only log. It pairs with BEL: `␇␞` kills
what follows (known before writing), `␚␞` replaces what precedes (found
out after). It is data correction and has nothing to do with C0DIFF,
which is text replacement and annotation.

**Why it is not adopted:**

1. **It cannot say which.** "The prior one" is a position. A log
   correction needs an address: a key, a sequence number, a path
   reference. The deferred data-target diff has addresses; this does
   not. Until it can name its target it does not do the job it was
   wanted for.
2. **The consumer retracts.** The parser never backtracks (the byte after
   SUB decides), but whoever already received the previous element must
   undo it. Every other construct in the format looks forward. A
   non-retracting streaming consumer would have to hold the last sibling:
   one record for `␚␞`, a whole group or file for `␚␝` and `␚␜`,
   unbounded. If anything is ever adopted it is the record grain only.

The pair's mandatory sides keep `SUB <opener>` free for whatever
addressing form this eventually takes. The builder's bare `sub` writes
the byte; it has no defined meaning.

## Against a C0DATA target

Deferred to after 1.0. A diff whose target is parsed as C0DATA, matching
elements rather than bytes, under a heading key (`match␟text` default,
`match␟data`; key name open). A boundary may be a reference (`␞␅users`,
`␞␅␂users␟Bob␟amount␃`); a unit-grain change is a pair in a mirror record
(`␞Bob␟340.00␚350.00`); a record-grain change is probably supersession
inside the diff (`␞Bob␟340.00` then `␚␞Bob␟350.00`), to be worked out
against the rule above. Pure addition; no existing diff changes. Only the
key name `match` should be reserved now.

## Use cases

- **Code patch:** C0DIFF, what `DIFF.md` was written for.
- **Editor's marks:** C0MARK, pairs and islands in a document.
- **Log correction:** supersession after a commit (exploratory).

## Discarded on the way

So they are not re-proposed: `SUB GS` and `SUB DLE` as block and island
qualifiers; fixed columns `before␟old␟new␟after`; SUB as an eighth
escaped code; run-split paragraphs; the GS name mirroring a target group;
`SUB US`. Each was a way of putting back, somewhere else, the information
the pair carries in place.

## Consequences for the implementations, if adopted

C0DIFF: `Diff.parse`/`apply` read records instead of GS lines; the diff
branch leaves the validator; `vectors/diff.json` (32 cases) regenerated;
grammar vectors for the pair. Ports with diff: Crystal, JavaScript, Rust,
Go, C. The pair as a unit kind touches every port's tokenizer/model
lightly (SUB outside text splits a unit). C0MARK islands and
supersession, if and when adopted, touch every port's parser and Document
model and need their own vectors; neither is needed for C0DIFF.

## How to resume this

Decide, in order: the pair as a unit kind with mandatory sides (yes/no);
C0DIFF open items 2 to 4; then rewrite `DIFF.md` and `GRAMMAR.md`,
regenerate vectors, port Crystal first. C0MARK is a separate
specification (`MARK.md`, proposal drafted) and follows 1.0.
Supersession is exploratory and needs an addressing form before it is a
proposal.
