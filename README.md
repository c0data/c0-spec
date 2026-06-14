# C0DATA Conformance Vectors

The canonical, language-agnostic test fixtures for [C0DATA](https://github.com/trans/c0data).
This repository is the **single source of truth**: every implementation
(Crystal, JS, Rust, C, …) vendors a copy and runs against it, so a fixture that
passes in one implementation must pass in all of them — the property that
content addressing depends on.

## Layout

- `vectors/*.json` — the fixtures (decode, encode, canonical, invalid, stream).
- `vectors/README.md` — the fixture schema (encoding conventions, per-file
  case shapes).

## Using the vectors

Each implementation keeps an in-tree copy under its own `conformance/` (so its
tests run offline) and re-syncs from here at a tagged version. The copy should
record which version it was synced from. When the vectors change, bump the
version here, then re-vendor into each implementation.

Treat these files as read-only downstream: edit them here, never in a vendored
copy.
