# Proposal: Supersession (and C0DIFF inside the base grammar)

**Status:** Decided 2026-11-12 in every part and written into DESIGN.md, GRAMMAR.md and DIFF.md the same day; kept as history
**Date:** 2026-11-12 (sketch 2026-11-06, rewritten 2026-11-07, revised
after the C0DIFF review `REVIEW-2026-11-09-C0DIFF.md` and renamed from
`SKETCH-SUBSTITUTION.md` on 2026-11-10). Nothing is normative, nothing is
built. The 2026-11-06 text, with the proposals this one discards, is in
git history (`d02ca9b`); the 2026-11-07 text, with the pair as a unit
kind, is at `434c06c`.

**Proposes:** one rule for the base grammar (`DESIGN.md`, `GRAMMAR.md`):
SUB before a separator or opener supersedes the element before it. And
its first use: C0DIFF restated as files of records under that rule, which
becomes the rewrite of `DIFF.md`. C0MARK (`MARK.md`) is the second use
and its own proposal.

**Decided 2026-11-08:** the substitution mechanism is defined once, in the
base grammar (`GRAMMAR.md`, `DESIGN.md`); the two uses are separate
specifications. **C0DIFF** (`DIFF.md`) is the text diff, a document shape
that finds its place by matching; it gates 1.0. **C0MARK** (`MARK.md`,
preliminary draft 2026-11-08) is editorial marks inside a document,
position-anchored, and is a 1.x proposal that does not gate 1.0.

**Decided 2026-11-09:** the mechanism is legal everywhere the base grammar
admits it, with one meaning; a shape constrains which grains it allows.
The word *boundary* is dropped: a diff record with no substitution is an
**assertion**, and that is the whole of what it is.

**Decided 2026-11-10:** the pair as a unit kind (`old␚new`, SUB between two
values inside one unit) is **withdrawn**. Its job is done by
**supersession**, SUB before the separator: `old␚␟new`. The pair needed
mandatory sides to keep `old␚␞end` from reading two ways, and mandatory
sides needed `␂␃` as the one canonical spelling of an empty side, a
carve-out from the rule that the empty string is written as nothing.
Supersession has neither problem: the byte after SUB is always a code, so
the grain is named and nothing is ambiguous, and an empty side is an empty
unit, spelled as nothing between two codes, as every empty unit is. One
rule where there were two. The scope of the rule (every separator and
opener, stated once) is the recommendation that went with that decision;
it is written below as agreed.

**Decided 2026-11-12:** the constraint list for diff records (review
decision 3): every slot the text diff does not use is an **error**, so each
stays free for a later additive meaning; dead records and dead file lines
included, because a diff is an instruction and a hunk that reads as live
but does not apply is the trojan-source shape of hazard; the note form
(`␇␂␞…␃`) is how a hunk is kept without applying. Notes are allowed. GS
in a diff is an error (closes Open 3). The list is under "The constraint
list" below.

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

C0DATA keeps that. `old␚␟new` puts SUB right after the fault, with what
was there before it and what should be there after the separator.
Everything below is that mark at one grain or another.

The framework test every piece must pass: **every shape parses under the
base grammar. A shape gives meaning and adds constraints; it never changes
what follows a code.** What was wrong with the current C0-DIFF is only
that it put the pattern on the GS line, so GS stopped meaning "group".

## Supersession: SUB before a separator or opener

**Rule.** Outside text, SUB immediately before US, SOH, RS, GS or FS marks
the element that precedes that code as **superseded** by the element that
follows it, at the grain of that code. SUB before any other byte outside
text, or at the end of input, is an error; the slot stays reserved.

    old␚␟new      the unit before is superseded by the unit after
    …␚␁k␟v        the keyed unit before, by the keyed unit after
    …␚␞…          the record before, by the record after
    …␚␝name       the group before, at that depth, by the group after
    …␚␜name       the file before, by the file after

**Meaning.** The superseded element was wrong; the superseding one stands
in its place. A reader hands both on, in order, with the fact that the
second supersedes the first; it never takes anything back, because it
streams. What to do with the fact is the consumer's: a document model
drops the superseded node as it builds the tree, a diff applier keeps
both as search and replacement, a marked-copy tool shows both. This is
the 1963 rule lifted a grain, and it pairs with BEL: `␇␞` kills what
follows (known before writing), `␚␞` replaces what precedes (found out
after).

**Empty sides.** An empty unit is nothing between two codes, so:

    ␞old␚␟new␞end     record 1 [old→new], record 2 [end]
    ␞old␚␟␞end        record 1 [old→""], a deletion; record 2 [end]
    ␞␚␟new            record 1 [""→new], an insertion
    ␞a␟b␚␟␟c          [a, b→"", c]: three units in the result

