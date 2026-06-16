# C0DATA Spec & Conformance Vectors

The single source of truth for [C0DATA](https://github.com/c0data) — the format
specification and the language-agnostic test fixtures that every implementation
(Crystal, JS, Rust, C, Python, …) is checked against. A fixture that passes in
one implementation must pass in all of them — the property content addressing
depends on.

## Layout

- `DESIGN.md` — the specification (the normative format definition).
- `reference.md` — the technical reference (format overview, control codes,
  data shapes, escaping, `c0fmt` usage).
- `vectors/*.json` — the conformance fixtures (decode, encode, canonical,
  invalid, stream).
- `vectors/README.md` — the fixture schema.
- `notes/` — design notes and proposals (non-normative): alternate
  design sketches and the schema-system proposal.

## Using the vectors

Each implementation includes this repository as a git submodule and runs its
tests against `vectors/`, so the copies can't drift — git pins the exact
version. Edit the fixtures here, never in a submodule checkout.
