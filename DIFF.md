# C0DIFF Specification

C0DIFF is a control-code markup for atomic multi-file edits, written in
the C0DATA vocabulary. It is a **profile** of C0DATA: an ordinary document
whose heading declares `shape` `diff`. It parses under the base grammar
like any document; this specification gives its records their meaning and
states what a diff may not hold. `DESIGN.md` defines the bytes and
`GRAMMAR.md` the grammar; there is no diff grammar.

Instead of line numbers, which shift, a diff gives **anchored patterns**:
literal text that must match exactly once, with the parts to change
marked inside it by supersession (`old␚␟new`, DESIGN.md, Supersession).

    ␖␁shape␟diff
    ␜greeting.txt
    ␞␂Hello ␃␟world␚␟universe␟!
    ␄

In `greeting.txt`, find `Hello world!`, once, and replace `world` with
`universe`.


## Structure

    ␖␁shape␟diff
    ␜<path>
    ␞<unit>␟<unit>␟…            a record: one anchored pattern
    ␞…
    ␜<path>
    …
    ␄

A diff is files of records. Nothing marks a record as a diff record; the
shape does.

- **FS** begins a file: the name after it is the path, relative to the
  directory the diff is applied in. A path is a name: no edge whitespace or
  control bytes, so files with such names are outside the format. A path
  may not escape that directory. A path is never empty.
- **RS** begins a **record**, one anchored pattern. Records within a file
  are sequential.
- **US** separates the **units** of a pattern. A unit that neither is
  superseded nor supersedes is an **anchor**. A superseded unit with the
  unit that supersedes it (`old␚␟new`) is a **substitution**: `old` is
  what the file holds, `new` what it will hold.
- **SYN**, the heading and **EOT** are as in every C0DATA document. The
  heading SHOULD carry `shape␟diff`; a diff tool accepts an unspecified
  shape and refuses a contradicting one. A generic C0DATA reader given a
  diff reads it as data: records whose units are anchors and
  substitutions, which is what it is.
- **BEL** followed by a value is a note, skipped as everywhere. A note
  may hold a whole hunk, `␇␂␞␂  # TODO␃␚␟␃`, which is how a hunk is kept
  in a diff without applying it.
- **ETB** and its payload are legal between records as everywhere; a diff
  MAY end with a committed block whose payload is a hash, and an applier
  that knows the payload semantics (DESIGN.md, ETB Payload) checks it
  before applying. EOT ends the diff, and bytes after it other than
  layout, SYN or EM are an error.

Every anchor, old and new is a **value** under the ordinary C0DATA rules:
plain, or text (`␂…␃`) where it holds a line break, a tab, edge whitespace
or a control code. Since whitespace next to a code is layout, an anchor
that begins or ends with a space is text. An empty old or new is an empty
unit, nothing between the codes; `␂␃` is never needed.


## Records

A record's **search text** is the concatenation of its anchors and
superseded units, in order. Its **replacement** is the same with each
superseding unit in place of the unit it supersedes.

| Unit | Search contributes | Replacement contributes |
|------|--------------------|-------------------------|
| `␂Hello ␃` (anchor) | `Hello ` | `Hello ` |
| `world␚␟universe` | `world` | `universe` |
| `!` (anchor) | `!` | `!` |

Rules:

- The search text must match **exactly once** in the part of the file
  after the previous record's match (from the start of the file for the
  first record) to the end of the file. Zero matches is an error; two or
  more is an error. Matches are counted at every position, overlapping
  ones included: `aa` occurs twice in `aaa`.
- Records are applied in order; the **cursor** moves to the end of each
  match. Matching is decided on the original file.
- An empty old is an **insertion**: the new is inserted where the old
  would be, between its neighbouring anchors. An insertion is anchored:
  `␞␂Hello ␃␟␚␟universe` inserts after `Hello `.
- An empty new is a **deletion**: `␞␂  # TODO␃␚␟` removes the text.
- A record with no substitution is an **assertion**: its search text must
  be present once; nothing changes, and the cursor moves past it.
- An empty search text is an error, so `␞` and the bare insertion
  `␞␚␟new` are errors. A substitution of nothing by nothing, `␟␚␟`, is an
  error.
