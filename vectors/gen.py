#!/usr/bin/env python3
"""Generate the conformance vectors from glyph-form cases.

Cases are written with Unicode Control Pictures (␖ ␁ ␞ …) so they can be
read; this script turns them into the hex the JSON files carry. Run it
from the repository root after editing: `python3 vectors/gen.py`.
"""
import json
import pathlib

GLYPHS = {
    "␀": 0x00, "␁": 0x01, "␂": 0x02, "␃": 0x03, "␄": 0x04, "␅": 0x05,
    "␆": 0x06, "␇": 0x07, "␈": 0x08, "␉": 0x09, "␊": 0x0A, "␋": 0x0B,
    "␌": 0x0C, "␍": 0x0D, "␎": 0x0E, "␏": 0x0F, "␐": 0x10, "␑": 0x11,
    "␒": 0x12, "␓": 0x13, "␔": 0x14, "␕": 0x15, "␖": 0x16, "␗": 0x17,
    "␘": 0x18, "␙": 0x19, "␚": 0x1A, "␛": 0x1B, "␜": 0x1C, "␝": 0x1D,
    "␞": 0x1E, "␟": 0x1F,
}


def b(s):
    """Glyph string → bytes. `\\xNN` in the string is a raw byte."""
    out = bytearray()
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and s[i + 1] == "x":
            out.append(int(s[i + 2:i + 4], 16))
            i += 4
            continue
        if c in GLYPHS:
            out.append(GLYPHS[c])
        else:
            out += c.encode("utf-8")
        i += 1
    return bytes(out)


def h(s):
    return b(s).hex()


def level(records, headers=None):
    return {"level": {"headers": headers, "records": records}}


def keyed(*pairs):
    return {"keys": [list(p) for p in pairs]}


OUT = pathlib.Path(__file__).parent

# ---------------------------------------------------------------- decode
decode = []


def dec(name, desc, bytes_, groups, file=None, heading=None, tail=None):
    c = {"name": name, "desc": desc, "bytes": h(bytes_), "file": file,
         "groups": groups}
    if heading is not None:
        c["heading"] = heading
    if tail is not None:
        c["tail"] = h(tail)
    decode.append(c)


def g(name, records, headers=None):
    return {"name": name, "headers": headers, "records": records}


dec("simple-table", "Group with a header row (SOH RS) and two records",
    "␝users␁␞name␟amount␞Alice␟100␞Bob␟200",
    [g("users", [["Alice", "100"], ["Bob", "200"]], ["name", "amount"])])
dec("trailing-us-empty-field",
    "N separators = N+1 fields: trailing US yields a final empty field",
    "␞Alice␟", [g("", [["Alice", ""]])])
dec("leading-us-empty-field", "Leading US yields an initial empty field",
    "␞␟Alice", [g("", [["", "Alice"]])])
dec("empty-middle-field", "Consecutive US yields an empty middle field",
    "␞a␟␟c", [g("", [["a", "", "c"]])])
dec("empty-record-at-end",
    "Trailing RS is an empty record with one empty field",
    "␞a␞", [g("", [["a"], [""]])])
dec("empty-record-between", "RS RS is an empty record before the next",
    "␞a␞␞b", [g("", [["a"], [""], ["b"]])])
dec("text-us-in-value",
    "US inside text is a character, not a separator; the value is the inside of the text",
    "␞␂a␟b␃␟z", [g("", [["a\x1fb", "z"]])])
dec("text-rs-in-value", "RS inside text is a character; no escape needed",
    "␞␂a␞b␃", [g("", [["a\x1eb"]])])
dec("text-escaped-etx", "DLE ETX inside text is a data ETX",
    "␞␂a␐␃b␃", [g("", [["a\x03b"]])])
dec("text-escaped-dle", "DLE DLE inside text is a data DLE",
    "␞␂a␐␐b␃", [g("", [["a\x10b"]])])
dec("text-escaped-framing",
    "DLE before ETB, EOT or SYN inside text is that data byte",
    "␞␂a␐␗b␐␄c␐␖d␃", [g("", [["a\x17b\x04c\x16d"]])])
dec("text-raw-newline-tab", "LF and HT inside text are data",
    "␞␂line 1␊\tline 2␃", [g("", [["line 1\n\tline 2"]])])
dec("text-edge-spaces", "Spaces at the edges of text are data",
    "␞␂  padded  ␃␟x", [g("", [["  padded  ", "x"]])])
