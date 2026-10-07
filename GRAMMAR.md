# C0DATA Grammar (ABNF)

The well-formedness grammar of compact and pretty form, in RFC 5234 ABNF
over bytes. Pretty form differs from compact form only in the Control
Picture glyphs standing for the codes and in layout, which the grammar
admits everywhere outside text through `L`. Canonical form is a subset
stated as constraints at the end; it is not a separate grammar.

This grammar describes well-formed input. Framing that cuts through an
open text or level (an unescaped ETB, EOT or SYN inside one) is not
well-formed and is handled by the stream rules in DESIGN.md.

## Codes

    SOH = %x01   STX = %x02   ETX = %x03   EOT = %x04   ENQ = %x05
    BEL = %x07   SI  = %x0F   DLE = %x10   SYN = %x16   ETB = %x17
    CAN = %x18   EM  = %x19   SUB = %x1A
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

`L` follows every code and every value. HT, LF and CR therefore occur
outside text only as layout; one in the middle of a plain value matches
no production.

## Container

    container = 1*document [ EM *OCTET ]

    document  = SYN L heading body [ EOT L ]
    heading   = *keyed-unit
    body      = [ FS L name L ] *item *group
    group     = 1*( GS L ) name L *item

    item      = record / header-row / comment / commit

A document's heading ends where its body begins: at the first code that
is not inside a keyed unit. A log is a document without EOT whose items
include commits. Everything after EM, to the end of the container, is
the raw region declared in the first document's heading.

## Records

    record      = RS L ( keyed / positional )
    positional  = [ value ] *( US L [ value ] )
    keyed       = 1*keyed-unit
    keyed-unit  = SOH L name L US L [ value ]

    header-row  = SOH L RS L name L *( US L name L )

A record is keyed or positional, never both. `RS` alone is a positional
record of one empty field. `SOH` followed by `RS` is a header row; `SOH`
followed by anything else begins a keyed unit.

## Values

    value     = ( plain / text / level / reference ) L

    text      = STX *tbyte ETX
    tbyte     = %x00-01 / %x05-0F / %x11-15 / %x18-FF
              / DLE ( STX / ETX / DLE / ETB / EOT / SYN )

    level     = SI L [ header-row ] *( record / comment ) CAN

    reference = ENQ L ( name / text )

Inside text every byte is data except STX, ETX, DLE, ETB, EOT and SYN,
each of which is data only after a DLE. Text does not nest. The position
directly after SI holds no text: a level's label is reserved. A reference
is a group name, or a path whose segments are separated by US inside
text (`[ENQ][STX]group[US]record[US]field[ETX]`).

## Comments and commits

    comment   = BEL [ introducer ] *( cbyte / text / level )
    introducer = FS / GS / RS / SOH [ L RS ] / US
    cbyte     = SP / HT / LF / CR / nsp / US / ENQ / SUB

    commit    = ETB L [ plain ] L

A comment runs to the next FS, GS, RS, SOH, SYN, EOT, ETB, BEL, or the
CAN of the level it sits in. An introducer directly after the BEL
belongs to the comment, so a comment neutralises the record, group line
or header row it is written in front of; `SOH RS` is one introducer. A
commit's plain text is its payload.

## C0-DIFF

    diff      = SYN L heading *dfile [ EOT L ]
    dfile     = FS L name L *( GS L pattern L )
    pattern   = unit *( US L unit )
    unit      = [ dvalue ] [ SUB L [ dvalue ] ]
    dvalue    = ( plain / text ) L

A diff's heading should carry `shape` `diff`. A unit without SUB is an
anchor; with SUB it is a substitution, old then new.

## Canonical constraints

A canonical unit is well-formed and additionally:

1. contains no layout: every `L` is empty;
2. spells each value once: `plain` when the value has no byte below 0x20
   and no edge whitespace, `text` otherwise; no empty text; no text
   around a value that could be plain;
3. has, in every keyed record and heading, keys unique and in ascending
   bytewise order;
4. contains no framing or metadata: no SYN, heading, EOT, ETB, comment,
   or EM. The canonical document unit is `body`.

## Notes for implementers

- Outside text, the hot test is `byte < 0x20`; on a hit, the byte's
  meaning is fixed by this grammar with at most one byte of lookahead
  (`SOH` then `RS`) and no lookbehind.
- Inside text, the reader looks for six byte values; a DLE is always
  followed by one of them.
- A scanner that skips a level must skip text whole: a raw RS, US, SI or
  CAN inside text matches `tbyte`, not a code.
- The grammar admits `GS` only at the top of a document and inside no
  level; a level holds records.
