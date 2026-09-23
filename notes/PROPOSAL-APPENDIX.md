# Proposal: Binary Appendix

**Status:** Deferred — designed in full, not adopted
**Date:** 2026-09-23

## Why deferred

The design below is sound, but adopting it makes C0DATA a container for
bytes it does not interpret, which changes the nature of the format, and
it touches pretty form, diff, converters, and the API of every
implementation. C0DATA's principle that the application is the authority
on what values mean already covers "this value names some bytes"; where
the bytes live is an application or container concern. The **blob sidecar
pattern** in DESIGN.md (blobs as files or content-addressed objects,
described by ordinary rows and referenced with ordinary references) serves
the need today, with per-blob memory mapping, caching, and deduplication
that a single appendix cannot offer. Its column convention is chosen so
that a sidecar row becomes an appendix row by replacing `location` with
`offset`.

Deferral costs nothing: everything here sits after EOT, and DESIGN.md
reserves `EOT` followed by `ENQ` so the frame slot stays free. If a
consumer with genuine single-file needs appears, this document is the
design to adopt.

## Summary

A C0DATA document may be followed by a single region of raw binary bytes,
the **appendix**. The document addresses byte ranges of the appendix by
offset and length, through an ordinary group that serves as an index and
through ordinary references into that group. The appendix begins with a
frame that reuses the existing reference syntax after EOT, is delimited
by a declared size, and is committed with an ordinary ETB marker.

No new control codes. No reserved names. Every existing reader stops at
EOT and sees a valid document.

    [GS]appendix[SOH]name[US]offset[US]length[US]hash
    [RS]image-001[US]0[US]4096[US]sha256:ab12…
    [RS]audio[US]4096[US]18000[US]sha256:cd34…
    [GS]users[SOH]name[US]avatar
    [RS]Alice[US][ENQ][STX]appendix[US]image-001[ETX]
    [EOT][ENQ][STX]appendix[US]22096[ETX]<22096 raw bytes>[ETB]sha256:ef56…

In pretty form:

    ␝appendix␁name␟offset␟length␟hash
    ␞image-001␟0␟4096␟sha256:ab12…
    ␞audio␟4096␟18000␟sha256:cd34…
    ␝users␁name␟avatar
    ␞Alice␟␅␂appendix␟image-001␃
    ␄␅␂appendix␟22096␃<22096 raw bytes>␗sha256:ef56…

## Motivation

C0DATA values are text. Binary values ride today in one of two in-spec
forms: as text (hex, base64) or as DLE-escaped raw bytes, which costs one
extra byte per control byte (about 12.5% on random data, nothing on text)
and requires the bytes to be scanned and, when escaped, copied on read.
That is the right trade for small values. It is the wrong trade for an
image, an audio clip, a tensor, or a compiled artifact, where the consumer
wants the bytes raw, unscanned, and sliced without copying, ideally
memory-mapped and aligned.