dec("text-binary",
    "Every byte but the six is data inside text, unassigned codes and non-UTF-8 included",
    "␞␂␀␁\\xff␃", [g("", [[{"hex": "0001ff"}]])])
dec("text-empty", "Empty text is the empty string (legal, not canonical)",
    "␞␂␃␟x", [g("", [["", "x"]])])
dec("layout-spaces-trimmed",
    "Whitespace touching a control code is layout, in compact form too",
    "␞ Alice ␟ Bob ", [g("", [["Alice", "Bob"]])])
dec("layout-lines-trimmed",
    "Line breaks and indentation around codes are layout; interior spaces are data",
    "␝users␊  ␞Alice Smith␟100␊  ␞Bob␟200␊",
    [g("users", [["Alice Smith", "100"], ["Bob", "200"]])])
dec("keyed-record", "SOH introduces a keyed unit; the record is a map",
    "␞␁host␟localhost␁port␟5432",
    [g("", [keyed(("host", "localhost"), ("port", "5432"))])])
dec("keyed-empty-value", "A keyed unit may have an empty value",
    "␞␁a␟␁b␟2", [g("", [keyed(("a", ""), ("b", "2"))])])
dec("keyed-text-value", "A keyed unit's value may be text",
    "␞␁note␟␂  hi  ␃", [g("", [keyed(("note", "  hi  "))])])
dec("keyed-records-as-written",
    "Keyed units are reported in written order; duplicates are reported too (a map API resolves last-wins with a warning)",
    "␞␁b␟1␁a␟2␁b␟3",
    [g("", [keyed(("b", "1"), ("a", "2"), ("b", "3"))])])
dec("nested-list", "A nested level holding one record is a list",
    "␞Alice␟␏␞Admin␟Editor␘␟x",
    [g("", [["Alice", level([["Admin", "Editor"]]), "x"]])])
dec("nested-empty", "An empty level holds no records",
    "␞␏␘␟x", [g("", [[level([]), "x"]])])
dec("nested-one-empty", "A level holding one empty record: a list of one empty string",
    "␞␏␞␘", [g("", [[level([[""]])]])])
dec("nested-table", "Several records in a level form a table",
    "␞␏␞1␟2␞3␟4␘", [g("", [[level([["1", "2"], ["3", "4"]])]])])
dec("nested-header-row", "A header row inside a level names its columns",
    "␞Alice␟␏␁␞street␟city␞1 Main␟Springfield␘",
    [g("", [["Alice", level([["1 Main", "Springfield"]], ["street", "city"])]])])
dec("nested-map", "A keyed record inside a level is a map value",
    "␞␏␞␁a␟1␁b␟2␘", [g("", [[level([keyed(("a", "1"), ("b", "2"))])]])])
dec("nested-nested", "Levels nest",
    "␞␏␞␏␞a␟b␘␟c␘", [g("", [[level([[level([["a", "b"]]), "c"]])]])])
dec("nested-text-inside", "Text inside a level; RS, SI and CAN inside the text are characters",
    "␞␏␞␂x␞y␏z␘w␃␟p␘", [g("", [[level([["x\x1ey\x0fz\x18w", "p"]])]])])
dec("nested-layout", "Layout inside a level is layout",
    "␞␏␊  ␁␞a␟b␊  ␞1␟2␊␘",
    [g("", [[level([["1", "2"]], ["a", "b"])]])])
dec("bare-records", "Records with no FS/GS preamble (e.g. a stream log body)",
    "␞a␟b␞c␟d", [g("", [["a", "b"], ["c", "d"]])])
dec("multi-group-document", "FS file name with two GS groups",
    "␜db␝g1␞a␝g2␁␞x␞b",
    [g("g1", [["a"]]), g("g2", [["b"]], ["x"])], file="db")
dec("utf8-value", "Multibyte UTF-8 passes through untouched (no normalization)",
    "␞héllo␟日本", [g("", [["héllo", "日本"]])])
dec("etb-tolerated",
    "ETB commit markers are framing: parsed structure is identical with or without them",
    "␞a␟b␗␞c␟d␗", [g("", [["a", "b"], ["c", "d"]])])
dec("header-no-records", "Group with a header row and zero records",
    "␝g␁␞a␟b", [g("g", [], ["a", "b"])])
