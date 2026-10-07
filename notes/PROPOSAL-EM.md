# Proposal: Trailing Blob (EM, End of Medium)

**Status:** Draft — settled in discussion — direction agreed in discussion; details open
**Date:** 2026-10-05
**Builds on:** `PROPOSAL-APPENDIX.md` (index group, references, integrity
reasoning) and `PROPOSAL-START.md` (the heading that carries the checks)

## Summary

**EM (0x19)** marks the end of all C0DATA on the medium. Everything after
it, to the end of the container, is one raw blob: no escapes, no framing,
no size needed to find its end, because the end of the container is its
end. Scanning stops at EM and never resumes.

The document's heading (`PROPOSAL-START.md`) declares the blob under one
key, `blob`, whose value is a table with one row per blob: name, offset,
length, and an optional hash. That table is the whole index; there is no
index group in the body.

    ␖␁blob␟␏␁name␟offset␟length␟hash
      ␞lamp␟0␟3072000␟sha256:cd34…
      ␞desk␟3072000␟1900000␟sha256:ef56…␘
    ␜scene
    ␝props␁name␟image
    ␞lamp␟lamp
    ␄␙<4972000 raw bytes to the end of the file>

In ASCII, EM is "end of medium": the end of the used or wanted portion
of data on a tape or other medium. That is exactly its job here. It
completes a ladder: ETB ends a block, EOT ends a document, EM ends the
C0DATA.

## Motivation

The first serious prospective client moves images: PNG and WebP files
averaging about 3 MB, the largest 17 MB, hundreds at a time, today as
base64 at a third of overhead plus an encoding pass. Three mechanisms
serve three needs, and this proposal is the middle one:

| Need | Mechanism | What it gives |
|---|---|---|
| Images in transit, consumed whole | text (`PROPOSAL-LITERAL.md`) | inline, about 2.3% overhead, one pass to read |
| A single file holding a document and its images | **trailing blob after EM** | raw bytes, zero-copy, memory-mappable, verifiable |
| A store of hundreds of megabytes | files beside the data, referenced (DESIGN.md sidecar pattern) | everything the filesystem already does |

Text can never be zero-copy at image sizes, since a 3 MB image always
contains some of the six escaped byte values, and a reader
must scan it to find its end. The trailing blob has neither cost. The
price is that it is out of line and write-once.

### Why EM, and not the earlier frame

`PROPOSAL-APPENDIX.md` framed the blob with EOT followed by ENQ and a
declared size, and allowed documents to chain, blob after blob. Its
review found the cost: a reader entering a chained container at an
arbitrary byte cannot tell whether it is inside a blob, which breaks the
bounded-lookbehind principle at container scope. The stricter option
noted then, one blob per container at the very end, removes the problem
entirely, and EM is the code whose meaning is that option.

- **No size is needed to frame it.** The blob runs to the end.
- **Nothing structured follows it,** so there is nothing to lose. Every
  byte before EM is scannable as today; every byte after it is the blob.
- **Chaining is simply not offered.** A container of several documents
  may end with one EM and one raw region, declared in the first
  document's heading and sliced into named blobs by its table.

The appendix proposal was deferred because it made C0DATA a container
for bytes it does not interpret, and because the sidecar pattern served
the need. Both remain true. What changed is a client whose data is
mostly bytes C0DATA does not interpret, and a cleaner frame.

## Proposal

### EM

EM is assigned. It appears at most once in a container, after the final
document, and it ends that document the way the end of input does. EOT
is optional at the end of a document already, so `…␄␙` and `…␙` are
both legal and neither is preferred (decided 2026-10-06). Nothing after
EM is C0DATA.

### The blob

Every byte after EM to the end of the container. Raw: no escapes, no
framing, no layout, no interpretation. A container with EM and nothing
after it has an empty blob.

### The declaration in the heading

The **first document's heading** declares the blobs, with one key:

| Key | Value |
|---|---|
| `blob` | a nested table, keys hoisted: `name`, `offset`, `length`, optional `hash` |

Offsets are relative to the first byte after EM. Rows may overlap, may
leave gaps for alignment, and may be zero length. A container with one
image is one row.