- A file with no records asserts only that the file exists; a diff with no
  files is a no-op. The same path twice in one diff is an error.

Patterns anchor on one side, both sides, or carry several substitutions:

    ␞␂class App
      def ␃␟run␚␟start                 anchor before only
    ␞␂Hello ␃␟world␚␟universe␟!         anchors before and after
    ␞␂x = ␃␟10␚␟20␟␂ + ␃␟5␚␟15          two substitutions: "x = 10 + 5" → "x = 20 + 15"
    ␞␂import os␃␟␚␟␂
    import sys␃                         insertion after an anchor
    ␞␂# TODO␃␚␟                         deletion
    ␞def tally(items)                   assertion

Because uniqueness is measured to the end of the file, an assertion that
is removed or fails to match can only widen the window the next record is
searched in: the next record then finds the same single match, or a second
one and the diff fails. It never applies somewhere else.


## What a diff may not hold

The base grammar admits more than a text diff uses. Every slot the diff
does not use is an **error**, so each stays free for a later, additive
meaning. A diff tool refuses a diff holding:

- a keyed unit, a level or a reference anywhere in a record;
- a header row;
- GS;
- a record before the first FS, or an empty path;
- a chained supersession, `a␚␟b␚␟c`: its search text would hold `b`,
  which the file never held;
- supersession at any grain but the unit: `␚␞`, `␚␝`, `␚␜`, `␚␁` (the
  record grain is reserved for a diff against a C0DATA target);
- a dead record or a dead file line. A diff is an instruction, and a hunk
  that reads as live but does not apply is a hazard: one byte, often
  rendered as nothing, would make it inert, and a diff is meant to apply
  entirely or not at all. What is written applies; a hunk is kept without
  applying by writing it inside a note.

Notes are allowed anywhere notes are, and change nothing.


## Replace-all

There is no replace-all mark. "Every `x` becomes `y`" is N anchored
substitutions, and a tool produces them from the target: it finds every
occurrence, takes enough context on each side to make each match unique
after the one before, and writes one record per occurrence. The expanded
diff is its own preview, since each record shows the change in its
context; what applies is explicit and atomic; and the inverse is free,
the same records with each `old␚␟new` turned to `new␚␟old`, which a
careful tool checks against the result before committing so that undo is
guaranteed. A blind replace-all, authored without the target and applied
to files it has never seen, is the one thing a diff cannot say.


## Atomicity

1. **Validate first.** Every record's search text is matched against
   every target file. Any error anywhere stops the whole diff.
2. **Apply only if all pass.** If any file fails validation, nothing is
   written.
3. **Then write.** All replacements are applied and every file is written.

A C0DIFF document is an all-or-nothing transaction across its files. A
tool SHOULD write each file atomically (write to a temporary file, then
rename) so an interruption during step 3 leaves no file half-written.


## Errors

A diff tool refuses, without writing, on:

- a file that does not exist, or a path that leaves the target directory;
- a search text with zero or several matches after the cursor;
- an empty search text, a bare insertion, or `␟␚␟`;
- anything in the list under "What a diff may not hold";
- a heading whose `shape` is present and is not `diff`;
- the same path twice;
- a hash payload that does not match, when the tool checks payloads;
- any byte sequence that is not well-formed C0DATA.

Files are compared and matched as bytes. A tool MAY offer options above
the format (ignore line-ending differences, dry run, verbose match
report, expansion of a replace-all); none of them changes the meaning of
the bytes.


## Relationship to C0DATA

A diff is a C0DATA document and nothing in it means anything it does not
mean elsewhere. FS is a file, RS a record, US a unit, text the mechanism
that protects whitespace, and SUB before US is supersession, the base
grammar's rule that the unit before is replaced by the unit after. The
diff adds only the reading: a record is a pattern, its superseded units
are what the file holds and its superseding units what it will hold.
Supersession is content, so a diff hashes as written: canonicalising a
diff never applies it.

A diff is data about data: a C0DIFF document can be stored, hashed and
transmitted like any other.


## Conformance

`vectors/diff.json` holds golden cases: the files before, the diff bytes,
and the files after or the expected refusal. A diff tool that produces
exactly the expected bytes, and refuses exactly the refused cases, is
conforming.
