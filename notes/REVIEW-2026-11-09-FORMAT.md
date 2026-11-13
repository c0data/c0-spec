# Independent review of the base format (2026-11-09)

A cold read of DESIGN.md, GRAMMAR.md, reference.md and the vectors by a
reviewer with no prior knowledge of the project, briefed to look for
consistency, ambiguity, over-engineering, principle violations and
unvectored rules. Citations were spot-checked against the files the same
day (findings 1, 2, 3, 8, 10 confirmed by reading). Line numbers are as of
commit 434c06c. Nothing here is decided; it is input to the pre-1.0 pass.

## Findings, most important first

1. **The grammar rejects a dead record after a live record.** `item =
   record / note / commit` and `litem = record / note` admit
   `dead-record` only in `pre`/`lpre`, i.e. before the first live item.
   Decode vector `comment-record` (`␝g␞a␇␞b␞c`) and DESIGN's own example
   `␇␞port␟5432` have no derivation. Fix: `item = record / dead-record /
   note / commit`, `litem = record / dead-record / note`; decide whether
   `dead-header` is also an item (see 5). *Confirmed: grammar defect;
   prose and ports are right.*

2. **Canonicalisation can change GS depth.** `␝␇n␝b` is an empty-named
   depth-1 group, a note, then depth-1 group `b`; strip the note and the
   bytes `␝␝b` read as depth 2. Same with a dead record or a commit between
   two GS. DESIGN's "an empty-named group cannot be followed directly by
   another group" is true only of canonical bytes. No rule for an encoder
   handed groups `["", "b"]`. Fix (smallest): a canonicaliser or encoder
   that would bring two GS together refuses, like the glyph-collision rule;
   add vectors. Alternative: define depth over the stream with
   notes/dead/commits removed (costs the one-code lookahead).

3. **A record holding only notes (`␞␇n`) derives as both keyed and
   positional**: empty map or one empty field. Changes the JSON mapping
   inside a level. Fix: `keyed = *note keyed-unit *( keyed-unit / note )`;
   at least one SOH unit (live or dead) makes a record keyed. Add a vector.

4. **Reference resolution unspecified across FS files and for duplicate
   names.** A path has no file segment; nothing forbids two groups with one
   name. Blob table says last-wins; groups and ids say nothing. Fix: one
   sentence for scope (suggest: the file containing the reference) and one
   for duplicates (error when asked to resolve); note that the format does
   not check group-name uniqueness.

5. **Header row after a dead group or file line**: grammar admits
   `␝g1␞1␇␝g2␁␞x␞2`, prose makes it an error (records after a dead group
   line belong to g1, which has a record). A dead header row mid-group is
   an error only by inference. Fix: say both; one invalid vector each.

6. **Header inheritance into GS-repeated subsections undecided**, and the
   reported shape of a skipped depth's implied parent undefined. Fix: "a
   header row applies to the group line it follows, not to its
   subsections"; implied parent reported as name `""`, no records. Vectors.

7. **Terms with shifting meaning**: *unit* (field / keyed unit / canonical
   hash span), *level* (DLE level / warning severity / GS depth), *text*
   (STX…ETX / "plain or text" in the BEL and payload sentences), *framing*
   (cut-through codes / also comments in the hash section), *name*
   (identifier / a record's first field, which may be text). Suggest
   "spans" for hash units, "depth" for GS, "severity" for warnings, "id"
   for the first-field convention; and "one value, possibly empty" for a
   unit (DESIGN says exactly one, GRAMMAR at most one).

8. **DESIGN's list of what may be dead omits a keyed unit**, which the
   grammar, a vector and reference.md all include. *Confirmed.*

9. **reference.md behind DESIGN.md**: "Compact Form (Canonical)" heading
   conflates the two; Diff row code lists differ; FS described as "a
   database, a file, a document"; DLE "must be followed by a code" vs the
   closed list; BEL error list omits ENQ and BEL; "values are plain text"
   vs byte-transparent.

10. **`shape` hints that "nothing may act on"** (`tabular`, `document`,
    `key-value`) contradict "the heading holds reader instructions only".
    Suggest cutting them; a converter can be told its target on the command
    line. *Confirmed as written.*

11. **Stream damage confinement is narrower than motivated**: only an ETB
    cutting open text/level is "damaged"; any other malformation in a
    committed block is a hard error for the whole read. Suggest: in stream
    mode any error inside a committed block marks that block damaged and
    the reader resumes after the next commit.

12. **Lookahead note overstates**: a dead header row is BEL SOH RS (two
    codes); GS depth needs one code of lookbehind or carried state. Say
    "two codes of lookahead and one of lookbehind, layout skipped".

13. **Notes inside a header row**: prose allows notes anywhere, grammar's
    `header-row` has no `*note`. Add it or say header rows admit none.

14. **Principles to own their exceptions**: DLE has two jobs by position
    (recurse / escape); BEL dead is an in-line annotation. Add a sentence
    to Principles, or narrow "nothing is annotated in line" to size, type
    and hash.

15. **Smaller edges**: canonical span of a depth-2 group; duplicate heading
    keys (which `shape` applies); ETB payload followed by text or US; SYN
    inside a committed block; blob rows written as keyed records.

## What is fine

Text and the seven escapes, cut-through and the parity argument; layout
rules; positional records and arity by separators; the commit rule, torn
tail, writer repair and payload span; EM and the blob table; code-at-end
and code-in-unexpected-position cases; keyed records and the header-row
position rule (apart from 1, 3, 13). All consistent across DESIGN,
GRAMMAR, reference and vectors.

## Rules no vector exercises (highest value first)

`␐␁k␟v␘` error (the reserved type-tag slot); `␝ ␝` depth two with layout,
and the GS-run cases of finding 2; dead record after a live record inside
a level, dead header mid-group, header after a dead group line; `␞␇n` and
`␐␞␇n␘`; SYN/EOT inside open text or level for a document reader, and
`␐␐ ␐␂ ␐␅ ␐␗` outside text; reference edges (four segments, empty segment,
`␅␂␃`, one-segment text, reference as keyed value and as heading value,
`␅ tags`); keyed record under a header row, empty key, empty FS name,
interior spaces in labels; heading edges (`␖x`, `␖␁k` at end, `␖␖`, EM
after SYN, duplicate key, dead key in decode); `␄␄`, two documents with
layout; stream: dead element in tail, SYN tearing a tail, cutting ETB,
EOT then bytes; encode: two files, GS depth, spaces-only value, refusals
(control byte or edge space in a name, `["", "b"]` groups), blob level,
stream blocks; canonical: dead element, layout inside level, ETB payload;
blob table validation.

## Taste (not defects)

A dead group line killing only the label is surprising and is the root
of 2 and 5. ENQ cannot reach a keyed record's field. Names can never be
text, so an FS label cannot be a path with a leading space (matters for
the diff). Record span excludes RS, group span includes GS. nested.json
prescribes an API. "Open Questions: none" is stronger than the document
supports.

## Verdict (reviewer's)

The byte-level core (text, escapes, layout, separators, commits, EM) is
consistent, well-motivated and well-vectored and would survive a freeze.
Not ready because the grammar rejects its own dead-record example,
canonicalisation can change GS depth, and three structural questions
(notes-only record, reference scope, header inheritance) each have two
defensible readings. Smallest fix: `item`/`litem`/`keyed` in GRAMMAR.md;
one GS-run rule; one sentence each for reference scope, header
inheritance, dead-element position; sync reference.md; the dozen vectors
in the first five groups above.
