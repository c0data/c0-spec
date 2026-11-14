# Proposal: SUB GS is depth; supersession is withdrawn; the diff needs no mark

**Status:** Direction agreed 2026-11-14 (SUB GS for depth, supersession
withdrawn, C0DIFF without a mark). Every detail below is open until taken
one by one; nothing is written into DESIGN.md, GRAMMAR.md or DIFF.md yet and
nothing is built. Supersedes `PROPOSAL-SUPERSESSION.md` (decided 2026-11-12,
built in all seven ports 2026-11-13), which stays as history.
**Date:** 2026-11-14.

**Proposes:** three changes to the base grammar and one to the C0DIFF
profile.

1. **SUB before GS is depth.** A group line is `*SUB GS name`; its depth is
   one plus the number of SUB. `␝a` is depth one, `␚␝b` depth two, `␚␚␝c`
   depth three. GS repetition is no longer depth.
2. **Repetition is an empty element for every code**, GS included: `␝␝b` is
   an empty-named group followed by group `b`, as `␟␟` is an empty unit and
   `␞␞` an empty record. The limitation paragraph, the canonicaliser's
   refusal clause and the lookbehind for GS runs go.
3. **Supersession is withdrawn** at every grain. SUB has one meaning, depth,
   and is an error anywhere but before GS.
4. **C0DIFF is defined by position**, not by a mark: a record's units are
   read in threes, anchor, old, new, with an optional closing anchor.
   Nothing in GRAMMAR.md is there for the diff.

Two side decisions ride along: a depth may not be skipped (`␝a␚␚␝c` is an
error), and `BEL` kills a group line whole, SUB prefix included (`␇␚␝b`).


## Why

The format review (2026-11-09) and the port of supersession (2026-11-13)
together showed three things.

**Supersession has no use in a machine-written format.** Its 1963 meaning
is a typist's correction of the character just struck. Lifted to elements
it was defensible at the record grain for append-only logs, where nothing
else can retract a committed record, but no client asked for it, and the
group and file grains had no use at all. The group grain is where the
ports diverged (`␝a␝␝b␝c␚␝␝d`: does `d` supersede `b` across parents?), a
question that only exists because the feature does. A correction that must
say *which* element it corrects is a keyed record or a reference, which the
data layer already has; a correction that would rewind a stream to a match
is a streaming diff, a 1.x profile if ever wanted (sketched at the end).
The one real user of SUB was the diff, and the diff can do without it.

**GS repetition was the one irregularity.** For every other code,
repetition means an empty element. For GS it meant depth, which made an
empty-named group unable to precede another group, made a canonicaliser
refuse to strip the note in `␝␇n␝b`, required a tokenizer to look behind
for GS runs, and produced skipped depths with null-name sections in the
model. With SUB free, depth can be spelled with a prefix and the
irregularity disappears. The outline stays flat, which is the reason to
have depth at all: a nested level must close, so a section cannot be
appended to a chapter at the end of a stream; a flat outline can be.

**One grammar, no dialects.** A `shape` names a profile, the constraints a
consumer applies and what it does with the result; it never changes how
bytes parse, because bytes travel without their heading (a level inside a
unit, a block in a stream, a body pasted into another). So a feature is
either in the core for everyone or not in 1.0. Depth is in the core, spelled
regularly. Supersession is out. The diff is a profile with nothing of its
own in the grammar.

The sacrifice is SUB's name. "Substitute" becomes "subordinate", a pun on
the abbreviation rather than the 1963 meaning. The second blog post says
SUB's meaning arrives with the C0DIFF post; that sentence changes, the
count of sixteen does not.


## The grammar

GRAMMAR.md, replacing the current lines.

    file-line  = [ BEL L ] FS L name L
    group-line = [ BEL L ] *SUB GS L name L
    hunit      = [ BEL L ] SOH L name L US L [ hvalue ]
    record     = RS L ( keyed / positional )
    positional = unit *( US L unit )
    keyed-unit = [ BEL L ] SOH L name L US L unit

