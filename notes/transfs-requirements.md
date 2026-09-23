# C0DATA requirements from transfs

**Status:** Historical — every item below was resolved in c0 0.9 (ETB stream
mode, canonical-form contract, conformance vectors); the binary-field ask was
dropped in favour of the blob sidecar pattern (see DESIGN.md, "Binary Data").

> Source: the **transfs** project (`~/Projects/transfs`), a content-addressable
> file store. transfs has chosen C0DATA as its truth-layer encoding for two
> things: per-document **append-only claim logs** and **content-addressed
> manifests** (directory/collection blobs). This note is a punch-list of what
> transfs needs from the C0 *spec* (not any single implementation) to adopt it
> as a foundation. Written 2026-06-12.
>
> Why C0 is a strong fit here: the compact form is already declared canonical,
> the separator hierarchy is the native shape of a record log, and the
> `byte < 0x20` scanner is fast — and transfs rebuilds its entire index by
> folding logs, so scan speed matters. The gaps below are exactly the ones a
> document-oriented format wouldn't have hit yet, but an append-only,
> content-addressed log surfaces immediately.

---

## How transfs uses C0 (context for the asks)

A **claim log** is an append-only stream of heterogeneous records (one C0 group
of `RS` records, `US` fields, first field = the op name, variable arity):

```
create   op␟<nonce>␟<ts>
version  op␟<hash>␟<parent>␟<ts>
name     op␟<label>␟<ts>
tag      op␟␂add…␃␟␂del…␃␟<ts>
```

A **manifest** is a content blob whose bytes are a C0 table — `(name → hash)`
for a directory tree, or `(id → version)` for a collection. The manifest's
SHA-256 *is* its address, and the create record's hash *is* the document id.
So: **records get hashed, and equal logical records must produce equal bytes.**

Two properties are therefore load-bearing, and one is a strong optimization.

---

## 1. Append / record-stream framing with torn-tail detection — **REQUIRED**

**Problem.** C0 records are *start-delimited*: `RS` *begins* a record, nothing
marks its end except the next control code or EOF. For an append-only log that
is the source of truth, a process can crash mid-append and leave a
half-written final record. With start-delimiters only, a **truncated final
record is indistinguishable from a complete one** — the reader cannot know the
last record is whole. transfs must be able to append a record, and on replay
**skip an incomplete trailing record** rather than fold corrupt state.

