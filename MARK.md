# C0MARK Specification (Proposal)

**Status:** proposal for a 1.x release, not normative, nothing built.
Named 2026-11-08; grown from `notes/SKETCH-SUBSTITUTION.md`. It depends on
the **pair** (`value SUB value`) being a unit kind of the base grammar,
which is decided in direction and not yet in `GRAMMAR.md`. Nothing here is
adopted until it appears in `DESIGN.md` and `GRAMMAR.md`.

C0MARK is editor's marks in a C0DATA document, in the proofreader's
sense: an insertion, a deletion, a substitution, a comment, written where
the change is. A mark is anchored by its **position**; nothing is
searched for. That is the difference from C0DIFF (`DIFF.md`), which finds
its place in another file by matching text. The two share the pair and
nothing else, so each is its own specification.

    ␞␂Hello Mr. ␐␞Davis␚Davidson␇misremembered␘. How are you today?␃

An editor has marked `Davis` to be replaced by `Davidson`, with a note
saying why. The paragraph reads three ways: as the author wrote it, as
the editor would have it, and with the mark showing.


## Marks

A mark is a **record** whose units say what happens at that position. Its
unit kinds are the base grammar's: a pair is a change, a plain or text
unit is a comment, a BEL note is a note.

| Mark | Record | Meaning |
|------|--------|---------|
| substitute | `␞old␚new` | `old` stands here; `new` replaces it |
| insert | `␞␂␃␚new` | nothing stands here; `new` is inserted |
| delete | `␞old␚␂␃` | `old` stands here; it is removed |
| comment | `␞text` | a remark on this position; nothing changes |
| noted | `␞old␚new␇why` | any of the above, with a note |

A pair's sides are values: plain when layout rules allow, text when the
side has edge whitespace, a line break, a tab or a control code. An
inserted `Mr. ` keeps its trailing space only as text: `␞␂␃␚␂Mr. ␃`. The
empty side is spelled `␂␃` and nothing else, so the byte after SUB always
decides the parse.

Richer marks cost nothing new, because a mark is a record and a record
may be keyed: `␞␁old␟Davis␁new␟Davidson␁by␟tom` carries attribution as
content. Two records at one position are two proposed readings. A mark
inside a pair's right side is a reply to a mark.


## Where a mark sits

**On a whole unit.** A pair in a record marks the unit it occupies, and
needs no new grammar at all: `␞old paragraph␚new paragraph`, or in a
keyed record `␞␁title␟Draft␚Final`. The record is the document's own; the
pair is one of its units.

**Inside a text value.** Within the bytes of a value, a mark is an
**island**: a level opened inside the text by DLE, holding the mark
record, closed by CAN, with the text resuming after it.

    substitute    ␂Hello Mr. ␐␞Davis␚Davidson␘. How are you today?␃
    insert        ␂Hello ␐␞␂␃␚␂Mr. ␃␘Davis.␃
    delete        ␂Hello ␐␞␂Mr. ␃␚␂␃␘Davis.␃
    comment       ␂Hello Mr. ␐␞Davis␇check spelling␘.␃

Only text can hold an island, because only text holds control codes as
content. A plain value is marked whole or not at all.

**On a whole record.** Deleting a record, a group line, a header row or a
level already exists in the base format: BEL before its code marks it
dead. C0MARK adds nothing there.


## Grammar

Inside text, DLE today precedes one of seven codes and is an escape;
before anything else it is an error. C0MARK uses that reserved space:

    text   = STX *( tbyte / island ) ETX
    island = DLE lbody CAN

DLE followed by a body opener (FS, GS, RS, SOH, BEL) inside text opens a
level, and `lbody` is a level body exactly as after DLE outside text, so
a record, a header row, a group or a file mean inside an island what they
mean anywhere. DLE before one of the seven stays an escape. DLE before
any other byte stays an error. No eighth escaped code is added.

An island may hold text values, so an unescaped STX can now appear inside
a text value, one level down. A scanner that skipped text flat, from STX
to the first unescaped ETX, must now count DLE-opened levels while inside
text. A document with no islands scans exactly as before.


## Readings

A marked document has three readings, each a C0DATA document:

- **original**: every pair's left side, islands' comments and notes
  dropped. The text as the author wrote it.
- **clean**: every pair's right side, comments and notes dropped. The text
  as the editor would have it.
- **marked**: the document as written, marks showing. The marked copy.

A comment-only island (`␐␞Davis␇check spelling␘`, one plain unit and a
note) contributes its unit to neither reading; the plain unit is the
span the comment is about, and it appears in the text already.

Taking a reading is a tool operation on a parsed document, not a reader
rule: a reader hands back the marked document, and a tool derives the
other two.


## Canonical form and hashing

Marks are content. A pair is hashed as written, both sides; an island is
hashed as the bytes of its level. Two documents that differ only in a
mark are different documents, which is the point: the editor's hand is
part of the record.

**Open:** notes. Under `DESIGN.md`, canonicalisation strips BEL notes and
the content hash does not cover them. Applied to a mark, `␞old␚new␇why`
canonicalises to `␞old␚new`, and the reason for the change is not in the
hash. That follows the base rule and may be right: the pair is the
change, the note is commentary. If a reason must survive canonicalisation
it is written as content, `␁why␟misremembered`. Whether a mark's note
should be treated differently from any other note is undecided; the lean
is no, one rule for BEL everywhere.


## Relationship to C0DATA

The pair is the base grammar's. DLE and CAN keep their meanings, open a
level and close it; C0MARK only admits them inside text. BEL keeps its two
meanings, note and dead. Framing codes (ETB, EOT, SYN, EM) cut through an
island as they cut through text and levels: a document reader that meets
one with an island open rejects the input.

A marked document is a valid document under these rules and no others. A
1.0 reader, which has no island rule, meets `␐␞` inside text and rejects
the document as malformed, which is the correct failure: it does not
misread. Every document valid under 1.0 is valid under C0MARK unchanged,
since no byte sequence that was legal changes meaning. The heading's
`version` key says which rules a document was written under.


## Relationship to C0DIFF

A C0DIFF document acts on another file and anchors by matching. A C0MARK
mark acts on the document it is in and anchors by position. A diff can be
derived from a marked document, since the text around an island is an
exact anchor and the pair is the substitution, and a diff could be
applied to produce a marked document rather than a changed one. Neither
derivation is specified here.


## Cost to implementations

Every port's text scanner gains a branch: on DLE inside text, look at the
next byte; one of the seven is an escape, a body opener enters a level,
anything else is an error. Every port's document model gains text that
holds levels. Pretty printers must lay out an island inside text. Tools
gain the three readings. None of this is needed for C0DIFF or for 1.0.


## Open questions

1. Whether a mark's BEL note is stripped by canonicalisation like any note
   (lean: yes; use a keyed unit for content that must survive).
2. Whether an island may hold more than records: a header row and a table
   inside a paragraph is legal under the grammar and has no editorial
   meaning. Lean: legal, meaning left to the application, as with levels.
3. Layout inside an island in the pretty form: a mark on one line, or the
   usual level layout.
4. Whether the whole-unit pair outside text should be in C0MARK at all or
   simply be the base grammar's pair, with C0MARK covering islands only.
   Lean: C0MARK describes the editorial meaning of both; the grammar of
   the whole-unit pair belongs to `GRAMMAR.md`.


## Conformance

`vectors/mark.json` would hold the cases: marked documents with their
three readings, canonical bytes, and the malformed islands a reader
refuses. It does not exist yet.