`sup` is deleted from every rule, and the paragraph defining it. Replacing
the GS paragraph:

> The number of SUB before a GS is the group's depth less one: `␝a` is at
> depth one, `␚␝b` at depth two. The SUB run is contiguous and stands
> directly before the GS; layout follows the GS as everywhere. A group's
> depth is at most one more than the depth of the previous live group in
> the same file, and the first live group of a file is at depth one; a
> deeper group is an error ("depth skipped"). Repetition of a code is an
> empty element for every code: `␝␝b` is an empty-named group then group
> `b`. SUB before any byte but GS, or at the end of input, matches no
> production.

Implementer note: SUB joins the one-byte lookahead set (`SUB` then `GS`);
the "one code of lookbehind, or a counter, for GS depth" clause goes.

A pattern (references) spells depth the same way: `␅␐␝docs␚␝intro␞3␘`.

### Open points on the grammar

- **Layout inside the prefix.** Proposed: none (`␚ ␝` is an error). The
  alternative, `*( SUB L ) GS`, costs nothing in a reader but admits a
  spelling nobody wants. Recommendation: contiguous.
- **Skipping.** Proposed: forbidden, measured against the previous *live*
  group of the file, so dead groups are transparent as everywhere and a
  canonicaliser that strips a dead group never creates a skip (a dead
  group's deeper subsections die with it, so no live group follows it at a
  deeper depth). The alternative is today's rule, "a reader reports what is
  written and invents nothing", which keeps null-name sections in every
  model and harness. Recommendation: forbid.
- **BEL and SUB.** Proposed: `␇␚␝b` is a dead group line at depth two;
  `␚␇␝b` is an error (SUB before BEL). Today `BEL` before `SUB` is an error
  because SUB was not an element; now SUB is part of the element's line.
- **Depth of a dead group for the skip rule.** It is not counted (dead is
  not there). `␝a␇␚␝x␚␚␝c` is a skip and an error.


## DESIGN.md changes

- *Assigned Control Codes*: SUB's row becomes "depth prefix: `␚␝` is a
  subgroup". The lifted-meaning paragraph says "subordinate".
- *Structural Hierarchy* and *Names*: a group name may be empty; `␝␝b` is
  two groups; the limitation paragraph is deleted.
- *Supersession (SUB)*: section deleted. The "two severities" and "canonical
  span" terminology stays where it is used elsewhere.
- *Document Mode (Depth via GS Repetition)*: retitled "Depth (SUB GS)"; the
  example becomes

        ␖␜My Document
        ␝Chapter 1
        ␞First paragraph of chapter one.
        ␚␝Section 1.1
        ␞A list of items:␟First item␟Second item␟Third item
        ␚␚␝Subsection 1.1.1
        ␞Deep content, kept exactly:␟␂    indented
          code␃
        ␝Chapter 2
        ␞And so on.
        ␄

  The skipped-depth sentence becomes the error; the header-row sentence
  stays (a header row belongs to its group line, not to its subsections).
- *Canonical Form*: the refusal clause for two GS goes; stripping a note
  between two group lines is now an ordinary canonicalisation. The sentence
  "supersession is content and is kept" goes.
- *Canonical Spans*: a group's span runs to the next group line at its own
  depth or shallower, FS or framing: unchanged in substance, respelled.
- *References*: the depth example and the pattern table row respelled.
- *C0DIFF*: the summary paragraph respelled (no mark).
- *Comments*: "BEL before SUB" examples respelled.
- reference.md: the Document shape example and the pattern sentence
  respelled; the code table row.
- README.md: the SUB line.
- MARK.md (preliminary, 1.x): its marks are written with `old␚␟new`; they
  respell by position (`␞old␟new`, `␞text` a comment) or wait for a mark of
  their own. A status line saying so is enough now.
- `notes/PROPOSAL-SUPERSESSION.md`: a dated closing paragraph pointing here.


## C0DIFF by position

DIFF.md keeps its structure (files of records, cursor, uniqueness to end of
file, atomicity, errors, the refused list) and changes how a record is read.

