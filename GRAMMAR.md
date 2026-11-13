# C0DATA Grammar (ABNF)

The well-formedness grammar of compact and pretty form, in RFC 5234 ABNF
over bytes. Pretty form differs from compact form only in the Control
Picture glyphs standing for the codes and in layout, which the grammar
admits everywhere outside text through `L`. Canonical form is a subset
stated as constraints at the end; it is not a separate grammar.

This grammar describes well-formed input. Framing that cuts through an
open text or level (an unescaped ETB, EOT, SYN or EM inside one) is not
well-formed; a document reader rejects it and a stream reader handles it
by the rules in DESIGN.md.

## Codes

    SOH = %x01   STX = %x02   ETX = %x03   EOT = %x04   ENQ = %x05
    BEL = %x07   DLE = %x10   SYN = %x16   ETB = %x17   CAN = %x18
    EM  = %x19   SUB = %x1A
    FS  = %x1C   GS  = %x1D   RS  = %x1E   US  = %x1F

    HT  = %x09   LF  = %x0A   CR  = %x0D   SP  = %x20

Every other byte below 0x20 is unassigned outside text and does not
appear in any production.

## Layout and plain bytes

    L     = *( SP / HT / LF / CR )        ; layout: touches a code, is not data
    nsp   = %x21-FF                       ; a non-whitespace data byte
    plain = nsp *( *SP nsp )              ; a plain value: no edge whitespace,
                                          ;   interior spaces only
    name  = [ plain ]                     ; a label, key or header name

`L` follows every code and every value, and begins the input. HT, LF and
CR therefore occur outside text only as layout; one in the middle of a
plain value matches no production. Layout never changes the meaning of
the codes around it.

## Start symbol

    input     = L [ first ] *document [ EM *OCTET ]
    first     = [ SYN L heading ] body [ EOT L ]
    document  = SYN L heading body [ EOT L ]

A file or message is a sequence of documents, each with SYN; only the
first may lack it, which is well-formed and draws DESIGN.md's loud
warning, and is how a slice (a group, a record, a log body) is read on
its own. After an EOT only SYN, EM or the end of input may follow.
Everything after EM, to the end of the input, is the raw region declared
in the first document's heading. Every shape, the diff included, parses
as `body`; a shape gives meaning and adds constraints (`DIFF.md`), it
never changes what follows a code.

## Heading and body

    heading   = *( hunit / note )
    hunit     = [ BEL L / sup ] SOH L name L US L [ hvalue ]

    body      = part *( file-line part )
    file-line = [ BEL L / sup ] FS L name L
    part      = *pre [ header-row ] *item *group
    group     = group-line *pre [ header-row ] *item
    group-line = [ BEL L / sup ] 1*( GS L ) name L
    pre       = note / commit / dead-record / dead-header
    item      = record / dead-record / note / commit
    dead-record = BEL L RS L ( keyed / positional )
    dead-header = BEL L SOH L RS L name L *( US L name L )

The heading ends where the body begins: at the first code that is neither
part of a keyed unit nor a note. A log is a document whose heading
declares `shape` `stream`; its items include commits. Records and groups
before the first FS belong to an unnamed file; records before the first
GS of a part belong to an unnamed group. A header row is the first live
item of a part, a group or a level, after any notes, commits or dead
elements; anywhere else a header row, live or dead, is an error, which
is why `dead-header` occurs only in `pre`. A dead group line opens a dead
group and a dead file line a dead file: what they hold is parsed and
discarded with them. `GS L GS` is depth two;
an empty-named group therefore cannot directly precede another group.
Stripping what stands between two GS (a note, a dead element, a commit)
can bring them together: `␝␇n␝b` is two groups at depth one, `␝␝b` one
group at depth two. A canonicaliser or encoder that would write two GS
in a row where the input had two groups refuses, as a formatter refuses
a value that collides with its glyphs; it never changes depth.
Commits occur only at depth zero: `lbody` below is `body` without them.

    lbody     = lpart *( file-line lpart )
    lpart     = *lpre [ header-row ] *litem *lgroup
    lgroup    = group-line *lpre [ header-row ] *litem
    lpre      = note / dead-record / dead-header
    litem     = record / dead-record / note

## Records

    record      = [ sup ] RS L ( keyed / positional )
    positional  = unit *( [ sup ] US L unit )
    unit        = [ ( plain / text / level / reference ) L ] *note
    keyed       = *note keyed-unit *( keyed-unit / note )
    keyed-unit  = [ BEL L / sup ] SOH L name L US L unit

    sup         = SUB L

    header-row  = SOH L RS L name L *note *( US L name L *note )

A record is keyed or positional, never both. A record is keyed when it
holds at least one keyed unit, live or dead; `RS` alone, or RS followed
only by notes (`␞␇n`), is a positional record of one empty unit. A unit holds at most one value, followed by any
number of notes; a note is never a unit, so `␞a␇n␟b` is two units and
`␞Alice␟␇old␟100` three. `SOH` followed (after layout) by `RS` is a
header row; `SOH` followed by anything else begins a keyed unit, which
occurs only in a record or the heading. The heading's units take `hvalue`
(no reference). A keyed record whose units are all dead is an empty map.