(C0's `EOT` doesn't solve this — it's an optional whole-document terminator, and
a crashed append never reaches it. The `CAN` speculation is also adjacent but
different: it's sender-initiated "discard the preceding," not crash detection.)

**Ask.** A blessed **record-stream mode** for append-only logs in which each
*complete* record is followed by an explicit terminator, so a trailing fragment
lacking that terminator is detected and skipped. Concretely, any one of:

- **(a) Record terminator.** Define that in stream mode `RS` (or a dedicated
  end-of-record byte) is written *after* each complete record, not only before
  the next. Replay treats "bytes after the last terminator" as an incomplete
  tail and ignores them. Simplest; pure framing.
- **(b) Length-prefixed records.** Each record is `<varint length><bytes>`; a
  short read at the tail is a torn record. Robust, but less inspectable and
  less in the spirit of C0's delimiter model.
- **(c) Checkpointed records via ETB.** The `ETB`+hash speculation already in
  DESIGN.md, applied per-record: a record is valid iff its trailing checkpoint
  verifies. Strongest (also catches mid-record corruption, not just truncation)
  but heaviest.

transfs's need is satisfied by the lightest option **(a)**; **(c)** would be a
welcome superset if C0 wants integrity too. The key spec deliverable is a
**defined, documented contract**: "in stream mode, a record without a closing
terminator is incomplete and MUST be skipped on read." This generalizes to *any*
event log / WAL / SSE-style use, not just transfs.

### Update 2026-06-12: ETB stream mode is being implemented — transfs's view

Good — ETB block semantics also give transfs **batch atomicity for free**: write
N records, close with one ETB; either the whole block replays or none does (the
block boundary is the transaction boundary). transfs supplies the rest of
durability itself (fsync after record+ETB before acting; write content blob
*before* the claim referencing it, so a crash leaves only harmless orphan
garbage in a content-addressed store — no cross-file journal needed). So ETB
makes interrupted writes *recoverable*; recoverable + append-only + ordering is
how the journal achieves effective atomicity. **This is why a consumer like
transfs does not need a journal layer in front of the log — the log is the WAL.**

### On the open ETB hash-payload question — transfs's input

(Flagged because it's the live open question.) Recommendations, priority order:

1. **Carry an algorithm tag (multihash-lite): `algo-id ‖ length ‖ digest`.**
   This is the future-proofing win — digest length and function aren't frozen
   into the format, and integrity-only consumers can pick a cheap hash while
   content-addressing consumers pick a crypto one. The length field also
   resolves "how many bytes is the payload" deterministically (ties into the
   binary-payload encoding, #3).

2. **Frame the hash as integrity/recovery, NOT semantic identity — and keep them
   distinct.** The ETB hash answers *"did this block of bytes write intact?"*
   (framing, over a **block**). It must not be conflated with a consumer's
   *semantic identity* (e.g. transfs's document id / blob address), which is
   *"what is this thing?"* over a **single record's / blob's canonical value
   bytes**. The footgun: once the canonical contract (#2) lands,
   "hash of canonical values" and "hash of canonical block bytes" converge, and
   it gets tempting to reuse a single-record block's ETB hash as that record's
   identity. They can share an *algorithm* but not a *meaning* — different
   granularity (block vs record) and different role (recovery vs identity). Worth
   a one-line caution in the spec so downstream consumers don't couple them.

3. **Keep blocks INDEPENDENT — do not build a hash *chain* into the format.**
   A chained head-hash would help log-equality/sync, but that belongs at the
   consumer's semantic layer: if transfs ever wants a tamper-evident chain, it
   includes the previous hash as a *field in its own claim*, invisible to C0.
   Independent per-block integrity keeps C0 simple and composable for its other
   consumers.

4. **Define the hashed span to the byte** (which bytes ETB covers: from after the
   prior block boundary to before this ETB marker; state whether any leading
   separator/label is included). This is just the canonical contract (#2)
   applied to the hashed region — resolve them together.

5. **Scope note:** ETB is a *log* concern. Immutable manifest/content blobs are
   write-once, whole-document, addressed by the consumer's own CAS hash of the
   full byte sequence — they don't need per-block checkpoints. So the
   hash-payload design only has to serve the append-log case; manifest-blob needs
   shouldn't muddy it.

---

## 2. Canonical-encoding contract strong enough to hash — **REQUIRED**

**Problem.** DESIGN.md calls the compact form "canonical," and informally it is.
But content-addressing needs the **strong** form: a **bijection** — one logical
record maps to **exactly one** byte sequence, reproducible by any independent
encoder in any language (C0 has Cr/Go/JS/Rs/Ed implementations; they must all
emit identical bytes or hashes diverge). Two latent ambiguities currently break
that guarantee:

- **DLE escaping is not constrained to minimal.** `DLE A` and `A` both decode to
  literal `A`. An encoder that gratuitously escapes produces different bytes for
  the same data → different hash. **Rule needed:** *escape if and only if
  strictly necessary* (the next byte is a control code that would otherwise be
  interpreted). Canonical encoders MUST NOT emit unnecessary DLE.
- **Empty / trailing fields are undefined.** Is `Alice␟` (trailing empty field)
  distinct from `Alice`? Is an absent optional field encoded as an empty `US`
  unit or omitted? **Rule needed:** a defined, single representation for
  empty/absent fields and trailing separators.

Possibly also worth pinning for a bijection: ordering of any unordered
constructs (if SOH-headerless records ever allow reordering), and whether `EOT`
is part of the hashed region (transfs hashes a *record*, not a document, so for
us it isn't — but state it).

**Ask.** Promote "canonical" from a property to a **specified contract** in
DESIGN.md: a short "Canonical Form for Content-Addressing" section stating the
escaping-minimality rule, the empty/trailing-field rule, and an explicit
"same logical value ⇒ identical compact bytes across conforming encoders"
guarantee. This is a *tightening* of what's already claimed, not a new feature —
but it's mandatory before anyone hashes C0, and transfs is that anyone.

---

## 3. Binary field values (SO/SI) — **DROPPED (2026-06-12)**

Originally requested (SO/SI length-prefixed inline binary, to avoid hex-doubling
32-byte hashes). **Decided against by C0:** inline binary blobs have serious
complications — they break the simplicity of the `byte < 0x20` scan, tangle with
the canonical-hashing contract (#2) on length encoding, and complicate every
implementation. Not worth it.

**transfs's resolution:** hex-encode hashes (`hash`/`parent` → 64 text chars).
This was always our stated fallback, so nothing structural changes — it just
becomes the decided approach. Cost is 2× on hash fields only; acceptable, and
the canonical contract is cleaner without a binary case to specify.

**Possible far-future approach (parked — "well maybe", needs a hard use case):**
binary blobs appended **after `EOT`**, with in-document offset references into
that trailing blob region. This keeps the structured/scannable part pure text
and pushes raw bytes entirely outside the record grammar. Explicitly *not* on
any roadmap — recorded only so the idea isn't lost. Requires a proven,
compelling use case before reconsideration. transfs does **not** need it
(content blobs live in transfs's own CAS, not inside C0 documents).

---

## Priority summary

| # | Item | Status for transfs | Effort in C0 |
|---|------|--------------------|--------------|
| 1 | Append/record-stream framing + torn-tail skip | **DONE — C0 0.9 (ETB)** | — |
| 2 | Canonical-encoding-for-hashing contract | **Blocking** | small (spec tightening) |
| 3 | SO/SI binary fields | **Dropped** (hex-encode instead) | — |

Item 1 is delivered (ETB stream mode, C0 0.9). Item 2 (canonical contract) is
the one remaining blocker — small, well-scoped spec tightening.
They also harden C0 for the entire class of append-only / content-addressed /
WAL use cases — so working through transfs's needs is a net improvement to the
spec, not a transfs-specific carve-out. (Same symbiosis as crystalfuse: a
demanding real consumer surfaces the gaps the format's own tests wouldn't.)

If/when 1 and 2 are spec'd and in `c0-cr`, transfs swaps its JSON-one-per-line
interim encoding for C0 with **no change to its data model** — the format sits
behind a clean interface by design.
