# Independent review of C0DIFF and the pair redesign (2026-11-09)

A cold read of DIFF.md, GRAMMAR.md's `diff-body`, PROPOSAL-SUPERSESSION.md,
MARK.md, diff.json and gen.py's reference applier by a reviewer with no
prior knowledge of the project. Citations spot-checked the same day
(findings 1, 2, 3, 4, 6 confirmed by reading). Line numbers as of
commit 434c06c. Nothing here is decided.

## Verdict (reviewer's)

Proceed with the pair as a base-grammar unit kind and the diff as files
of records: sound, strictly simpler, and a generic reader then reads a
diff correctly. Before DIFF.md is rewritten, decide in writing: (1)
whether a pair is well-formed in every document or only under the diff
shape, the sketch says both (recommend: everywhere; converters refuse
what they cannot represent); (2) whether sides are mandatory, decided on
its real ground, the reserved `SUB <opener>` slot, and if yes with the
canonical and warning exception for `␂␃` written into GRAMMAR.md and
DESIGN.md (reviewer leans: optional sides, close the slot); (3) the diff
shape's constraint list (keyed unit, level, reference, header row, GS,
pre-FS record, empty path, island: all errors). Then: defer replace-all,
uniqueness to end of file, GS forbidden, drop the term "boundary",
rewrite gen.py to consume the base parser, regenerate vectors.

## Findings, most important first

1. **The sketch re-introduces a shape-dependent grammar.** "A shape that
   does not define the pair rejects it" (sketch) vs "marks are not a
   shape; they sit in any document" (sketch) and MARK.md's whole-unit pair
   in any keyed record. If the pair is base grammar, `␞a␚b` with no
   heading is well-formed. Invalid vector `sub-outside-diff` and DESIGN
   "SUB is rejected elsewhere" are wrong under the new design.
   *Confirmed.*

2. **Mandatory sides rest on the unadopted supersession idea.**
   `old␚␞end` is ambiguous only if `␚␞` already means something. With
   optional sides the byte after SUB still decides with no lookahead.
   Mandatory sides cost a context-sensitive exception to "empty text is
   non-canonical and a warning", unstated in the sketch, and respell
   today's insertion/deletion vectors. Decide on the true ground: (a)
   mandatory, state the slot as the reason, add the exception; or (b)
   optional, keep "empty is written as nothing", close the slot.
   *Confirmed.*

3. **The diff shape's constraint list is missing.** DIFF.md bans SOH, DLE,
   ENQ and relies on "outside diff-body is an error"; under the base
   grammar a keyed unit, level, reference, header row, GS and pre-FS
   record are all well-formed and the sketch says nothing. Recommend:
   errors, so each slot stays additive (a keyed diff record is the natural
   future replace-all spelling). *Confirmed.*

4. **Pair rules to state, one line each**: no chaining (`a␚b␚c` error);
   sides plain or text only; `a␚b␇n` is pair then note, `a␇n␚b` error; no
   pair in names, header rows, notes, heading values; SUB joins the
   BEL-error list; `␚` at EOF, `␚␞`, `␚␟`, `␟␚x`, `␞␚x` errors; layout
   around SUB per the layout rule (add a pretty-form vector). The sketch's
   `unit = value / level / reference / pair` drops the empty unit, `L`
   and `*note` that GRAMMAR.md's rule has. *Confirmed.*

5. **"Semantics carry over word for word" is half true.** Sections and
   Atomicity carry over verbatim (with insertion/deletion respelled under
   mandatory sides). Replace-all, BEL attachment ("a dead GS kills its
   pattern; RS lines attach to the previous live section" becomes "a dead
   record is dropped and does not move the cursor"), the error list and
   the Structure paragraph are rewritten. Say so.

6. **"Boundary" names a distinction that does not exist**: under DIFF.md
   every record moves the cursor. Keep "assertion" unless a rule needs the
   term. *Confirmed.*

7. **Claim that `diff-body` is a second grammar holds**, and so does the
   no-lookahead claim (one code after layout, as the base grammar already
   does). Consequential edits: Consistent Roles table, C0-DIFF section of
   DESIGN.md.

8. **Replace-all**: defer. Any mark now re-labels RS/GS or spends a code;
   the scope needs a container the flat list lacks. Keep keyed records and
   GS as errors so the two future spellings stay additive.

9. **GS in a diff**: error, not inert label; inert-then-meaningful changes
   the meaning of valid 1.0 bytes.

10. **Uniqueness span**: keep end of file; the next-boundary rule accepts
    a superset, so loosening later is additive and tightening is not, and
    EOF keeps validation independent of later records.

11. **Pair as grammar**: yes, conditional on 1, 2 and 4.

12. **Separation from C0MARK is right.** Restated in both: `␂␃` spelling
    and "the byte after SUB decides" (cite GRAMMAR.md instead). In
    neither: the meaning of a pair in a document that is neither diff nor
    marked. Interaction: under MARK's island rule, `DLE RS` inside text in
    a diff record would be an island; DIFF.md must say an island in a diff
    record is an error. "Hashed as written" should read "hashed over its
    canonicalised bytes, both sides".

13. **Simplicity holds**: minus seven productions and one alternation,
    plus one production and one branch; user loses section, replace-all,
    scope, attach rules. Move supersession and the data-target section out
    of the decision document.

14. **gen.py must be rewritten**, not patched: the diff applier should
    consume the base parser's records, or the vectors do not test the
    claim.

15. **Vectors**: 25 re-encode GS→RS, 2 respell, 7 drop (the replace-all
    and attach cases). Add: pre-FS record, keyed/level/reference/header/GS
    in a diff, empty FS path, dead record cursor, `␂␃␚␂␃`, both sides
    text, pretty-form diff, and the six gaps that exist today (empty search
    text, path escape, no files, file with no records, layout, literal
    0x1A in an anchor, ETB with payload). Base vectors: pair in positional,
    keyed, level; `a ␚ b` well-formed non-canonical; invalid list in
    finding 4; move `sub-outside-diff` to decode.

16. **DESIGN.md edits to enumerate**: SUB row and "rejected elsewhere";
    example diff; `shape` row; empty-text warning/canonical (if mandatory);
    BEL error list; roles table; C0-DIFF section; Open Questions.

## Taste

Spell the empty side as nothing and give up the slot. Drop "boundary".
Let the pretty printer align on SUB as on US. MARK.md's lean "one BEL
rule everywhere" is right.