`sup` is **supersession** (DESIGN.md, Supersession): SUB before US, SOH,
RS, GS or FS marks the element before that code as superseded by the
element after it, at that code's grain. It is admitted wherever the code
is, which is why `sup` stands in each rule above and in `hunit`; a header
row's names are not units and admit none. SUB before any other byte, at
the end of input, before BEL, or after BEL (`␚␇␞`, `␇␚␞`) matches no
production. `␝g␚␞x` with no record before it in the group, `␚␝` with no
earlier group at that depth, `␚␜` with no earlier file and `␚␁` with no
earlier keyed unit in the record are errors: there is nothing to
supersede. A unit always has a predecessor, so `␞␚␟x` is the empty first
unit superseded by `x`.

## Values

    hvalue    = [ ( plain / text / level ) L ] *note

    text      = STX *tbyte ETX
    tbyte     = %x00-01 / %x05-0F / %x11-15 / %x18 / %x1A-FF
              / DLE ( STX / ETX / DLE / ETB / EOT / SYN / EM )

    level     = [ BEL L ] DLE L lbody CAN

    reference = ENQ L ( plain / DLE L lbody CAN )

A dead level (`BEL L DLE …`) in unit position leaves the unit empty.

Inside text every byte is data except STX, ETX, DLE, ETB, EOT, SYN and
EM, each of which is data only after a DLE. Text does not nest. A level
is DLE, then a body whose first token is a code (`FS`, `GS`, `RS`, `SOH`
or `BEL`; `lbody` admits no leading plain text and no commit), then CAN;
an empty body gives the empty level, `DLE CAN`. The DLE is on the opener
only. A reference is a group name, or a pattern: a level whose body is
one branch of the target with its values left out (DESIGN.md, References).
A pattern holds at most one file line, then group lines, then at most one
record; a positional record in it holds one to three units, a name, a
name, and a level that continues the pattern; a keyed record in it holds
one keyed unit with an empty value. Every name is written plain. A pattern
holding anything else (text, a header row, a dead element, a second record
or group at one depth, an element after the record, an empty body) is an
error, as is ENQ followed by text. A pattern that is a bare group
(`ENQ DLE GS name CAN`) is a group reference, legal and not canonical.

## Comments and commits

    note      = BEL L ( plain / text ) L

    commit    = ETB L [ plain ] L

BEL owns the text after it like any other code: a `note` has content and
is skipped by the reader. A `BEL L` in front of a record, header row,
keyed unit, group line, file line or level marks that element **dead**:
it is parsed as written and then discarded. Because a note's content is
required, `BEL` directly before a code is always the dead marker, and BEL
before any other code (US, ETX, CAN, ENQ, BEL, SUB, ETB, EOT, SYN, EM) or
at the end of input matches no production. A commit's plain text is its
payload; the commit ends the record before it.

## C0DIFF

A diff (`shape` `diff`) has no grammar of its own: it is a `body` whose
records are anchored patterns, with supersession at the unit grain as the
substitution. What a diff may not hold, and what its records mean, is in
`DIFF.md`.

## Canonical constraints

A canonical span (a record, a group or a body as hashed; DESIGN.md,
Canonical Spans) is well-formed and additionally:

1. contains no layout: every `L` is empty;
2. spells each value once: `plain` when the value has no byte below 0x20
   and no edge whitespace, `text` otherwise; no empty text; no text
   around a value that could be plain; a group reference is plain;
3. has, in every keyed record, unique keys; their order is data and is
   kept as written;
4. contains no notes, dead elements, commits, SYN, heading, EOT or EM.
   The canonical document span is a `body` with none of these.
   Supersession is content and is kept, each side in its one spelling.

A file as written carries SYN, a heading whose keys are unique, the
canonical body, and EOT; the heading and markers are outside the hash.

## Notes for implementers

- Outside text, the hot test is `byte < 0x20`; on a hit, the byte's
  meaning is fixed by this grammar with two codes of lookahead, layout
  skipped (`SOH` then `RS`; `BEL` then the code it kills, which may be
  `SOH` then `RS`; `SUB` then the code it qualifies; `DLE` then the first
  code of the level), and one code
  of lookbehind, or a counter, for GS depth (`GS` after `GS`).
- Inside text, the reader looks for seven byte values; the parity of the
  DLE run before one of them says whether it is escaped, a lookbehind
  bounded by the run's length. A backward scan for the last ETB or for EM
  counts the same run.
- A scanner that skips a level must skip text whole: a raw RS, US or CAN
  inside text matches `tbyte`, not a code. It counts DLE openers against
  CANs to find the level's end.
- Mid-buffer resynchronisation (first unescaped bracket decides inside or
  outside text; an unescaped SYN is a document start) holds everywhere
  before EM. A backward scan presumes the container has no raw region;
  with EM present the first heading says where the region starts.
