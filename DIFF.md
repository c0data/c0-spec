# C0-DIFF Specification (Draft)

C0-DIFF is a control-code markup for atomic multi-file edits, written in
the C0DATA vocabulary. It is a **profile** of C0DATA: a document whose
heading declares `shape` `diff`, read by its own rules. This document is
normative for those rules; `DESIGN.md` defines the bytes and `GRAMMAR.md`
the grammar (`diff-body`).

Instead of line numbers, which shift, a diff gives **anchored patterns**:
literal text that must match exactly once, with the parts to change
marked inside it.

    ␖␁shape␟diff
    ␜greeting.txt
    ␝␂Hello ␃␟world␚universe␟!
    ␄

In `greeting.txt`, find `Hello world!`, once, and replace `world` with
`universe`.


## Structure

    ␖␁shape␟diff
    ␜<path>
    ␝<unit>␟<unit>␟…            a section: one anchored pattern
    ␞<old>␚<new>                 replace-all within the section's scope
    ␜<path>
    …
    ␄

- **FS** begins a file: the text after it is the path, relative to the
  directory the diff is applied in. A path is a name: no edge whitespace or
  control bytes, so files with such names are outside the format. A path
  may not escape that directory.
- **GS** begins a **section**, one anchored pattern. Sections within a
  file are sequential.
- **US** separates the **units** of a pattern.
- **SUB (0x1A)** inside a unit separates old from new: the unit is a
  **substitution**. A unit without SUB is an **anchor**.
- **RS** begins a **replace-all**: old, SUB, new, applied to every
  occurrence within the scope of the section it follows.
- **SYN**, the heading and **EOT** are as in every C0DATA document. The
  heading SHOULD carry `shape␟diff`; a diff tool accepts an unspecified
  shape and refuses a contradicting one. A generic C0DATA reader given a
  diff with no shape may misread it as data (a diff of anchors alone is
  also a valid data body) or reject it at the first SUB.
- **BEL** is as everywhere: a note ends at the next code and is never a
  unit, and a BEL before GS, RS or FS kills that line only. A dead GS kills
  its pattern; RS lines after it attach to the previous live section (or
  the file's leading scope). A dead FS kills its path line; lines after it
  belong to the previous file.
- **ETB** and its payload are tolerated between lines as everywhere; EOT
  ends the diff, and bytes after it other than layout, SYN or EM are an
  error.
- **SOH**, **DLE** and **ENQ** have no meaning in a diff body and are
  errors there. SUB has no meaning outside a diff and is an error
  elsewhere.

Every anchor, old and new is a **value** under the ordinary C0DATA rules:
plain, or text (`␂…␃`) where it holds a line break, a tab, edge whitespace
or a control code. Since whitespace next to a code is layout, an anchor
that begins or ends with a space is text.


## Sections

A section's **search text** is the concatenation of its units' anchors
and old parts, in order. Its **replacement** is the same with each old
part replaced by its new part.

| Unit | Search contributes | Replacement contributes |
|------|--------------------|-------------------------|
| `␂Hello ␃` (anchor) | `Hello ` | `Hello ` |
| `world␚universe` | `world` | `universe` |
| `!` (anchor) | `!` | `!` |

Rules:

- The search text must match **exactly once** in the part of the file
  after the previous section's match (from the start of the file for the
  first section). Zero matches is an error; two or more is an error.
  Matches are counted at every position, overlapping ones included: `aa`
  occurs twice in `aaa`.
- Sections are applied in order; the **cursor** moves to the end of each
  match.
- An empty old part is an **insertion**: the new part is inserted where
  the old would be, between its neighbouring anchors.
- An empty new part is a **deletion**.
- A section with no substitution is an **assertion**: the anchor must be
  present once; nothing changes, and the cursor moves past it.
- An empty search text is an error. An empty unit contributes nothing.
- A file with no sections asserts only that the file exists; a diff with no
  files is a no-op. The same path twice in one diff is an error.

Patterns anchor on one side, both sides, or carry several substitutions:

    ␝␂class App
      def ␃␟run␚start                 anchor before only
    ␝␂Hello ␃␟world␚universe␟!         anchors before and after
    ␝␂x = ␃␟10␚20␟␂ + ␃␟5␚15           two substitutions: "x = 10 + 5" → "x = 20 + 15"
    ␝␂import os␃␟␚␂
    import sys␃                        insertion after an anchor
    ␝␂# TODO␃␚                          deletion


## Replace-all (RS)

An RS line after a section replaces **every** occurrence of its old part
with its new part within that section's **scope**. The scope runs from the
end of the section's match to the start of the next section's match in
the same file, or to the end of the file for the last section.

    ␖␁shape␟diff
    ␜tally.rb
    ␝def tally(items)
    ␞count␚total
    ␝end
    ␄

Every `count` between `def tally(items)` and the following `end` becomes
`total`. Rules:

- The old part is non-empty. An empty old part is an error.
- Occurrences are found left to right and do not overlap.
- Zero occurrences is an error, like an anchor that does not match.
- Several RS lines after one section apply in order, each to the scope as
  left by the one before.
- An RS line before any GS in a file has as its scope the start of the file
  up to the first section's match (the whole file when there is none).
- A replace-all does not move the cursor; the next section is searched
  from the end of its own section's match, in the text as it was before
  the replace-all. Section matching is decided on the original file.

Each occurrence is a record, which is what RS has always meant.


## Atomicity

1. **Validate first.** Every section's search text is matched and every
   replace-all's occurrences are counted against every target file.
   Any error anywhere stops the whole diff.
2. **Apply only if all pass.** If any file fails validation, nothing is
   written.
3. **Then write.** All replacements are applied and every file is written.

A C0-DIFF document is an all-or-nothing transaction across its files. A
tool SHOULD write each file atomically (write to a temporary file, then
rename) so an interruption during step 3 leaves no file half-written.


## Errors

A diff tool refuses, without writing, on:

- a file that does not exist, or a path that leaves the target directory;
- a search text with zero or several matches after the cursor;
- a replace-all with zero occurrences, or an empty old part;
- an empty search text;
- a heading whose `shape` is present and is not `diff`;
- the same path twice;
- any byte sequence outside the `diff-body` grammar.

Files are compared and matched as bytes. A tool MAY offer options above
the format (ignore line-ending differences, dry run, verbose match
report); none of them changes the meaning of the bytes.


## Relationship to C0DATA

FS and GS keep their structural meanings (file boundary, section). US
keeps its unit role. Text is the same mechanism and the only one that
protects whitespace. RS keeps its meaning, one record per occurrence. SUB
takes the diff-specific role that matches its C0 name, substitution.
Framing (SYN, EOT, ETB, EM) applies as everywhere; a diff is normally one
document and uses none but SYN and EOT.

A diff is data about data: a C0-DIFF document is itself a C0DATA
document, so it can be stored, hashed and transmitted like any other.


## Conformance

`vectors/diff.json` holds golden cases: the files before, the diff bytes,
and the files after or the expected refusal. A diff tool that produces
exactly the expected bytes, and refuses exactly the refused cases, is
conforming.
