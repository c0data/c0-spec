# Proposal: Comments (BEL)

**Status:** Draft — direction agreed in discussion, details open
**Date:** 2026-10-05

## Summary

**BEL (0x07)** begins a comment. A comment is text for humans: it means
nothing to any reader or tool. Comments are part of the compact form, so
converting between compact and pretty forms loses nothing; they are
outside the hash, like other framing.

To comment something out, put a BEL **in front of it**. The code that
follows the BEL is kept, so nothing is lost and nothing has to be guessed
when the BEL is removed again.

In pretty form (BEL is `␇`):

    ␝database
      ␇ primary database, see the ops runbook
      ␞host␟localhost
      ␇␞port␟5432
      ␞port␟6432␇ pgbouncer, not postgres
    ␇␝server
      ␇␞host␟0.0.0.0
      ␇␞port␟8080

That is one group, `database`, with two live records (`host localhost`,
`port 6432`). Everything introduced by `␇` is comment: a note, a
commented-out record, a trailing note on a record, and a commented-out
group line with its two records.

This assigns a control code (the fourteenth, counting SYN from
`PROPOSAL-START.md`).

## Motivation

The absence of comments is the most common complaint against JSON.
C0DATA claims the configuration niche of TOML and INI, where people
expect to annotate what they edit.