No `␂␃` is ever needed, and `␂␃` keeps its one meaning everywhere: a
non-canonical empty text.

**Arity.** "N separators, N+1 units" counts what was written; the
**result** of a record, after supersession, omits the superseded units, so
`␞a␟b␚␟␟c` has three units as the 1963 SUB kept the record's length.
Superseding chains: `␞a␚␟b␚␟c` is `[c]`, with `a` and `b` both handed on.

**Nothing to supersede.** A unit always has a predecessor, since the first
unit of a record exists even when empty. A record, group or file does not:
`␝g␚␞x` with no record before it in the group is an error, as is `␚␝` with
no earlier group at that depth and `␚␜` with no earlier file.

**Why on the separator and not in the value.** `old␚new` (the withdrawn
pair) put the right side straight after SUB, so an empty right side had to
be spelled or the parser could not tell `old␚` + `␞end` from `old` + `␚␞end`.
With the separator after SUB there is always a code there, and the code
says the grain. The earlier objection to `SUB US`, that it adds a unit, is
answered by the arity rule: the superseded unit is written and handed on
but not counted in the result.

**Where it is legal.** Everywhere the grammar admits the code that follows
it; the meaning is the base grammar's and does not vary by shape. A shape
says which grains it allows: C0DIFF allows the unit grain (and only that,
pending the constraint list); C0MARK allows unit and keyed-unit grains in
records and islands; a data document may use any grain, a correction
written in band.