dec("heading-empty", "SYN with an empty heading, EOT at the end",
    "␖␝g␞a␄", [g("g", [["a"]])], heading=[])
dec("heading-keys", "The heading is keyed units after SYN",
    "␖␁shape␟stream␁version␟1␞a␟b",
    [g("", [["a", "b"]])], heading=[["shape", "stream"], ["version", "1"]])
dec("heading-then-header-row",
    "SOH RS ends the heading and is the log's header row",
    "␖␁shape␟stream␁␞x␟y␞1␟2",
    [g("", [["1", "2"]], ["x", "y"])], heading=[["shape", "stream"]])
dec("heading-nested-value", "A heading value may be a level (the blob table)",
    "␖␁blob␟␏␁␞name␟offset␟length␞img␟0␟3␘␝g␞a",
    [g("g", [["a"]])],
    heading=[["blob", level([["img", "0", "3"]], ["name", "offset", "length"])]])
dec("comment-record", "BEL before a record comments it out, up to the next RS",
    "␝g␞a␇␞b␞c", [g("g", [["a"], ["c"]])])
dec("comment-note", "A plain note after a group label",
    "␝g␇ staging only␞a", [g("g", [["a"]])])
dec("comment-header-row", "A commented-out header row declares nothing",
    "␝g␇␁␞x␟y␞a", [g("g", [["a"]])])
dec("comment-in-level", "Comments are allowed inside a level",
    "␞␏␇␞x␞y␘", [g("", [[level([["y"]])]])])
dec("comment-with-text", "Text inside a comment is content of the comment",
    "␝g␇␂␞not a record␃␞a", [g("g", [["a"]])])
dec("em-stops-reading", "Everything after EM is the raw tail, not scanned",
    "␖␁blob␟␏␁␞name␟offset␟length␞t␟0␟3␘␝g␞a␙x␞y",
    [g("g", [["a"]])],
    heading=[["blob", level([["t", "0", "3"]], ["name", "offset", "length"])]],
    tail="x␞y")

# ---------------------------------------------------------------- encode
encode = []


def enc(name, desc, build, canonical, bytes_=None):
    c = {"name": name, "desc": desc, "build": build, "canonical": h(canonical)}
    if bytes_ is not None:
        c["bytes"] = h(bytes_)
    encode.append(c)


def doc(groups, file=None, heading=None):
    d = {"file": file, "groups": groups}
    if heading is not None:
        d["heading"] = heading
    return d


enc("simple-table", "Header row and records encode in order, nothing fenced",
    doc([g("users", [["Alice", "100"], ["Bob", "200"]], ["name", "amount"])]),
    "␝users␁␞name␟amount␞Alice␟100␞Bob␟200")
enc("text-for-control-byte", "A value holding a control byte is text; RS inside text is raw",
    doc([g("", [["a\x1eb"]])]), "␞␂a␞b␃")
enc("text-escapes-six", "Only STX, ETX, DLE, ETB, EOT, SYN take a DLE inside text",
    doc([g("", [["\x02\x03\x10\x17\x04\x16"]])]), "␞␂␐␂␐␃␐␐␐␗␐␄␐␖␃")
enc("text-for-newline-tab", "LF and HT in a value require text and are raw inside it",
    doc([g("", [["a\nb\tc"]])]), "␞␂a␊b␉c␃")
enc("text-for-edge-space", "Edge whitespace requires text; interior space does not",
    doc([g("", [[" x", "y ", "Alice Smith"]])]), "␞␂ x␃␟␂y ␃␟Alice Smith")
enc("empty-string-plain", "The empty string is written as nothing",
    doc([g("", [["", "a", ""]])]), "␞␟a␟")
enc("binary-run", "Bytes 0x00–0x1F in a value: text, with only the six escaped",
    doc([g("", [[{"hex": bytes(range(32)).hex()}]])]),
    "␞␂␀␁␐␂␐␃␐␄␅␆␇␈␉␊␋␌␍␎␏␐␐␑␒␓␔␕␐␖␐␗␘␙␚␛␜␝␞␟␃")
enc("high-bytes-unescaped", "No byte >= 0x20 is ever fenced (UTF-8 passes through)",
    doc([g("", [["héllo", "日本"]])]), "␞héllo␟日本")
