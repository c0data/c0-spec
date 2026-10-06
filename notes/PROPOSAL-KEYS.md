# Proposal: Keyed Units (SOH Marks a Key)

**Status:** Draft — agreed in discussion; details open
**Date:** 2026-10-06

## Summary

**SOH marks a key.** Inside a record, the unit after an SOH is a name,
and the unit after that is the value the name belongs to. With that one
rule the three structures every modern language is built on are all
records, at the same level of the hierarchy:

    ␞Admin␟Editor␟User                 a list: plain units
    ␞␁host␟localhost␁port␟5432          a map: keyed units

The table header C0DATA already has is the same marking, hoisted: SOH
after a group label means "these keys apply to every record below".

    ␝users␁name␟amount
      ␞Alice␟100
      ␞Bob␟200

So a table is a list of maps with the keys written once, which is what a
table is. Nothing about today's headers changes.

## Motivation

C0DATA had no way to say "this is a map". The config idiom wrote one
record per pair, `␞host␟localhost`, which is byte-for-byte a two-column
table, so the canonical-form section had to admit that map-ness is
invisible in the bytes and push map canonicalization onto producers,
where the conformance suite cannot check it. The JSON converter guessed.
And the document heading (`PROPOSAL-START.md`) needed pairs but could
not use RS, so it spelled them a second way, as alternating fields.

A list is a map whose keys are consecutive integers, implied by order.
A map is a list whose keys are written. They belong at the same level,
and the thing that distinguishes them is a mark on the keys. The only
code that means "the name of what follows" is SOH, and it already does
that job for tables.

## History

The hierarchy file, record, field predates ASCII; by the 1950s a record
was one entity's related fields. ASCII gave the hierarchy four
separators and insisted only on their nesting order, leaving what a
record *is* to each application. SOH was "the first character of a
heading of an information message", the information about a message
that precedes it. Names arrived through headers, a leading record of
column names, as CSV still does. ASCII never had a pair. This proposal
gives it one, using the code whose sense is "the heading of what
follows".

## Proposal

### The record grammar

A record is RS followed by units. A unit is one of:

- a **value**: plain, text, or a nested level;
- a **keyed unit**: SOH, a key, US, a value.

SOH both separates the unit from the one before it and marks it: no US
precedes an SOH. A key is a name under the same rules as a header name,
no control codes and no edge spaces. The value may be empty. A key with
nothing after it, at the end of a record, has an empty value.

A record is positional or keyed, never mixed (decided 2026-10-06): an
index lookup addresses a list, a key lookup a map, and nothing has to
say what an index returns from a map.

**SOH is an introducer, not a separator.** C0DATA is start-delimited: RS
does not separate records, it begins one, and the next RS ends the
previous record by beginning another. SOH is the same kind of thing one
level down. It begins a keyed unit, heading then text, and the next SOH
ends the previous one by beginning another. US is the only true
separator in the format and keeps that role everywhere: within a keyed
unit it divides the key from the value. Two alternatives were weighed
and rejected: a US between keyed units (`␁k␟v␟␁k␟v`), under which US
would alternate in meaning; and a colon-like code between key and value
(`k⁝v␟k⁝v`), JSON's shape, for which no code with a fitting name exists.

### Hoisted keys

SOH directly after a group label, or at the top of a log, carries the
keys for every record that follows, exactly as today. Records under
hoisted keys are positional.

### Maps and canonical form

A map is a record whose units are all keyed. In a canonical unit a map's
keys are **unique and sorted** by the bytewise order of their names.
Readers accept any order. This is the rule the map-canonical vectors
already state for producers, now checkable by the codec, so the
exception in DESIGN.md's canonical section goes away.

### Where it is used

- **The document heading** (`PROPOSAL-START.md`): `␖␁shape␟stream␁version␟2`.
- **Config**: one map record per section, respecting the hierarchy.

      ␝database␞␁host␟localhost␁port␟5432
      ␝server␞␁host␟0.0.0.0␁port␟8080

- **Nested maps**: a nested level holding a map record.

      ␞Alice␟␏␞␁street␟1 Main␁city␟Springfield␘

- **The JSON converter**: an object is a keyed record, an array a plain
  record, with no guessing. A headerless two-column group is what it
  always was, a list of pairs.

### The code-and-text rule

Taking stock of every code that is followed by its own text showed one
rule underneath all of them: **a code is followed by its own text, parts
separated by US, ending at the next control code.** Labels after FS and
GS, hoisted keys after SOH, the payload after ETB, the heading after SYN
are all that rule. The one exception is a code that sits inside a field,
where a US would end the field: there its text is fenced as text, STX … ETX.
ENQ is the only such code, so a bracket directly after ENQ is ENQ's text
and not a nested level. Position tells them apart, and the two can never
occupy the same place. Keyed units are the same rule with a mark.

## What it costs

- SOH inside a record is new. Every record scanner must treat SOH as a
  unit boundary that flags the next unit as a key. In the bytes it is
  free: no builder writes a raw SOH inside a record today, so none
  exists in conforming data.
- The schema proposal's `GS SOH` marker is dead for good, since SOH after
  a label already means keys. It was flawed in any case (see
  `PROPOSAL-SCHEMA.md`, Open Question 7).
- One more thing for a pretty-printer to align.

## Open Questions

1. **Duplicate keys outside canonical form.** Last wins, first wins, or
   an error.
2. **Pretty alignment** of keyed records in `c0fmt`'s aligned modes.
3. **The converter's reverse guess.** Whether a headerless two-column
   group should still export as a JSON object for compatibility, or now
   as an array of pairs.

## Feedback

Discussion in progress. Nothing here is adopted until it appears in
DESIGN.md.