**Canonical form and hashing (confirmed 2026-11-12).** Supersession is
content: a document that says "this, superseded by that" is a different
document from one that says only "that". Canonical form keeps it and
hashes it as written, with each side in its own one spelling (plain or
text by the usual rule). The deciding case is the diff: a C0DIFF document
is made of supersessions, and if canonical form applied them,
canonicalising `␞␂Hello ␃␟world␚␟universe␟!` would leave
`␞␂Hello ␃␟universe␟!`, the replacement text alone; the diff would be
gone and its content hash would be the hash of its output. The rule is
the base grammar's and has one meaning, so canonical form cannot apply it
in one shape and keep it in another. It therefore differs from BEL, which
canonical form strips: a note is outside the data, a supersession is a
statement about it. The cost falls on data documents: a log corrected in
band (`␞Bob␟340.00␗` then `␚␞Bob␟350.00␗`) and one written right the
first time have different content hashes. A tool that wants the
corrected data, or its hash, takes a reading (C0MARK's *clean*), as it
takes the live records of a document with dead ones. The ETB digest is
unaffected either way: it covers each block's bytes as written, so the
correction is covered by its own block and the block it corrects stays
verifiable.

**The two earlier objections** (2026-11-07, when supersession was demoted
to exploratory) were that it cannot say *which* element it corrects and
that a consumer must retract. The first is answered by what it is for: at
the unit grain inside a diff or a mark the superseded side *is* the
address, and at the record grain in a log the position right after
writing is the 1963 case; a correction that needs a key or a sequence
number is the data-target diff, below, which supplies addresses. The
second is not the parser's problem: it passes the fact along, and a
consumer that cannot retract holds one sibling at the grain it cares
about, which for a unit or a record is bounded.

The builder already writes it: bare `sub()` before `us`, `rs`, `gs`, `fs`
or `soh`. The convenience `us("10").sub("20")` that spelled a pair is
withdrawn.

## C0DIFF: the text diff

The name loses its hyphen to match C0DATA; the heading value stays
`shape␟diff`.

    ␖␁shape␟diff
    ␜greeting.txt
    ␞␂Hello ␃␟world␚␟universe␟!
    ␄

A diff is files of records. Nothing marks a record as a diff record; the
shape does.

- **FS path**, as in `DIFF.md`.
- **A record** is one anchored pattern. Its units that are not superseded
  and do not supersede are **anchors**; a superseded unit with its
  superseding unit is a **substitution**. Its **search text** is the
  concatenation of its anchors and superseded units in order; its
  **replacement** is the same with each superseding unit in place of the
  one it supersedes. This is `DIFF.md`'s section, spelled RS instead of GS.
- A record with no substitution is an **assertion**: its search text must
  match, and the cursor moves past it. A record with substitutions is a
  **substitution record**.
- Rules carried over unchanged: the search text matches exactly once
  after the cursor; the cursor moves to the end of the match; empty
  search text is an error; a file with no records asserts existence; the
  same path twice is an error; BEL, ETB, EOT as everywhere.

    ␜tally.rb
    ␞def tally(items)                 assertion
    ␞␂  ␃␟count␚␟total␟␂ = 0␃         anchored both sides
    ␞␂  # TODO␃␚␟                     deletion, anchored by indent
    ␞␂x = ␃␟10␚␟20␟ + ␟5␚␟15          two substitutions, one record
    ␞end                              assertion

### The constraint list

Decided 2026-11-12. The base grammar admits everything below; the diff
shape rejects it. The principle: every slot the text diff does not use is
an **error**, so each stays free for a later additive meaning (a keyed
diff record is the natural future spelling of replace-all; the record
grain of supersession is reserved for the data diff).

Errors in a diff:

- a keyed unit, a level or a reference anywhere in a record, superseding
  or not;
- a header row;
- GS (closes Open 3);
- a record before the first FS; an empty FS path;
- a chained supersession `a␚␟b␚␟c`: the search text would hold `b`, which
  the target never held;
- supersession at any grain but the unit: `␚␞`, `␚␝`, `␚␜`, `␚␁`;
- a record whose search text is empty: `␞`, and a bare insertion
  `␞␚␟new`; an insertion is anchored, `␞␂Hello ␃␟␚␟universe`;
- a substitution of nothing by nothing, `␟␚␟` (low stakes; a no-op in a
  patch is a mistake, and the diff's style is strict);
- a **dead record or dead file line**. A diff is an instruction, and the
  hazard is the gap between what a reader sees and what the machine does:
  a dead record has anchors and substitutions and sits in sequence with
  the live hunks, and one byte, often rendered as nothing, makes it inert.
  Atomicity says the same from the other side: a diff with dead hunks is
  one designed to apply partially. The mechanism is redundant here, since
  a text note holds a hunk intact and unmistakably as a comment:

      ␇␂␞␂  # TODO␃␚␟␃

  What is written applies.

Allowed: notes (`␞a␚␟b␇n`), which change nothing. An island (`␐␞…␘`
inside text) is not 1.0 grammar at all, since DLE inside text is legal
only before the seven escaped codes; the diff inherits that, and C0MARK,
when it comes, keeps diff text island-free.

Base-grammar rules confirmed while here: SUB joins the list of codes BEL
may not precede; `␚` at end of input is an error; `␚` before anything but
a separator or opener (`␚a`, `␚␂`) is an error.

Integrity is not the constraint list's concern: a diff may end with a
committed, hashed block (`␗sha256:…␄`) as any document may, and an
applier that knows the payload semantics (DESIGN.md, ETB Payload, still
to be specified) checks it before applying. Uniqueness measured to end
of file (Open 2) also means a skipped or missing assertion can only
widen a search window, which either finds the same single match or
fails; it never redirects a change.

### What changes against DIFF.md

- Patterns move from the GS line to RS records. `diff-body`, `section`,
  `replace`, `dpre`, `pattern`, `dunit`, `dvalue` leave `GRAMMAR.md`; the
  base grammar gains supersession.
- The replace-all RS line is gone, because RS is now a record. Replace-all
  has no spelling (see Open).
- `shape␟diff` no longer selects a grammar. It says what the document is
  for, as every shape does.
- GS has no role in a diff. Whether it is forbidden or tolerated as a label
  is open.

### Open, for C0DIFF

1. **Replace-all.** Decided 2026-11-12: **no mark, ever needed.**
   Replace-all is N anchored substitutions, and a tool produces them from
   the target: find every `x`, take enough context on each side to make
   each match unique, write one record per occurrence. The expanded diff
   is the preview (each record shows the change in its context), what
   applies is explicit and atomic, and undo is free: the inverse diff is
   the same records with `old␚␟new` turned to `new␚␟old`, which a careful
   tool checks against the result before committing. The blind
   replace-all, authored without the target and shipped to many files, is
   exactly the case the format should not be able to express. The "all x
   to y" is a c0fmt input (`diff --all`, after 1.0), not a diff record.
   The keyed-record slot stays reserved. (Earlier: left out on purpose;
   constraints statable; review recommended defer.)
2. **Where uniqueness is measured.** Decided 2026-11-12: `DIFF.md`'s
   rule, exactly once from the cursor to the end of the file. The
   alternative (to the next assertion's match) would need the next
   assertion matched first and loses the property that a missing or
   skipped assertion can only widen a window, never redirect a change.
3. **GS in a diff:** decided 2026-11-12, an error (part of the constraint
   list).
4. **Shape name.** Decided 2026-11-08: `diff`. Marks (C0MARK) are not a
   shape; they sit inside text in any document.
5. **The constraint list.** Decided 2026-11-12; see "The constraint
   list" below. (Deferred 2026-11-09 as review decision 3.)

## C0MARK: marks in a document

Named 2026-11-08: **C0MARK**, proposal in `MARK.md` (written from this
section the same day; `MARK.md` is now the fuller text). Editor's marks,
as in proofreading: insertion, deletion, substitution, comment. Not search
and replace. An editor marks a document in place; position is the anchor.
Separate specification; does not gate C0DIFF or 1.0.

A whole-unit mark is a supersession in the record:

    ␞old paragraph␚␟new paragraph

A mark inside a text value is an **island**: a level opened in the text,
holding a record, closed by CAN, with the text resuming after it.

    ␞␂Hello Mr. ␐␞Davis␚␟Davidson␇misremembered␘. How are you today?␃

    substitute    Hello Mr. ␐␞Davis␚␟Davidson␘. How are you today?
    insert        Hello ␐␞␚␟␂Mr. ␃␘Davis.
    delete        Hello ␐␞␂Mr. ␃␚␟␘Davis.
    comment       Hello Mr. ␐␞Davis␇check spelling␘.

A record of one plain unit is a comment on a span. Richer marks cost
nothing new, since the island is a body: `␐␞␁old␟Davis␁new␟Davidson␁by␟tom␘`
for attribution; two records for two proposed readings; an island inside
a superseding unit for a reply to a mark.

Three readings: *original* takes every superseded unit, *clean* every
superseding one, *marked* shows both with the notes (the marked copy, as
in proofreading). Marks are content, hashed and canonical; the editor's
hand is part of the record. Deleting a paragraph already exists: bare BEL
before RS.

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
key says which rule applies. Whole-unit marks need no new grammar at all
and are legal the moment supersession is.

## Log correction

The record grain in a data document: the writer found the mistake right
after making it and fixes it in band, which is the one way to correct a
committed block in an append-only log.

    ␞Bob␟340.00␗
    ␚␞Bob␟350.00␗

The base rule covers it; nothing more is proposed. Whether a stream shape
wants to say anything about it (a correction that crosses a commit, a
correction by key rather than position) is that shape's question and is
not opened here.

## Against a C0DATA target

Deferred to after 1.0. A diff whose target is parsed as C0DATA, matching
elements rather than bytes, under a heading key (`match␟text` default,
`match␟data`; key name open). An assertion may be a reference (`␞␅users`,
`␞␅␐␝users␞Bob␟amount␘`); a unit-grain change is a supersession in a mirror
record (`␞Bob␟340.00␚␟350.00`); a record-grain change is a record
supersession inside the diff (`␞Bob␟340.00␚␞Bob␟350.00`). Both are the
one rule above at two grains. Pure addition; no existing diff changes.
Only the key name `match` should be reserved now.

## Use cases

- **Code patch:** C0DIFF, what `DIFF.md` was written for.
- **Editor's marks:** C0MARK, supersessions in records and islands.
- **Log correction:** record supersession after a commit.

## Discarded on the way

So they are not re-proposed: `SUB GS` and `SUB DLE` as block and island
qualifiers; fixed columns `before␟old␟new␟after`; SUB as an eighth
escaped code; run-split paragraphs; the GS name mirroring a target group;
the **pair as a unit kind** (`old␚new`, withdrawn 2026-11-10: it needed
mandatory sides and a canonical `␂␃`, and it was a second mechanism beside
supersession saying the same thing). `SUB US` was on this list on
2026-11-07 because it "adds a unit"; it does not, once the superseded
unit is handed on and not counted, and it is now the mechanism.

## Consequences for the implementations, if adopted

C0DIFF: `Diff.parse`/`apply` read records instead of GS lines; the diff
branch leaves the validator; `vectors/diff.json` (32 cases) regenerated;
grammar vectors for supersession. Ports with diff: Crystal, JavaScript,
Rust, Go, C. Supersession touches every port's tokenizer lightly: SUB
outside text followed by US, SOH, RS, GS or FS is a qualifier on that
code, as BEL is on the code after it; followed by anything else it is an
error. Document models gain a superseded flag or event. C0MARK islands,
if and when adopted, touch every port's parser and Document model and
need their own vectors; they are not needed for C0DIFF.

## How to resume this

Every open item is decided (2026-11-12: constraint list, Open 1 no
replace-all mark, Open 2 end-of-file uniqueness, Open 3 GS an error,
canonical/hash stance confirmed: supersession is content, hashed as
written). Written into `DIFF.md`, `GRAMMAR.md` and `DESIGN.md` and the
vectors regenerated the same day; this note is history. Next: port
Crystal first. C0MARK is a separate
specification (`MARK.md`, proposal drafted) and follows 1.0.