enc("keyed-record-sorted", "A map encodes as a keyed record with keys sorted bytewise",
    doc([g("", [keyed(("port", "5432"), ("host", "localhost"))])]),
    "␞␁host␟localhost␁port␟5432")
enc("keyed-byte-lex", "Key order is by raw byte: 'Z' (0x5a) before 'a' (0x61)",
    doc([g("", [keyed(("a", "1"), ("Z", "2"))])]), "␞␁Z␟2␁a␟1")
enc("nested-list", "A list is a level holding one record",
    doc([g("", [["Alice", level([["Admin", "Editor"]])]])]),
    "␞Alice␟␏␞Admin␟Editor␘")
enc("nested-empty", "An empty list is an empty level", doc([g("", [[level([])]])]), "␞␏␘")
enc("nested-one-empty", "A list of one empty string is a level with one empty record",
    doc([g("", [[level([[""]])]])]), "␞␏␞␘")
enc("nested-map", "A map value is a level holding one keyed record, sorted",
    doc([g("", [["cfg", level([keyed(("b", "2"), ("a", "1"))])]])]),
    "␞cfg␟␏␞␁a␟1␁b␟2␘")
enc("nested-table-header", "A nested table with a header row",
    doc([g("", [[level([["1 Main", "Springfield"]], ["street", "city"])]])]),
    "␞␏␁␞street␟city␞1 Main␟Springfield␘")
enc("file-two-groups", "Document with FS name and two groups; the canonical unit has no framing",
    doc([g("g1", [["a"]]), g("g2", [["b"]], ["x"])], file="db"),
    "␜db␝g1␞a␝g2␁␞x␞b")
enc("heading-written", "With a heading the file is SYN, sorted keys, body, EOT; the canonical unit is the body",
    doc([g("g", [["a"]])], heading=[["version", "1"], ["shape", "tabular"]]),
    "␝g␞a", bytes_="␖␁shape␟tabular␁version␟1␝g␞a␄")

# -------------------------------------------------------------- canonical
canonical = []


def can(name, desc, bytes_, wellformed, canonical_):
    canonical.append({"name": name, "desc": desc, "bytes": h(bytes_),
                      "wellformed": wellformed, "canonical": canonical_})


can("plain-table", "Ordinary table, nothing fenced, no framing",
    "␝g␁␞a␟b␞1␟2", True, True)
can("text-necessary", "Text around a value holding a control byte: canonical",
    "␞␂a␟b␃", True, True)
can("text-escaped-six", "DLE before one of the six inside text: canonical",
    "␞␂a␐␗b␃", True, True)
can("text-gratuitous", "Text around a value that could be plain: not canonical",
    "␞␂only␃", True, False)
can("text-empty", "Empty text: the empty string is written as nothing",
    "␞␂␃", True, False)
can("layout-space", "Whitespace touching a code is layout: legal, not canonical",
    "␞a ␟b", True, False)
can("layout-newline", "Line breaks between codes are layout",
    "␝g␊␞a", True, False)
can("keyed-sorted", "Keyed record with sorted unique keys", "␞␁a␟1␁b␟2", True, True)
can("keyed-unsorted", "Keys out of bytewise order: not canonical", "␞␁b␟1␁a␟2", True, False)
can("keyed-duplicate", "Duplicate key: not canonical", "␞␁a␟1␁a␟2", True, False)
can("trailing-eot", "EOT is framing: not part of a canonical document unit",
    "␞a␄", True, False)
can("etb-framing", "ETB is framing: not part of a canonical document unit",
    "␞a␗", True, False)
can("syn-heading", "SYN and the heading are framing: not part of a canonical document unit",
    "␖␁shape␟stream␞a", True, False)
can("comment", "A comment is outside the hash: not part of a canonical unit",
    "␝g␇note␞a", True, False)
can("raw-lf-in-plain", "LF inside a plain value: malformed", "␞a␊b", False, False)
can("dle-outside-text", "DLE outside text: malformed", "␞a␐b", False, False)
can("dle-before-plain-in-text", "DLE before a byte that is not one of the six: malformed",
    "␞␂a␐bc␃", False, False)
can("dangling-dle", "DLE at end of input: malformed", "␞␂a␐", False, False)
can("unassigned-code", "Bare unassigned control byte: malformed", "␞a␆b", False, False)
can("so-byte", "SO is permanently unassigned", "␞a␎b", False, False)
can("level-label", "Text after SI is reserved: malformed", "␞␏x␞a␘", False, False)
can("mixed-record", "A record is positional or keyed, never mixed", "␞a␁k␟v", False, False)

