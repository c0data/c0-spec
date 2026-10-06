# Proposal: Trailing Blob (EM, End of Medium)

**Status:** Draft — direction agreed in discussion; details open
**Date:** 2026-10-05
**Builds on:** `PROPOSAL-APPENDIX.md` (index group, references, integrity
reasoning) and `PROPOSAL-START.md` (the heading that carries the checks)

## Summary

**EM (0x19)** marks the end of all C0DATA on the medium. Everything after
it, to the end of the container, is one raw blob: no escapes, no framing,
no size needed to find its end, because the end of the container is its
end. Scanning stops at EM and never resumes.

The document's heading (`PROPOSAL-START.md`) carries the blob's size and
hash as checks. Several blobs share the region and are addressed by an
ordinary index group of offsets, as `PROPOSAL-APPENDIX.md` designed.

    ␖blob␟3072000␟blob-hash␟sha256:cd34…
    ␜scene
    ␝props␁name␟image
    ␞lamp␟␅␂␞images␟lamp␃
    ␝images␁name␟offset␟length
    ␞lamp␟0␟3072000
    ␄␙<3072000 raw bytes to the end of the file>

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
| Images in transit, consumed whole | literal region (`PROPOSAL-LITERAL.md`) | inline, about 1.5% overhead, one pass to read |
| A single file holding a document and its images | **trailing blob after EM** | raw bytes, zero-copy, memory-mappable, verifiable |
| A store of hundreds of megabytes | files beside the data, referenced (DESIGN.md sidecar pattern) | everything the filesystem already does |

A literal region can never be zero-copy at image sizes, since a 3 MB
image always contains some of the four escaped byte values, and a reader
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
  may end with one EM and one blob, which the last document owns.

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

### Checks in the heading

The document that owns the blob declares it in its SYN heading, with two
proposed keys:

| Key | Value |
|---|---|
| `blob` | the blob's size in bytes, canonical decimal |
| `blob-hash` | `<algorithm>:<hex>` over the blob's bytes, optional |

A reader compares the size to what the container actually holds past EM.
A shortfall is truncation; a surplus is trailing garbage. A hash mismatch
is corruption. Both are known before any blob byte is trusted. The
heading sits at the front, so the writer must know size and hash before
writing the document; for a file written at rest that is no burden.

The size is a check, not framing. A reader that has no heading still
knows where the blob ends.

### Several blobs: the index group

Carried over from `PROPOSAL-APPENDIX.md`. An ordinary group, any name,
with rows of `name`, `offset`, `length`, and an optional per-blob `hash`.
Offsets are relative to the first byte after EM. Rows may overlap, may
leave gaps for alignment, and may be zero length. Fields elsewhere point
at a blob with an ordinary reference to its row. Resolving a row to bytes
is a library operation.

The index group's name is the application's choice. The heading may
name it (`blob-index`, say) so tools can find it without a convention;
that key is an open question.

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
padding. The spec stays silent beyond that note.

## What it costs

- A fifteenth assigned code, after SYN and BEL. EM was held for this.
- C0DATA files can now carry bytes C0DATA does not read. Tools must say
  so plainly: the head is the document, the blob is cargo.
- Pretty form is lossy for the blob by design.
- Write-once containers.

## Relationship to other proposals

- **Start marker:** the checks live in the SYN heading, which is the
  first reason that heading needed to exist.
- **Literal regions:** complementary, not competing. Literal for transit,
  EM for packaging.
- **Appendix:** superseded in its framing; everything about the index,
  references, hashing, and padding carries over.
- **DESIGN.md** currently reserves EOT followed by ENQ for the old frame.
  If EM is adopted, that reservation can be released.

## Open Questions

1. **Key names** in the heading: `blob`, `blob-hash`, and whether a key
   names the index group.
2. **Ownership in a multi-document container:** the last document, as
   proposed, or the first.
3. **Direct ranges.** The appendix proposal allowed a reference to carry
   an offset and length without a row. Reference paths are themselves
   under review in `PROPOSAL-LITERAL.md`; settle them together.
4. **Alignment:** silent, as proposed, or a recommended page size.
5. **Whether the index group is required** when the heading declares a
   single blob. A one-image container could do without it.

## Feedback

Discussion in progress. Nothing here is adopted until it appears in
DESIGN.md.