> A record's units are read in **threes**: an anchor, an old, a new. A
> final anchor may close the record. A record of one unit is an
> **assertion**. So a record has 1, 3, 4, 6, 7, 9, 10, … units; a count of
> 2, 5, 8, … (two more than a multiple of three) is an error.
>
> The **search text** is the anchors and olds in order; the **replacement**
> is the same with each new in place of its old.

    ␞␂Hello ␃␟world␟universe␟!            Hello world! → Hello universe!
    ␞␂class App
      def ␃␟run␟start                       anchor before only (3 units)
    ␞␂x = ␃␟10␟20␟␂ + ␃␟5␟15               two substitutions (6 units)
    ␞␂import os␃␟␟␂
    import sys␃                             insertion: empty old
    ␞␟␂ # TODO␃␟                            deletion: empty anchor, empty new
    ␞def tally(items)                       assertion (1 unit)

The rules that follow are unchanged in meaning: empty search text is an
error (so `␞` and the bare insertion `␞␟␟new`); nothing by nothing
(`a␟␟␟`) is an error; a record with no substitution asserts.

The refused list loses "a chained supersession" and "supersession at any
grain but the unit", and gains "a unit count of 2 mod 3". The sentence
reserving the record grain for a diff against a C0DATA target becomes a
sentence reserving a future shape for it.

### Open points on the diff

- **Threes with an optional closing anchor** (above) against the simpler
  **exactly 1 or 4 units** (anchor, old, new, anchor; one substitution per
  record). Fours are easier to state and to read in a column; threes keep
  the multi-substitution hunk, where an anchor between two substitutions
  ties them into one match window, and they keep every existing vector
  byte-for-byte minus its SUB bytes. Recommendation: threes.
- **Readability.** `␞␂x = ␃␟10␟20␟␂ + ␃␟5␟15` is not self-describing to the
  eye as `10␚␟20` was. The formatter knows the shape from the heading and
  can show `10 → 20`; a diff is written by tools.
- **Could SUB still mark the diff?** Explored for completeness:
  - *SUB before US as a second meaning.* Breaks one meaning per code, which
    is the rule this proposal is restoring; rejected unless "subordinate"
    can honestly cover "the unit after replaces the unit before", which it
    cannot.
  - *Depth in the diff.* A substitution as a subgroup has no sense.
  - *A level per substitution*, `␞␂Hello ␃␟␐␞world␞universe␘␟!`: no new
    code, self-describing, four bytes heavier, and it repurposes the level
    the diff currently refuses. Workable; heavier than position for no gain
    a tool needs.
  Recommendation: no mark. The question can be reopened for C0MARK, where a
  human reads the bytes.


## Vectors

Counts today: decode 97, encode 19, canonical 28, invalid 60, stream 20,
nested 12, diff 41 = 277. Every case below is named; nothing else changes.

**decode**
- Deleted (10): `supersede-unit`, `-deletion`, `-insertion`, `-middle`,
  `-chain`, `-record`, `-keyed-unit`, `-group`, `-file`, `-in-heading`.
- Respelled `␝␝` → `␚␝` (4): `reference-depth`, `gs-depth`,
  `header-not-inherited`, `comment-dead-group-subsections`; their expected
  structures are unchanged.
- Moved to invalid (1): `gs-depth-skipped` (`␝a␚␚␝c␞1`, "depth skipped").
  It is the only case with a null-name *section*; the null-name *files* in
  the reference cases are leading files and stay.
- New (3): `empty-group-then-group` (`␝␝b␞x`: groups `""` and `b`),
  `depth-after-dead-group` (`␝a␇␚␝x␝b␞1`: a dead subgroup does not break
  the file), `dead-subgroup-line` (`␝a␞1␇␚␝s␞2␝b␞3`: `s` and its record
  die).

**encode** (19): the builder writes depth as `gs(name, depth: 2)` or an
explicit `sub` primitive before `gs`; no case changes bytes except any
that spell depth (none today). `reference-plain` unchanged.