# ---------------------------------------------------------------- invalid
invalid = []


def inv(name, desc, bytes_):
    invalid.append({"name": name, "desc": desc, "bytes": h(bytes_)})


inv("unassigned-nul", "NUL (0x00) is unassigned outside text", "␞␀")
inv("unassigned-ack", "ACK (0x06) is unassigned", "␞␆")
inv("unassigned-so", "SO (0x0E) is permanently unassigned", "␞␎")
inv("raw-lf-in-plain", "LF in the middle of a plain value", "␞a␊b")
inv("raw-tab-in-plain", "HT in the middle of a plain value", "␞a␉b")
inv("dle-outside-text", "DLE has no meaning outside text", "␞a␐␟b")
inv("dle-before-plain-in-text", "DLE inside text before a byte that is not one of the six", "␞␂a␐bc␃")
inv("dangling-dle", "DLE at end of input has nothing to escape", "␞␂a␐")
inv("text-unclosed", "Text open at end of input", "␞␂abc")
inv("stx-inside-text", "Text does not nest", "␞␂a␂b␃␃")
inv("text-spliced", "Text cannot be part of a plain value", "␞a␂b␃c")
inv("etx-unmatched", "ETX with no open text", "␞a␃")
inv("level-unclosed", "A level open at end of input", "␞␏␞a")
inv("can-unmatched", "CAN with no open level", "␞a␘")
inv("level-label", "Text after SI is reserved", "␞␏rgb␞1␟2␟3␘")
inv("text-after-can", "Text after CAN belongs to nothing", "␞␏␘x")
inv("mixed-record", "Positional then keyed units in one record", "␞a␁k␟v")
inv("key-without-value", "SOH, key, then a record-level code with no US", "␞␁k␞x")
inv("name-with-text", "Labels and keys are never text", "␝␂g␃␞a")

# ----------------------------------------------------------------- stream
stream = []


def st(name, desc, bytes_, committed_end, torn, blocks, records=None, damaged=None):
    c = {"name": name, "desc": desc, "bytes": h(bytes_),
         "committed_end": committed_end, "torn": torn,
         "blocks": [h(x) for x in blocks]}
    if records is not None:
        c["records"] = records
    if damaged is not None:
        c["damaged"] = damaged
    stream.append(c)


st("two-commits", "Two records, each ETB-committed", "␞a␗␞b␗", 6, False,
   ["␞a", "␞b"], [["a"], ["b"]])
st("torn-tail", "Uncommitted trailing record is skipped", "␞a␗␞b", 3, True,
   ["␞a"], [["a"]])
st("batch-block", "Two records under one commit form one atomic block",
   "␞a␞b␗", 5, False, ["␞a␞b"], [["a"], ["b"]])
st("escaped-etb-in-text-not-commit", "DLE ETB inside text is data; nothing is committed",
   "␞␂a␐␗b␃", 0, True, [])
st("etb-in-text-cuts", "A raw ETB inside open text is a commit: the block is damaged, and later commits are found",
   "␞␂a␗␞b␗", 7, False, ["␞␂a", "␞b"], damaged=[0])
st("etb-in-level-cuts", "A raw ETB inside an open level is a commit: that block is damaged",
   "␞␏␞a␗␞b␗", 8, False, ["␞␏␞a", "␞b"], damaged=[0])
st("heading-committed", "The SYN heading is committed with the first ETB like anything else",
   "␖␁shape␟stream␗␞a␗", 18, False, ["␖␁shape␟stream", "␞a"], [["a"]])
st("header-row-committed", "A header row is committed like a record",
   "␁␞x␟y␗␞1␟2␗", 11, False, ["␁␞x␟y", "␞1␟2"], [["1", "2"]])
st("payload-in-committed-region", "ETB payload extends committed_end but is excluded from the block",
   "␞a␗sha256:00␞b␗", 15, False, ["␞a", "␞b"], [["a"], ["b"]])
st("torn-open-text", "A tail that leaves text open is torn", "␞a␗␞␂b", 3, True, ["␞a"], [["a"]])
st("torn-lone-dle", "A tail ending in a lone DLE is torn", "␞a␗␞␂b␐", 3, True, ["␞a"], [["a"]])
st("empty-stream", "Empty buffer: no commits, not torn", "", 0, False, [])

