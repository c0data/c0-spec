# C0DATA Grammar (ABNF)

The well-formedness grammar of compact and pretty form, in RFC 5234 ABNF
over bytes. Pretty form differs from compact form only in the Control
Picture glyphs standing for the codes and in layout, which the grammar
admits everywhere outside text through `L`. Canonical form is a subset
stated as constraints at the end; it is not a separate grammar.

This grammar describes well-formed input. Framing that cuts through an
open text or level (an unescaped ETB, EOT or SYN inside one) is not
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

## Start symbols

    input     = L ( container / body / diff-body )

    container = 1*document [ EM *OCTET ]
    document  = SYN L heading ( body / diff-body ) [ EOT L ]

A file or message is a `container`. A slice handled on its own (a group,
a record, a log body read without its heading) is a `body`; DESIGN.md
makes a missing SYN a loud warning, not an error. Everything after EM, to
the end of the container, is the raw region declared in the first
document's heading. Which of `body` and `diff-body` applies is decided by
the heading's `shape`, or by the reader's caller when `shape` is absent.

## Heading and body

    heading   = *keyed-unit

    body      = part *( FS L name L part )
    part      = *comment [ header-row ] *item *group
    group     = 1*( GS L ) name L *comment [ header-row ] *item
    item      = record / comment / commit

A document's heading ends where its body begins: at the first code that
is not inside a keyed unit. A log is a document whose heading declares
`shape` `stream`; its items include commits. Records and groups before
the first FS belong to an unnamed file; records before the first GS of a
part belong to an unnamed group. A header row is the first item of a
part, a group or a level, after any comments. `GS L GS` is depth two; an
empty-named group therefore cannot directly precede another group.

## Records

    record      = RS L ( keyed / positional )
    positional  = [ value ] *( US L [ value ] )
    keyed       = 1*keyed-unit
    keyed-unit  = SOH L name L US L [ value ]

    header-row  = SOH L RS L name L *( US L name L )

A record is keyed or positional, never both. `RS` alone is a positional
record of one empty field. `SOH` followed (after layout) by `RS` is a
header row; `SOH` followed by anything else begins a keyed unit. The
heading's keyed units take `hvalue` in place of `value` (no reference).

## Values

    value     = ( plain / text / level / reference ) L
    hvalue    = ( plain / text / level ) L

    text      = STX *tbyte ETX
    tbyte     = %x00-01 / %x05-0F / %x11-15 / %x18-FF
              / DLE ( STX / ETX / DLE / ETB / EOT / SYN )

    level     = DLE L body CAN

    reference = ENQ L ( plain / text )

Inside text every byte is data except STX, ETX, DLE, ETB, EOT and SYN,
each of which is data only after a DLE. Text does not nest. A level is
DLE, then a body whose first token is a code (`FS`, `GS`, `RS`, `SOH` or
`BEL`; `body` admits no leading plain text), then CAN; an empty body
gives the empty level, `DLE CAN`. The DLE is on the opener only. A reference is a group name,
or a path of two or three segments separated by US inside text
(`[ENQ][STX]group[US]record[US]field[ETX]`); the name is non-empty.

## Comments and commits

    comment    = BEL [ introducer ] *( cbyte / text / level )
    introducer = FS / GS / RS / SOH [ L RS ] / US / level
    cbyte      = SP / HT / LF / CR / nsp / US / ENQ / SUB / csoh
    csoh       = <SOH not followed by L RS>

    commit     = ETB L [ plain ] L

A comment runs to the next FS, GS, RS, `SOH RS`, DLE, SYN, EOT, ETB, EM
or BEL at its own depth, or the CAN of the level it sits in. An
introducer directly after the BEL belongs to the comment, so a comment
neutralises the record, group line, header row or nested level it is
written in front of. A bare SOH inside a comment is content: a comment
written in field position therefore runs to the end of its record. A
commit's plain text is its payload.

## C0-DIFF

    diff-body = *( FS L name L *( GS L pattern L *comment ) )
    pattern   = unit *( US L unit )
    unit      = [ dvalue ] [ SUB L [ dvalue ] ]
    dvalue    = ( plain / text ) L

A diff's heading should carry `shape` `diff`. A unit without SUB is an
anchor; with SUB it is a substitution, old then new. RS, SOH, DLE and ENQ
do not occur in a diff body; SUB does not occur outside one.

## Canonical constraints

A canonical unit is well-formed and additionally:

1. contains no layout: every `L` is empty;
2. spells each value once: `plain` when the value has no byte below 0x20
   and no edge whitespace, `text` otherwise; no empty text; no text
   around a value that could be plain; a group reference is plain;
3. has, in every keyed record, keys unique and in ascending bytewise
   order;
4. contains no framing or metadata: no comment, commit, SYN, heading,
   EOT or EM. The canonical document unit is a `body` with none of these.

A file as written carries SYN, a heading whose keys are unique and
sorted, the canonical body, and EOT; the heading and markers are outside
the hash.

## Notes for implementers

- Outside text, the hot test is `byte < 0x20`; on a hit, the byte's
  meaning is fixed by this grammar with one code of lookahead (`SOH` then
  `RS`, `DLE` then the first code of the level, with layout between) and
  no lookbehind.
- Inside text, the reader looks for six byte values; the parity of the
  DLE run before one of them says whether it is escaped, a lookbehind
  bounded by the run's length. A backward scan for the last ETB counts
  the same run.
- A scanner that skips a level must skip text whole: a raw RS, US or CAN
  inside text matches `tbyte`, not a code. It counts DLE openers against
  CANs to find the level's end.
- Mid-buffer resynchronisation (first unescaped bracket decides inside or
  outside text; an unescaped SYN is a document start) holds only before
  EM; a reader cannot tell it is inside the raw region without the first
  heading.