**canonical**
- Deleted (2): `supersession-kept`, `supersession-side-spelling`.
- Respelled (1): `note-between-gs` (`␝␇n␝b␞x`) now canonicalises to `␝␝b␞x`,
  two groups, with no refusal.
- New (1): `depth-prefix-kept` (`␚␝s␞1` is canonical as written).

**invalid**
- Deleted (9): `sub-before-value`, `sub-before-text`, `sub-at-eof`,
  `sub-before-bel`, `bel-before-sub`, `sub-record-nothing-before`,
  `sub-group-nothing-before`, `sub-file-nothing-before`,
  `sub-first-keyed-unit`.
- New (9, plus the one moved from decode): `sub-before-us` (`␞a␚␟b`), `sub-before-rs` (`␞a␚␞b`),
  `sub-before-fs` (`␚␜f`), `sub-before-soh` (`␞␚␁k␟v`), `sub-before-value`
  (`␞␚a`), `sub-at-eof` (`␞a␚`), `sub-before-bel` (`␚␇␝g`),
  `sub-layout-gs` (`␚ ␝g`), `depth-skipped` (moved from decode),
  `depth-first-group` (`␚␝g␞1`: the first group of a file at depth two).

**stream** (20), **nested** (12): unchanged; none holds SUB or a GS run.

**diff**
- Respelled by position (38): every case holding SUB, minus the two below;
  `two-substitutions` becomes six units, `deletion` gains its empty leading
  anchor, `insertion` keeps three units, `bare-insertion` becomes `␞␟␟new`
  and stays an error, `empty-substitution` becomes `a␟␟␟` and stays an
  error.
- Deleted (2): `chained-supersession-refused`, `record-grain-refused`.
- New (2): `two-units-refused` (`␞a␟b`), `five-units-refused`
  (`␞a␟b␟c␟d␟e`).

After: decode 89, encode 19, canonical 27, invalid 61, stream 20, nested 12,
diff 41 = 269. `gen.py` regenerates all of it; its applier reads records by
position.


## The ports

Every change is a deletion or a one-line respelling except the diff
reader. Per port (Crystal first, as reference):

- Parser: the `sup` flag and every "nothing to supersede" error, the group
  supersession span removal, the record and keyed-unit paths, the
  `supersessions` grain list; depth becomes "count SUB, expect GS" with the
  skip check; null-name sections go from the model and the harness. The
  body-level state machine keeps BEL, dead depth and dead file as they are.
- Model: `Unit#superseded?`, `Record#units` as-written and the result/
  written distinction go; a record's units are its units. `FileView`,
  `Group`, `Reference#path` unchanged (`path` already linearises depth).
- Builder: `sub` stays the bare primitive and now precedes `gs`; `gs(name,
  depth:)` or equivalent convenience; `supersede(old, new)` removed.
- Pretty: the prefix form `␚␝` is already how an element-level SUB prints;
  the inline `␚␟` form goes.
- Diff: `Pattern` reads units by position; `PatternBuilder#sub(old, new)`
  becomes `substitute(old, new)` writing `old␟new` at the right position
  with the anchor bookkeeping; the grain and chain checks go.
- Stream, Document, Heading, Validator: untouched.
- c0-fmt: follows c0-cr; `c0fmt` gains nothing.

Order: spec and vectors first (this note taken, DESIGN/GRAMMAR/DIFF/
reference/MARK edited, gen.py run), then Crystal, then the six others as
before, Python and Ruby over the C core. None of the 2026-11-13 commits is
pushed, so the port history can be rewritten or stacked, as preferred.


## Not in this proposal

- **Streaming corrections** ("rewind to a match"): SUB followed by an
  element matching an earlier one, nearest in byte order, discards
  everything from the match onward. Complete for the tail of a stream;
  costs unbounded retraction in every reader and a definition of "match" per
  grain. A 1.x profile if a client needs it; nothing in 1.0 forecloses it,
  since SUB before anything but GS is an error.
- **A diff against a C0DATA target** (records addressed by key or id): a
  future shape, as before.
- **Pretty indentation of subgroups** under their parents: parked cosmetic.