Comments are neither metadata nor data. The test used elsewhere: what the
format's reader or tools act on is metadata; what the application acts on
is data. Nobody acts on a comment. That is why the usual objection to
annotations (XML's attributes competing with elements) does not apply, as
long as the rule holds that a comment carries no meaning to any program.

They belong in the compact form, not only the pretty form. YAML and TOML
parsers simply discard comments, but C0DATA promises more: compact and
pretty are two forms of the same thing and conversion between them is
lossless. Comments that existed only in pretty form would vanish the
first time a tool compacted a file. Whether a sender strips them before
transmission is a separate, optional step.

## Proposal

### The rule

1. BEL begins a comment.
2. A structural code immediately after the BEL belongs to the comment and
   has no effect.
3. The comment then runs to the next record-level code, scanned the way a
   record is: DLE pairs and STX/ETX scopes are skipped.

So `[BEL][RS]port[US]5432` is a commented-out record,
`[BEL][GS]server` a commented-out group line,
`[BEL][SOH]name[US]amount` a commented-out header, and
`[BEL] see the runbook` a plain note, which is simply the case with no
code after the BEL.

### Prefix, not replace

An earlier form of this idea replaced the RS with the comment code. That
destroys information: on restoring, one must guess which code was there,
and the guess gets worse with every code a future format adds. With a
prefix, commenting out is inserting one byte and restoring is deleting
it. It works the same for RS, GS, SOH, FS, and any future code. This is
how `#` and `//` behave: they go before a line; they do not overwrite its
first character.

### Elements, not lines

Lines are not real. They exist only as layout in pretty form, where line
breaks are ignored; compact form has none. A comment therefore does not
run to the end of a line. It runs to the next record-level code, wherever
that sits:

    ␇␞host␟0.0.0.0␝server␞port␟8080

Only `␞host␟0.0.0.0` is comment. The `␝` ends it; the group `server` and
its record are live. In the other direction, a long note may wrap across
lines and is still one comment.

Tooling covers the hazard for people who think in lines: the formatter
starts every record-level element on its own line, and editor grammars
colour from the BEL to the next record-level code rather than to the end
of the line.

### Trailing comments

A BEL ends the record before it, as any record-level code does, so a note
may follow a record directly:

    ␞port␟6432␇ pgbouncer, not postgres

The record is `port`, `6432`. Field slices stay contiguous, because a
comment never sits inside a value.

### Group lines

Commenting out a group line alone does not hide the group's records.
They fall into the group before it, exactly as commenting out a
`[section]` line does in an INI file. To remove a whole group, comment
each of its elements.

This is deliberate. A BEL before GS that swallowed the entire group would
make a block comment one byte, but a reader landing mid-file would see
live-looking records with no way of knowing that a commented group line
sat far above them. Keeping each comment to one element preserves the
property that structure is determinable locally.

### Comment text

Comment text follows the rules of a value: bytes below 0x20 are
DLE-escaped. To mention a control code literally in a note it must be
escaped, or it will be taken as the real thing and end the comment.

### Hashing

Comments are framing. A canonical unit contains none, in the way it
contains no ETB or EOT. The stripped form is what is hashed; two
documents that differ only in comments are the same document.

### No meaning

A conforming reader or tool MUST NOT change its interpretation of the
data on account of a comment's content. Instructions to readers go in the
document heading (`PROPOSAL-START.md`). This is the guard against the
misuse that led JSON to drop comments: parser directives smuggled into
them.

## Tooling implications

- **Tokenizer:** emits a comment token. **Readers** (table, document)
  skip it.
- **Builder:** a method to write a note, and one to write a commented-out
  element.
- **Pretty form:** each comment on its own line; `c0fmt` gains an option
  to strip comments.
- **Editor grammar:** highlight the true extent, BEL to the next
  record-level code.
- **Converters:** JSON and CSV have no comments and drop them. YAML export
  could carry notes as `#` lines.

## Practical notes: BEL on a terminal

BEL rings the terminal when printed raw. In practice viewers do not print
it raw. Checked on one Linux system:

- `cat -v` prints it as `^G`.
- `less` shows control characters in caret notation by default.
- `bat -A --nonprintable-notation unicode` renders compact C0DATA as
  control pictures already (`␝database␞host␟localhost␇ primary db…`).
- `git diff` treats a file containing BEL as text and diffs it.

Only a raw `cat` of a compact file to a terminal beeps, which is already
a poor way to view one.

## Alternatives considered

- **SO … SI brackets.** "Shift out of the data, shift back in" fits, and
  a pair can wrap a whole block. But a missing closer swallows the rest of
  the file; a reader starting mid-file cannot tell it is inside a comment;
  a bracket pair invites meta attributes, which this proposal exists to
  avoid; and a raw SO flips the Linux console and some terminals into the
  line-drawing set. It also spends the one pair that means a mode shift.
- **DC2 … DC4 brackets.** Same structural drawbacks; obscure meaning.
- **NAK as the single code.** Reads as "not a record". A looser metaphor
  than BEL's "call for human attention".
- **DC2 or DC4 as the single code.** No meaning to remember it by.
- **CAN, EM.** Both have better jobs waiting (cancel; end of medium).
- **DLE plus a printable byte.** No new code, but DLE stops having one
  simple job.
- **Pretty form only.** Breaks the lossless round trip.
- **Replace instead of prefix.** Loses the replaced code.
- **Level-aware comments** (BEL before GS hides the group). Breaks local
  determinability.
- **General inline metadata.** Out of scope by design; see
  `PROPOSAL-START.md`, "What the heading is not".

Never assignable for any purpose: the format effectors (tab, line feed,
carriage return and their kin, which editors rewrite), NUL (breaks C
strings and makes tools treat a file as binary), ESC, and DC1/DC3
(terminals and serial links act on them).

## Decided (2026-10-06)

- **Framing cannot be commented out.** A BEL before EOT, ETB, or SYN does
  not neutralise it; those codes mean what they mean everywhere.
- **Comments are allowed inside nested levels,** between the records of a
  nested table, exactly as at the top.
- **Stripping is a tool option.** No profile may require comment-free
  input.
- **Comments may appear inside committed blocks** of a stream log. The
  block's ETB digest covers them, because it covers every byte between
  two commits as written; the content hash does not, because comments
  are framing and outside every canonical unit. The two spans already
  differ (the block span includes the leading RS, the canonical record
  excludes it) and answer different questions: whether the write landed,
  and what the data is.

- **A comment has the extent of a record** (2026-10-06). It ends where
  an element of the enclosing shape ends, and is scanned the way that
  element is: in C0DATA at the next FS, GS, RS, SOH, SYN, EOT, ETB, or
  BEL, or at the ETX that closes a nested level it sits in; in a C0-DIFF
  at the next FS or GS. What does not end it: US, which is content; a
  nested level, skipped whole; DLE sequences, so a literal region inside
  a comment holds anything, control codes included; ENQ and SUB. A BEL
  before a nested value comments out that value through its matching
  ETX, `␞Alice␟␇␂␞Admin␟Editor␃`, as a consequence of the prefix rule;
  no general bracketed comment is added.

## Feedback

Discussion in progress. Nothing here is adopted until it appears in
DESIGN.md.
