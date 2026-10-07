# C0DATA Spec & Conformance Vectors

The single source of truth for [C0DATA](https://github.com/c0data) — the format
specification and the language-agnostic test fixtures that every implementation
(Crystal, JS, Rust, C, Python, …) is checked against. A fixture that passes in
one implementation must pass in all of them — the property content addressing
depends on.

## Layout

- `DESIGN.md` — the specification (the normative format definition).
- `GRAMMAR.md` — the formal grammar (ABNF) of well-formed input, with the
  canonical constraints.
- `reference.md` — the technical reference (format overview, control codes,
  data shapes, escaping, `c0fmt` usage).
- `vectors/*.json` — the conformance fixtures (decode, encode, canonical,
  invalid, stream).
- `vectors/README.md` — the fixture schema.
- `notes/` — design notes and proposals (non-normative): alternate
  design sketches, the schema-system proposal, and the 2026-10 proposals
  for a document start marker (SYN), comments (BEL), text and nesting
  (STX … ETX text, SI … CAN levels), keyed units (SOH introduces a
  key), and a trailing blob (EM), all settled 2026-10-07 and now
  normative in DESIGN.md. Nothing in `notes/` is adopted until it appears in DESIGN.md.

## Using the vectors

Each implementation includes this repository as a git submodule and runs its
tests against `vectors/`, so the copies can't drift — git pins the exact
version. Edit the fixtures here, never in a submodule checkout.