# ----------------------------------------------------------------- nested
nested = []


def ne(name, desc, bytes_, record, canonical_=True):
    nested.append({"name": name, "desc": desc, "bytes": h(bytes_),
                   "record": record, "canonical": canonical_})


def lst(*items):
    return {"list": list(items)}


ne("three-items", "A list of three plain items between two scalar fields",
   "␞Alice␟␏␞Admin␟Editor␟User␘␟100", ["Alice", lst("Admin", "Editor", "User"), "100"])
ne("empty-list", "An empty level is an empty list", "␞a␟␏␘", ["a", lst()])
ne("one-empty-item", "A level with one empty record is a list of one empty string",
   "␞a␟␏␞␘", ["a", lst("")])
ne("two-empty-items", "A lone US in the record yields two empty items",
   "␞a␟␏␞␟␘", ["a", lst("", "")])
ne("single-item", "One item, no separator", "␞a␟␏␞x␘", ["a", lst("x")])
ne("two-lists", "Adjacent list fields; CAN closes one before the next US",
   "␞a␟␏␞1␟2␘␟␏␞3␘", ["a", lst("1", "2"), lst("3")])
ne("text-item", "An item holding a control byte is text inside the level",
   "␞a␟␏␞␂x␟y␃␟z␘", ["a", lst("x\x1fy", "z")])
ne("binary-item", "A binary item is text; 0xFF is raw",
   "␞a␟␏␞␂␀\\xff␃␘", ["a", lst({"hex": "00ff"})])
ne("list-in-list", "A nested level inside an item is a nested list",
   "␞a␟␏␞␏␞x␟y␘␟z␘", ["a", lst(lst("x", "y"), "z")])
ne("map-item", "A keyed record inside a level is a map, not a list",
   "␞a␟␏␞␁k␟v␘", ["a", level([keyed(("k", "v"))])])
ne("table-not-a-list", "Two records in a level form a table; the list accessor rejects it",
   "␞a␟␏␞1␟2␞3␟4␘", ["a", level([["1", "2"], ["3", "4"]])])
ne("header-row-in-level", "A level with a header row is a named-column table",
   "␞a␟␏␁␞x␟y␞1␟2␘", ["a", level([["1", "2"]], ["x", "y"])])
ne("plain-field-as-list", "Reading a non-level field as a list yields its value as one item (decode only)",
   "␞a␟b", ["a", lst("b")], canonical_=False)

# ---------------------------------------------------------- map-canonical
mapc = []


def mc(name, desc, group, map_, canonical_):
    mapc.append({"name": name, "desc": desc, "group": group, "map": map_,
                 "canonical": h(canonical_)})


mc("basic-sort", "Two entries given out of order; sorted by key: host (0x68) before port (0x70)",
   "database", [["port", "5432"], ["host", "localhost"]],
   "␝database␞␁host␟localhost␁port␟5432")
mc("byte-lex-not-alpha", "Order is by raw byte, not case-insensitive or locale: 'A' (0x41) < 'Z' (0x5a) < 'a' (0x61)",
   None, [["a", "1"], ["Z", "2"], ["A", "3"]], "␞␁A␟3␁Z␟2␁a␟1")
mc("empty-key-first", "The empty key sorts before any non-empty key",
   None, [["a", "1"], ["", "0"]], "␞␁␟0␁a␟1")
mc("nested-map-recurse", "A value that is itself a map is a level holding a keyed record, sorted recursively",
   "cfg", [["z", "26"], ["nested", {"map": [["b", "2"], ["a", "1"]]}]],
   "␝cfg␞␁nested␟␏␞␁a␟1␁b␟2␘␁z␟26")
mc("text-value", "A value needing text is fenced; keys are names and never are",
   None, [["k", "a\nb"]], "␞␁k␟␂a␊b␃")

# ------------------------------------------------------------------ write
for fname, cases in [("decode", decode), ("encode", encode),
                     ("canonical", canonical), ("invalid", invalid),
                     ("stream", stream), ("nested", nested),
                     ("map-canonical", mapc)]:
    names = [c["name"] for c in cases]
    assert len(names) == len(set(names)), fname
    (OUT / f"{fname}.json").write_text(
        json.dumps({"version": 2, "cases": cases}, ensure_ascii=False, indent=2) + "\n")
    print(fname, len(cases))