Blobs belong to the container, not to a document: any document in it
may reference any blob by name, and a reference is data, resolved by
the library. So the table must be known before any document is read,
which is the format's declare-before-use rule, and the first heading is
also the one place found without a scan. A `blob` key in any later
heading is a loud warning. For a container of several documents the
recommended form is a heading-only first document, a container header:

    ␖␁blob␟␏␁name␟offset␟length␟hash
      ␞lamp␟0␟3072000␟sha256:cd34…
      ␞desk␟3072000␟1900000␟sha256:ef56…␘␄
    ␖␜catalogue␝items␁name␟photo␞Lamp␟lamp␞Desk␟desk␄
    ␖␁shape␟stream␞…␗
    ␙…raw…

It keeps container metadata apart from document metadata and leaves the
first real document extractable unchanged, at the cost of a few bytes
and an empty-bodied document at the front. It is a style, not a
mechanism: a single-document file writes the table into its own heading,
and a reader applies the same rule to both. Per-document declarations
were considered and rejected: a document split out of a container loses
the raw tail regardless, so the library rewrites blobs and offsets
either way, and per-document rows only add duplicates and conflicts.

The checks a reader makes before trusting any blob byte: the container
must hold at least the largest offset plus length past EM, or the blob
is truncated; each row's hash, if present, must match its bytes. The
heading sits at the front, so the writer must know the sizes and hashes
before writing the document; for a file written at rest that is no
burden.

Declaring the blob up front is what makes its absence detectable: a
container cut off before EM still promised a blob in its heading. Facts
carried on EM itself were considered and rejected for that reason, and
because they need a terminator ahead of raw bytes.

An earlier draft had three keys (`blob` size, `blob-hash`, `blob-index`)
plus an index group in the body. The group's rows and the keys described
the same thing in two shapes, so the group moved into the heading and
the keys collapsed into it.

### Naming a blob from the data

A field that refers to a blob holds its name, `lamp`. The application
asks the library for the blob by name, as it would for any value it
understands. No reference path reaches into the heading, and nothing is
named by convention.

### Identity

Document identity is unchanged: the hash of the canonical head, which
contains the index rows and any per-blob hashes, so it commits to the
blob bytes transitively. EM and the blob are outside the canonical unit,
like other framing.

### Mutation

Write-once. Adding a blob means rewriting the container, since the head
grows and the region shifts. Growth is a new container. This matches how
content-addressed stores already work.

### Streams

EM has no meaning in an ETB stream log, which has no end to put it at.

### Scanning

Unchanged before EM. A reader that lands after EM is in the blob and
cannot know it from the bytes; but there is no structure after EM to
find, so the only consequence is that such a reader reports nothing.
Twenty of the thirty-two low byte values are rejected raw, so random
binary trips a tokenizer within a few dozen bytes in any case.

### Pretty form

After `␙`, one summary line: the size, the hash if any, and the index
row count. Pretty-to-compact needs the blob supplied separately; `c0fmt`
gains an option to attach one and an option to strip one.

### Alignment

Explicit offsets make alignment the producer's choice. A producer that
wants page-aligned images pads the region; the index points past the
padding, and the bytes in the gaps are undeclared. The spec stays silent
beyond that note; a library may offer alignment as a writer option. A
recommended page size would be right for one platform and decade and
wrong for the next.

## What it costs

- A fifteenth assigned code, after SYN and BEL. EM was held for this.
- C0DATA files can now carry bytes C0DATA does not read. Tools must say
  so plainly: the head is the document, the blob is cargo.
- Pretty form is lossy for the blob by design.
- Write-once containers.

## Relationship to other proposals

- **Start marker:** the declaration lives in the SYN heading, which is
  the first reason that heading needed to exist.
- **Text:** complementary, not competing. Text for transit,
  EM for packaging.
- **Appendix:** superseded in its framing; its index columns survive as
  the keys of the `blob` table, and its reasoning on hashing and padding
  carries over.
- **DESIGN.md** currently reserves EOT followed by ENQ for the old frame.
  If EM is adopted, that reservation can be released.

## Decided (2026-10-06)

- The `blob` table lives in the first document's heading; a heading-only
  first document is the recommended form for a multi-document container;
  any document may reference any blob by name; `blob` in a later heading
  is a loud warning.
- Alignment is the writer's choice; the spec is silent.

No open questions.

## Feedback

Discussion in progress. Nothing here is adopted until it appears in
DESIGN.md.
