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

    input     = L *document [ EM *OCTET ]
    document  = [ SYN L heading ] ( body / diff-body ) [ EOT L ]

A file or message is a sequence of documents, each with SYN; a document
without SYN is well-formed and draws DESIGN.md's loud warning, which is
how a slice (a group, a record, a log body) is read on its own.
Everything after EM, to the end of the input, is the raw region declared
in the first document's heading. Which of `body` and `diff-body` applies
is decided by the heading's `shape`, or by the reader's caller when
`shape` is absent.

## Heading and body

    heading   = *( keyed-unit / note )

    body      = part *( file-line part )
    file-line = [ BEL L ] FS L name L
    part      = *note [ header-row ] *item *group
    group     = group-line *note [ header-row ] *item
    group-line = [ BEL L ] 1*( GS L ) name L
    item      = record / note / commit

The heading ends where the body begins: at the first code that is neither
part of a keyed unit nor a note. A log is a document whose heading
declares `shape` `stream`; its items include commits. Records and groups
before the first FS belong to an unnamed file; records before the first
GS of a part belong to an unnamed group. A header row is the first item
of a part, a group or a level, after any notes. `GS L GS` is depth two;
an empty-named group therefore cannot directly precede another group.
Commits occur only at depth zero: `lbody` below is `body` without them.

    lbody     = lpart *( file-line lpart )
    lpart     = *note [ header-row ] *litem *lgroup
    lgroup    = group-line *note [ header-row ] *litem
    litem     = record / note

## Records

    record      = [ BEL L ] RS L ( keyed / positional )
    positional  = [ value ] *( US L [ value ] )
    keyed       = 1*keyed-unit
    keyed-unit  = [ BEL L ] SOH L name L US L [ value ]

    header-row  = [ BEL L ] SOH L RS L name L *( US L name L )

A record is keyed or positional, never both. `RS` alone is a positional
record of one empty field. `SOH` followed (after layout) by `RS` is a
header row; `SOH` followed by anything else begins a keyed unit, which
occurs only in a record or the heading. The heading's keyed units take
`hvalue` in place of `value` (no reference).

## Values

    value     = ( plain / text / level / reference ) L
    hvalue    = ( plain / text / level ) L

    text      = STX *tbyte ETX
    tbyte     = %x00-01 / %x05-0F / %x11-15 / %x18 / %x1A-FF
              / DLE ( STX / ETX / DLE / ETB / EOT / SYN / EM )

    level     = [ BEL L ] DLE L lbody CAN

    reference = ENQ L ( plain / STX 1*tbyte ETX )

Inside text every byte is data except STX, ETX, DLE, ETB, EOT, SYN and
EM, each of which is data only after a DLE. Text does not nest. A level
is DLE, then a body whose first token is a code (`FS`, `GS`, `RS`, `SOH`
or `BEL`; `lbody` admits no leading plain text and no commit), then CAN;
an empty body gives the empty level, `DLE CAN`. The DLE is on the opener
only. A reference is a group name, or a path of two or three non-empty
segments separated by US inside text
(`[ENQ][STX]group[US]record[US]field[ETX]`); text with one segment is a
group reference.

## Comments and commits

    note      = BEL L [ plain / text ] L

    commit    = ETB L [ plain ] L

BEL owns the text after it like any other code: a `note` is skipped by
the reader. A `[ BEL L ]` in front of a record, header row, keyed unit,
group line, file line or level marks that element **dead**: it is parsed
as written and then discarded. BEL before any other code (US, ETX, CAN,
ETB, EOT, SYN, EM) matches no production. A commit's plain text is its
payload; the commit ends the record before it.

## C0-DIFF

    diff-body = *( file-line *note *( [ BEL L ] GS L pattern L *note ) )
    pattern   = unit *( US L unit )
    unit      = [ dvalue ] [ SUB L [ dvalue ] ]
    dvalue    = ( plain / text ) L

A diff's heading should carry `shape` `diff`. A unit without SUB is an
anchor; with SUB it is a substitution, old then new. RS, SOH, DLE and ENQ
do not occur in a diff body; SUB does not occur outside one. A dead GS
kills its pattern; a dead FS kills its file.

## Canonical constraints

A canonical unit is well-formed and additionally:

1. contains no layout: every `L` is empty;
2. spells each value once: `plain` when the value has no byte below 0x20
   and no edge whitespace, `text` otherwise; no empty text; no text
   around a value that could be plain; a group reference is plain;
3. has, in every keyed record, keys unique and in ascending bytewise
   order;
4. contains no notes, dead elements, commits, SYN, heading, EOT or EM.
   The canonical document unit is a `body` with none of these.

A file as written carries SYN, a heading whose keys are unique and
sorted, the canonical body, and EOT; the heading and markers are outside
the hash.

## Notes for implementers

- Outside text, the hot test is `byte < 0x20`; on a hit, the byte's
  meaning is fixed by this grammar with one code of lookahead (`SOH` then
  `RS`; `BEL` then the code it kills; `DLE` then the first code of the
  level; layout may lie between) and no lookbehind.
- Inside text, the reader looks for seven byte values; the parity of the
  DLE run before one of them says whether it is escaped, a lookbehind
  bounded by the run's length. A backward scan for the last ETB or for EM
  counts the same run.
- A scanner that skips a level must skip text whole: a raw RS, US or CAN
  inside text matches `tbyte`, not a code. It counts DLE openers against
  CANs to find the level's end.
- Mid-buffer resynchronisation (first unescaped bracket decides inside or
  outside text; an unescaped SYN is a document start) holds everywhere
  before EM, and EM is itself found by the same scan.