DESIGN.md rejects in-line binary regions (see "Binary Data (SO/SI) —
REJECTED") because they break the bounded-lookbehind scan invariant, and
notes that the one shape that could work is a blob appendix after EOT.
This proposal is that shape, worked out.

The closest existing analogues are glTF's binary container and the
safetensors format: a small structured header addressing one raw buffer by
offset and length. What C0 adds is that the header is itself a scannable,
canonical, hashable, diffable structure, and blob references are the
format's ordinary references rather than a convention.

## Design Principles

1. **No new control codes.** Every marker is an existing code in a
   position that is well-formed but meaningless today.
2. **No reserved names.** The document says which group indexes the
   blob; the spec recommends a default name and reserves nothing.
3. **Invisible to existing readers.** Everything new sits after EOT.
4. **The structured part is unchanged.** Scanning, canonical form,
   hashing, diffing, and references work exactly as they do today on the
   part of the document before EOT.
5. **Raw bytes stay raw.** No transform on the blob. Zero-copy slicing
   and alignment are possible because offsets are explicit.

## Proposal

### The frame

EOT then ENQ is well-formed today (ENQ is an assigned code) and has no
meaning (ENQ is defined only as a field value). It is therefore free to
define. After EOT, a path-shaped reference names the index group and
declares the appendix size:

    [EOT][ENQ][STX]<index-group>[US]<size>[ETX]

Exactly `<size>` raw bytes follow the ETX. A reader positioned at EOT
peeks one byte: ENQ means an appendix follows; anything else means what
it means today (a following document, or end of input).

The first segment names the group, in this document, whose rows describe
the blob. The group must exist. It may be empty. `appendix` is the
recommended name; `#` is a reasonable short alternative. Neither is
reserved.

### The index group

An ordinary group. Its recommended columns:

| column   | meaning                                                   |
|----------|-----------------------------------------------------------|
| `name`   | record id used by references                              |
| `offset` | first byte of the range, relative to the first byte after the frame's ETX |
| `length` | byte count                                                |
| `hash`   | optional per-blob digest, `<alg>:<hex>` (same form as ETB payloads) |

Rows may overlap (read-only views of one region), may leave gaps
(padding, alignment), and may have zero length. The frame size MUST be at
least the largest `offset + length`. Padding after the last row is legal.

Offsets are relative to the appendix, not the file, so the document can be
rewritten without invalidating a single offset.

### References

References into the index group have ordinary path semantics and nothing
about them is special-cased:

    [ENQ]appendix                             the group (the table itself)
    [ENQ][STX]appendix[US]image-001[ETX]      a row
    [ENQ][STX]appendix[US]image-001[US]hash[ETX]   one field of a row

Turning a row into bytes is a library operation ("give me the blob this
row describes"), not a reference form. This keeps the core rule that
references are never resolved by the scanner.

A range may also be addressed directly, without a row, by giving a nested
scope as the second segment:

    [ENQ][STX]appendix[US][STX]0[US]4096[ETX][ETX]

This is unambiguous because path segments are names, and names may not
contain control bytes (a guard every implementation enforces), so a
segment that is itself an STX scope cannot occur today. Splitting a path
on US must skip nested scopes, as the record field scanner already does.
Direct ranges carry no per-blob digest.

### Integrity

Two layers, deliberately distinct:

- **Per-blob digests** live in the index rows. They are inside the
  canonical unit, so the document's hash transitively commits to the bytes
  of every blob that has one.
- **Whole-appendix integrity** is an ordinary ETB commit after the bytes,
  with the digest as its optional payload, using the existing ETB grammar
  unchanged:

      <size bytes>[ETB]sha256:ef56…

  A reader that knows the size lands exactly on the byte after the blob.
  ETB there commits the appendix; its payload runs to the next control
  code. Anything else means the next document starts there, or input ends.
  An appendix with no ETB is uncommitted, the same word stream mode uses.

Putting the digest after the bytes lets a producer learn a file's size
from a stat call, write the frame, copy while hashing, and emit the digest
last. It never needs the blob in memory or a second pass.

The recommended full integrity layout treats the head and the appendix as
two committed blocks:

    <head>[ETB]sha256:…[EOT][ENQ][STX]appendix[US]<size>[ETX]<bytes>[ETB]sha256:…

### Numbers

C0DATA has no number typing; whether a value is numeric is the
application's business. The exception is values the spec itself reads.
The ETB payload is already one (text hex with an algorithm tag). Offsets,
lengths, and the frame size are the second: **decimal ASCII digits, no
sign, no leading zeros, no separators.** No leading zeros because the
index sits inside the canonical unit and canonical form needs one encoding
per value.

### Identity

Document identity is unchanged: the hash of the canonical unit, byte zero
to EOT. That unit contains the index rows and their digests. The ETB
digest after the bytes is transport integrity, not identity.

### Mutation

Documents with an appendix are write-once. Rewriting the head changes its
length and physically shifts the tail on disk, even though offsets remain
valid. Growth is done by appending a new document (see Sequences), not by
editing. A compaction tool may rebuild a document without gaps.

### Sequences

Because the size is declared, a container may hold several documents,
each with its own appendix:

    <doc>[EOT]<frame><bytes>[ETB]…<doc>[EOT]<frame><bytes>[ETB]…

A reader skips each blob in one jump. Indexing such a container costs
time proportional to the heads and the number of documents, never the
blob bytes. See "What this costs" for the property this gives up.

The appendix is a document-mode feature. It has no meaning inside an ETB
stream log (stream mode), which is an append-only sequence of committed
records with no tail.

### Blob-first input (reserved)

An input beginning `[EOT][ENQ]…` is an empty document followed by a
frame. A binding rule could make this legal: a frame with no preceding
document binds forward to the next document, which must contain the named
group. This would allow blob-first streaming with per-blob digests
computed in one pass. It is small, but it makes every reader carry a
deferred-binding path for a producer that does not yet exist. **This
version treats it as an error** and notes the binding rule as the intended
extension.

## What this preserves, and what it costs

DESIGN.md's design principle: structure is determinable with bounded
lookbehind; chunked scanning, SIMD acceleration, and mid-buffer
resynchronization depend on it.

**Within a document the principle holds exactly.** The head contains no
binary. A forward scanner stops at EOT and never enters the tail. SIMD
masks, chunked scanning, and resync inside a head work as today.
Sequential readers, including SIMD ones, lose nothing anywhere: they always
know where they are.

**Between documents it does not.** In a container of several documents
with appendices, a block taken at an arbitrary offset may lie inside any
blob, and knowing which requires having followed every frame before it.
That is the same sequential dependency in-line length prefixes create,
now at container scope rather than document scope. What is lost is
scanning a chained container from an arbitrary offset with no prior
knowledge: zero-knowledge parallel byte-splitting, and corruption salvage
inside a chain. Both are niche today (no implementation has a SIMD
scanner, a parallel splitter, or a resync routine) and both are partly
mitigated by a head-only pre-pass. Landing in a blob is detected quickly
in practice, since twenty of the thirty-two low byte values are illegal
raw, but a blob that is itself text can fool that heuristic.

Adopting this proposal therefore means restating the principle honestly:
it is a guarantee about documents. A container of blob-carrying documents
is read sequentially or indexed by a pre-pass, not scanned from an
arbitrary offset.

A stricter rule keeps a clean container story at the cost of sequences:
**at most one appendix per container, at the very end.** Then a scanner
at any offset either sees valid structure or detects binary and knows it
is at the end. This is a legitimate alternative and is recorded under
Open Questions.

The other cost is locality. An in-line escaped value keeps a record
self-contained; an appendix blob does not, so extracting a record with
its image means carrying a slice of the tail. This is why both forms
should exist: small binary stays in-line and local, large binary goes to
the tail and is raw.

The EOT wart: EOT is no longer quite "end of transmission". It never
meant end of everything (a stream has many EOTs, one per document); the
appendix is an attachment to the document that just ended. The wart is the
price of placing the blob after EOT, which is what makes the feature
invisible to every existing reader. It cannot be removed, only reframed.

## Alternatives considered

**In-line binary regions (SO/SI with a length prefix).** Rejected in
DESIGN.md and the reasoning stands: every region, anywhere in the
document, requires unbounded context to classify a byte, defeats the mask
approach to scanning, and turns a corrupted length into a cascade.

**Prependix (blob first, document after).** Wins single-pass per-blob
digests, ZIP-style append growth, and alignment from byte zero. Loses the
decisive properties: metadata-first reading over pipes, partial downloads,
and range requests; backward compatibility (every existing reader would
fail on byte one); and a canonical unit at a fixed offset. Rejected.

**A dedicated frame code (SO/SI after EOT).** SO and SI, "shift out" and
"shift in", mean exactly "the following bytes are not in the current
character set". `[EOT][SO]<name>[US]<size>…<bytes>[SI][ETB]…` reads
without explanation, and the earlier rejection of SO/SI stands for
in-line use. It costs assigning two codes, which touches every tokenizer,
the assigned table, the invalid vectors, the pretty glyphs, and the editor
grammar. Against it: ENQ already carries three meanings (simple reference,
path reference, frame), coherent as "data defined elsewhere" but a
stretch for the frame. **This is the one open fork with real weight.**

**A reserved index-group name.** Avoided: the frame names the group, so
nothing is reserved and the recommended name is only a default.

**Virtual group with in-reference offsets only, no table.** Loses names,
per-blob digests, and readability. The nested-scope range form gives the
same capability alongside the table instead of instead of it.

**SYN-encoded blobs.** SYN (0x16, "synchronous idle") was the byte
telecom equipment inserted so a receiver joining mid-stream could find
sync. Escape the blob's DLE and SYN bytes, insert a raw SYN every 63
bytes, and every 64-byte window of a blob contains a raw SYN while no head
ever does. Blob detection becomes a guarantee, blob ends are findable,
and the scan principle holds everywhere with the bound raised to 64
bytes, including in chained containers. Cost: about 2.5% size and, more
importantly, the bytes are no longer raw, so zero-copy slicing and
memory-mapped alignment are lost, which are the headline reasons for an
appendix. A synthesis is possible (an encoding tag in the frame: raw only
as a final tail, SYN anywhere) at the price of two encodings in every
port. **Held in reserve.** The frame shape leaves room for a tag.

**A forward manifest.** A generalization worth keeping: a specially
marked, ordinary C0DATA group that declares what to expect over the next
extent of input, the forward-looking counterpart of ETB (which commits
what came before). The frame above is a degenerate manifest carrying two
facts, a name and a size. A manifest could carry a schema (see
`PROPOSAL-SCHEMA.md`, whose marked groups are already declarations of
expected shape), an extent, an encoding tag, or an appendix index, and it
fits the existing rule that referenced material is defined before use.
It does not restore arbitrary-offset scanning; it makes the loss explicit.
Not designed here; recorded as the shape a future appendix, schema, and
extent declaration would share.

**A magic number.** C0DATA has none; a document starts with FS, GS, RS, or
SOH. One would tell sequential readers something they do not need and
tell arbitrary-offset readers nothing, since they never see the start.

**Container index.** A trailing ordinary C0 document listing each
document's offset and size, ZIP-style, restores random access to a
chained container. It is a container layer above C0 and needs nothing
from the spec except declared sizes, which frames provide.

## Tooling implications

- **Pretty form / c0fmt.** After `␄`, render the frame as text and the
  bytes as one summary line (size, digest, row count). Pretty form is
  lossy for the appendix by design. Pretty-to-compact needs the appendix
  supplied separately; c0fmt would gain an option to attach an appendix
  file and one to strip it. This is the first time a C0 document cannot be
  fully shown as text, and it deserves discussion on its own.
- **C0DIFF.** Head only. A blob change appears as a row change (offset,
  length, hash). Byte-level appendix diff is a separate tool if ever
  needed.
- **Converters.** JSON, YAML, and CSV drop the appendix and keep
  references as the text they already are. JSON export may inline blobs as
  base64 behind a flag. No blob import in a first cut.
- **Reference API (Crystal, mirrored by every port).** On the document:
  the raw appendix slice, the index group, blob by name / by row / by
  range as zero-copy slices, and verification of the ETB digest. On the
  builder: an appendix block that takes a group name, collects named byte
  slices, and writes rows with computed offsets, the frame, the bytes, and
  the commit; plus a range-reference writer.
- **Conformance.** A `vectors/appendix.json` file, as with list fields.
- **Old readers.** No declaration needed. They stop at EOT, see a valid
  document, and resolve references into the index group as ordinary rows:
  the metadata, without the bytes. A spec version bump marks the addition.

## Open Questions

1. **ENQ or SO/SI for the frame.** Zero new codes with ENQ doing triple
   duty, or two new codes with self-explanatory semantics.
2. **Sequences.** Keep chaining legal and scope the scan principle to
   documents, or allow one appendix per container at the end and keep the
   principle literal.
3. **Per-blob digests in the first version**, or ETB only.
4. **Pretty form.** Summary line only, or an optional hex/base64 rendering
   for small appendices.
5. **Blob-first binding.** Error (proposed) or defined now.
6. **Placement.** A normative section in DESIGN.md (the semantics are
   core: what EOT+ENQ means, one new reference shape) or a separate
   profile spec as the original note suggested.

## Feedback

Discussion in progress. Nothing here is adopted until it appears in
DESIGN.md.
