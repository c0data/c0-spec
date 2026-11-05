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


def dec(name, desc, bytes_, groups, file=None, heading=None, tail=None,
        files=None, documents=None):
    c = {"name": name, "desc": desc, "bytes": h(bytes_), "file": file,
         "groups": groups}
    if heading is not None:
        c["heading"] = heading
    if tail is not None:
        c["tail"] = h(tail)
    if files is not None:
        c["files"] = files
    if documents is not None:
        c["documents"] = documents
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
    "DLE before ETB, EOT, SYN or EM inside text is that data byte",
    "␞␂a␐␗b␐␄c␐␖d␐␙e␃", [g("", [["a\x17b\x04c\x16d\x19e"]])])
dec("text-raw-newline-tab", "LF and HT inside text are data",
    "␞␂line 1␊\tline 2␃", [g("", [["line 1\n\tline 2"]])])
dec("text-edge-spaces", "Spaces at the edges of text are data",
    "␞␂  padded  ␃␟x", [g("", [["  padded  ", "x"]])])
dec("text-binary",
    "Every byte but the seven is data inside text, unassigned codes and non-UTF-8 included",
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
    "␞Alice␟␐␞Admin␟Editor␘␟x",
    [g("", [["Alice", level([["Admin", "Editor"]]), "x"]])])
dec("nested-empty", "An empty level holds no records",
    "␞␐␘␟x", [g("", [[level([]), "x"]])])
dec("nested-one-empty", "A level holding one empty record: a list of one empty string",
    "␞␐␞␘", [g("", [[level([[""]])]])])
dec("nested-table", "Several records in a level form a table",
    "␞␐␞1␟2␞3␟4␘", [g("", [[level([["1", "2"], ["3", "4"]])]])])
dec("nested-header-row", "A header row inside a level names its columns",
    "␞Alice␟␐␁␞street␟city␞1 Main␟Springfield␘",
    [g("", [["Alice", level([["1 Main", "Springfield"]], ["street", "city"])]])])
dec("nested-map", "A keyed record inside a level is a map value",
    "␞␐␞␁a␟1␁b␟2␘", [g("", [[level([keyed(("a", "1"), ("b", "2"))])]])])
dec("nested-nested", "Levels nest",
    "␞␐␞␐␞a␟b␘␟c␘", [g("", [[level([[level([["a", "b"]]), "c"]])]])])
dec("nested-text-inside", "Text inside a level; RS, SOH and CAN inside the text are characters",
    "␞␐␞␂x␞y␁z␘w␃␟p␘", [g("", [[level([["x\x1ey\x01z\x18w", "p"]])]])])
dec("nested-layout", "Layout inside a level is layout, after the opener too",
    "␞␐␊  ␁␞a␟b␊  ␞1␟2␊␘",
    [g("", [[level([["1", "2"]], ["a", "b"])]])])
dec("nested-empty-level", "DLE CAN is the empty level (no body)",
    "␞␐␘␟x", [g("", [[level([]), "x"]])])
dec("nested-document", "A level may hold a whole body: groups and files",
    "␞doc␟␐␜f␝g1␞a␝g2␁␞x␞b␘",
    [g("", [["doc", {"level": {"files": [{"name": "f", "groups": [g("g1", [["a"]]), g("g2", [["b"]], ["x"])]}]}}]])])
dec("reference-group", "ENQ with a plain name is a group reference; reported as written",
    "␞a␟␅tags", [g("", [["a", {"ref": "tags"}]])])
dec("reference-path", "ENQ with text is a path; segments split on US",
    "␞a␟␅␂tags␟001␟label␃", [g("", [["a", {"ref": ["tags", "001", "label"]}]])])
dec("gs-depth", "GS repetition is depth; subsections belong to the group",
    "␝c1␞p1␝␝s1␞p2␝c2␞p3",
    [{"name": "c1", "headers": None, "records": [["p1"]],
      "sections": [{"name": "s1", "headers": None, "records": [["p2"]]}]},
     g("c2", [["p3"]])])
dec("two-files", "A document may hold several FS files",
    "␜a␝g␞1␜b␝g␞2",
    [g("g", [["1"]])], file="a", files=[{"name": "a", "groups": [g("g", [["1"]])]},
                         {"name": "b", "groups": [g("g", [["2"]])]}])
dec("records-before-first-gs", "Records before the first GS form the unnamed group",
    "␜db␞a␝g␞b", [g("", [["a"]]), g("g", [["b"]])], file="db")
dec("etb-payload-tolerated", "Outside stream mode an ETB and its payload are a no-op",
    "␞a␗sha256:00␞b", [g("", [["a"], ["b"]])])
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
    "␖␁shape␟tabular␁version␟1␞a␟b",
    [g("", [["a", "b"]])], heading=[["shape", "tabular"], ["version", "1"]])
dec("heading-then-header-row",
    "SOH RS ends the heading and is the body's header row",
    "␖␁version␟1␁␞x␟y␞1␟2",
    [g("", [["1", "2"]], ["x", "y"])], heading=[["version", "1"]])
dec("heading-layout-between-soh-rs", "Layout between SOH and RS is still a header row",
    "␖␁version␟1␊␁ ␞x␟y␊␞1␟2",
    [g("", [["1", "2"]], ["x", "y"])], heading=[["version", "1"]])
dec("heading-nested-value", "A heading value may be a level (the blob table)",
    "␖␁blob␟␐␁␞name␟offset␟length␞img␟0␟3␘␝g␞a",
    [g("g", [["a"]])],
    heading=[["blob", level([["img", "0", "3"]], ["name", "offset", "length"])]])
dec("comment-record", "BEL before a record marks it dead; it is parsed and discarded",
    "␝g␞a␇␞b␞c", [g("g", [["a"], ["c"]])])
dec("comment-layout-then-record", "Layout after BEL is layout; the record is still dead",
    "␝g␇␊␞b␞c", [g("g", [["c"]])])
dec("comment-dead-group-line", "A dead group line; its records belong to the group before",
    "␝g1␞1␇␝g2␞2", [g("g1", [["1"], ["2"]])])
dec("comment-dead-keyed-unit", "A dead keyed unit is dropped from the map",
    "␞␁a␟1␇␁b␟2␁c␟3", [g("", [keyed(("a", "1"), ("c", "3"))])])
dec("comment-note-in-heading", "A note between heading keys",
    "␖␁a␟1␇old␁b␟2␞x", [g("", [["x"]])], heading=[["a", "1"], ["b", "2"]])
dec("comment-note", "A plain note after a group label",
    "␝g␇ staging only␞a", [g("g", [["a"]])])
dec("comment-header-row", "A dead header row declares nothing",
    "␝g␇␁␞x␟y␞a", [g("g", [["a"]])])
dec("comment-in-level", "Comments are allowed inside a level",
    "␞␐␇␞x␞y␘", [g("", [[level([["y"]])]])])
dec("comment-dead-level-in-field", "A dead level leaves an empty unit; the next field is live",
    "␞Alice␟␇␐␞Admin␘␟100␞Bob", [g("", [["Alice", "", "100"], ["Bob"]])])
dec("comment-note-in-field", "A note in field position is one empty unit",
    "␞Alice␟␇old value␟100", [g("", [["Alice", "", "100"]])])
dec("comment-note-between-keyed-units", "A note ends at the next code; the next key is live",
    "␞␁a␟1␇n␁b␟2␞x", [g("", [keyed(("a", "1"), ("b", "2")), ["x"]])])
dec("comment-ends-at-header-row", "A note ends at a header row",
    "␝g␇note␁␞x␟y␞1␟2", [g("g", [["1", "2"]], ["x", "y"])])
dec("comment-with-text", "A note that holds control codes is text",
    "␝g␇␂␞not a record␃␞a", [g("g", [["a"]])])
dec("two-documents", "Two documents in one container, each with its own SYN",
    "␖␝g␞a␄␖␝g␞b␄", [], documents=[
        {"heading": [], "file": None, "groups": [g("g", [["a"]])]},
        {"heading": [], "file": None, "groups": [g("g", [["b"]])]}])
dec("em-stops-reading", "Everything after EM is the raw tail, not scanned",
    "␖␁blob␟␐␁␞name␟offset␟length␞t␟0␟3␘␝g␞a␙x␞y",
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
enc("text-escapes-seven", "Only STX, ETX, DLE, ETB, EOT, SYN, EM take a DLE inside text",
    doc([g("", [["\x02\x03\x10\x17\x04\x16\x19"]])]), "␞␂␐␂␐␃␐␐␐␗␐␄␐␖␐␙␃")
enc("text-for-newline-tab", "LF and HT in a value require text and are raw inside it",
    doc([g("", [["a\nb\tc"]])]), "␞␂a␊b␉c␃")
enc("text-for-edge-space", "Edge whitespace requires text; interior space does not",
    doc([g("", [[" x", "y ", "Alice Smith"]])]), "␞␂ x␃␟␂y ␃␟Alice Smith")
enc("empty-string-plain", "The empty string is written as nothing",
    doc([g("", [["", "a", ""]])]), "␞␟a␟")
enc("binary-run", "Bytes 0x00–0x1F in a value: text, with only the seven escaped",
    doc([g("", [[{"hex": bytes(range(32)).hex()}]])]),
    "␞␂␀␁␐␂␐␃␐␄␅␆␇␈␉␊␋␌␍␎␏␐␐␑␒␓␔␕␐␖␐␗␘␐␙␚␛␜␝␞␟␃")
enc("high-bytes-unescaped", "No byte >= 0x20 is ever fenced (UTF-8 passes through)",
    doc([g("", [["héllo", "日本"]])]), "␞héllo␟日本")
enc("keyed-record-sorted", "A map encodes as a keyed record with keys sorted bytewise",
    doc([g("", [keyed(("port", "5432"), ("host", "localhost"))])]),
    "␞␁host␟localhost␁port␟5432")
enc("keyed-byte-lex", "Key order is by raw byte: 'Z' (0x5a) before 'a' (0x61)",
    doc([g("", [keyed(("a", "1"), ("Z", "2"))])]), "␞␁Z␟2␁a␟1")
enc("nested-list", "A list is a level holding one record",
    doc([g("", [["Alice", level([["Admin", "Editor"]])]])]),
    "␞Alice␟␐␞Admin␟Editor␘")
enc("nested-empty", "An empty list is an empty level", doc([g("", [[level([])]])]), "␞␐␘")
enc("nested-one-empty", "A list of one empty string is a level with one empty record",
    doc([g("", [[level([[""]])]])]), "␞␐␞␘")
enc("nested-empty-level", "An empty level is DLE CAN", doc([g("", [[level([]), "x"]])]), "␞␐␘␟x")
enc("reference-plain", "A group reference is plain, never text",
    doc([g("", [[{"ref": "tags"}, {"ref": ["tags", "001"]}]])]), "␞␅tags␟␅␂tags␟001␃")
enc("nested-map", "A map value is a level holding one keyed record, sorted",
    doc([g("", [["cfg", level([keyed(("b", "2"), ("a", "1"))])]])]),
    "␞cfg␟␐␞␁a␟1␁b␟2␘")
enc("nested-table-header", "A nested table with a header row",
    doc([g("", [[level([["1 Main", "Springfield"]], ["street", "city"])]])]),
    "␞␐␁␞street␟city␞1 Main␟Springfield␘")
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
can("text-escaped-seven", "DLE before one of the seven inside text: canonical",
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
can("comment", "A note is outside the hash: not part of a canonical unit",
    "␝g␇note␞a", True, False)
can("raw-lf-in-plain", "LF inside a plain value: malformed", "␞a␊b", False, False)
can("dle-mid-value", "DLE in the middle of a plain value: malformed", "␞a␐b", False, False)
can("dle-before-plain-in-text", "DLE before a byte that is not one of the seven: malformed",
    "␞␂a␐bc␃", False, False)
can("dangling-dle", "DLE at end of input: malformed", "␞␂a␐", False, False)
can("unassigned-code", "Bare unassigned control byte: malformed", "␞a␆b", False, False)
can("so-byte", "SO is permanently unassigned", "␞a␎b", False, False)
can("dle-before-plain", "DLE outside text must be followed by a code: malformed", "␞␐x␞a␘", False, False)
can("empty-level", "DLE CAN is the empty level: canonical", "␞␐␘", True, True)
can("text-reference", "A group reference written as text: not canonical", "␞␅␂tags␃", True, False)
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
inv("dle-before-us", "DLE must be followed by a structural code or CAN", "␞a␟␐␟b")
inv("dle-before-plain", "DLE followed by a plain byte outside text", "␞␐x␘")
inv("dle-before-plain-in-text", "DLE inside text before a byte that is not one of the seven", "␞␂a␐bc␃")
inv("dangling-dle", "DLE at end of input has nothing to escape", "␞␂a␐")
inv("text-unclosed", "Text open at end of input", "␞␂abc")
inv("stx-inside-text", "Text does not nest", "␞␂a␂b␃␃")
inv("text-spliced", "Text cannot be part of a plain value", "␞a␂b␃c")
inv("etx-unmatched", "ETX with no open text", "␞a␃")
inv("level-unclosed", "A level open at end of input", "␞␐␞a")
inv("can-unmatched", "CAN with no open level", "␞a␘")
inv("header-row-mid-group", "A header row is only the first item of a group", "␝g␞1␁␞x␞2")
inv("us-after-keyed-value", "US after a keyed value is a mixed record", "␞␁a␟1␟2")
inv("sub-outside-diff", "SUB has no meaning outside a diff", "␞a␚b")
inv("bytes-after-eot", "After EOT only layout, SYN or EM may follow", "␖␞a␄x")
inv("reference-empty-name", "A reference needs a name", "␞␅␟x")
inv("em-inside-level", "EM while a level is open", "␞␐␞a␙raw")
inv("em-inside-text", "EM cuts through text; raw EM inside text is an error for a document reader", "␞␂a␙b␃")
inv("bel-before-us", "BEL before US: US is not an element", "␞a␇␟b")
inv("bel-before-etb", "Framing cannot be commented out", "␞a␇␗")
inv("bel-before-can", "BEL before CAN", "␞␐␞a␇␘")
inv("text-after-can", "Text after CAN belongs to nothing", "␞␐␘x")
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
   "␞␐␞a␗␞b␗", 8, False, ["␞␐␞a", "␞b"], damaged=[0])
st("heading-committed", "The SYN heading is committed with the first ETB like anything else",
   "␖␁shape␟stream␗␞a␗", 18, False, ["␖␁shape␟stream", "␞a"], [["a"]])
st("header-row-committed", "A header row is committed like a record",
   "␁␞x␟y␗␞1␟2␗", 11, False, ["␁␞x␟y", "␞1␟2"], [["1", "2"]])
st("payload-in-committed-region", "ETB payload extends committed_end but is excluded from the block",
   "␞a␗sha256:00␞b␗", 15, False, ["␞a", "␞b"], [["a"], ["b"]])
st("torn-open-text", "A tail that leaves text open is torn", "␞a␗␞␂b", 3, True, ["␞a"], [["a"]])
st("torn-lone-dle", "A tail ending in a lone DLE is torn", "␞a␗␞␂b␐", 3, True, ["␞a"], [["a"]])
st("tail-only-layout", "A tail of layout alone is not torn", "␞a␗␊", 3, False, ["␞a"], [["a"]])
st("tail-eot", "EOT after the last commit closes the log and is not torn", "␞a␗␄", 3, False, ["␞a"], [["a"]])
st("tail-comment", "A comment after the last commit is not torn", "␞a␗␇bye", 3, False, ["␞a"], [["a"]])
st("empty-stream", "Empty buffer: no commits, not torn", "", 0, False, [])

# ----------------------------------------------------------------- nested
nested = []


def ne(name, desc, bytes_, record, canonical_=True):
    nested.append({"name": name, "desc": desc, "bytes": h(bytes_),
                   "record": record, "canonical": canonical_})


def lst(*items):
    return {"list": list(items)}


ne("three-items", "A list of three plain items between two scalar fields",
   "␞Alice␟␐␞Admin␟Editor␟User␘␟100", ["Alice", lst("Admin", "Editor", "User"), "100"])
ne("one-empty-item", "A level with one empty record is a list of one empty string",
   "␞a␟␐␞␘", ["a", lst("")])
ne("two-empty-items", "A lone US in the record yields two empty items",
   "␞a␟␐␞␟␘", ["a", lst("", "")])
ne("single-item", "One item, no separator", "␞a␟␐␞x␘", ["a", lst("x")])
ne("two-lists", "Adjacent list fields; CAN closes one before the next US",
   "␞a␟␐␞1␟2␘␟␐␞3␘", ["a", lst("1", "2"), lst("3")])
ne("text-item", "An item holding a control byte is text inside the level",
   "␞a␟␐␞␂x␟y␃␟z␘", ["a", lst("x\x1fy", "z")])
ne("binary-item", "A binary item is text; 0xFF is raw",
   "␞a␟␐␞␂␀\\xff␃␘", ["a", lst({"hex": "00ff"})])
ne("list-in-list", "A nested level inside an item is a nested list",
   "␞a␟␐␞␐␞x␟y␘␟z␘", ["a", lst(lst("x", "y"), "z")])
ne("map-item", "A keyed record inside a level is a map, not a list",
   "␞a␟␐␞␁k␟v␘", ["a", level([keyed(("k", "v"))])])
ne("table-not-a-list", "Two records in a level form a table; the list accessor rejects it",
   "␞a␟␐␞1␟2␞3␟4␘", ["a", level([["1", "2"], ["3", "4"]])])
ne("header-row-in-level", "A level with a header row is a named-column table",
   "␞a␟␐␁␞x␟y␞1␟2␘", ["a", level([["1", "2"]], ["x", "y"])])
ne("empty-level", "DLE CAN: an empty level, read as an empty list", "␞a␟␐␘", ["a", lst()])

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
   "␝cfg␞␁nested␟␐␞␁a␟1␁b␟2␘␁z␟26")
mc("text-value", "A value needing text is fenced; keys are names and never are",
   None, [["k", "a\nb"]], "␞␁k␟␂a␊b␃")

# ------------------------------------------------------------------- diff
# A small reference applier, so the expected outputs are computed from the
# rules in DIFF.md rather than typed by hand. It handles what the vectors
# use: SYN heading, FS/GS/RS/US/SUB, text with escapes, notes, layout.
SEVEN = {0x02, 0x03, 0x10, 0x17, 0x04, 0x16, 0x19}
LAYOUT = {0x09, 0x0A, 0x0D, 0x20}


class DiffError(Exception):
    pass


def _value(bs, i):
    """Read one value (plain or text) starting at i; return (bytes, next i)."""
    while i < len(bs) and bs[i] in LAYOUT:
        i += 1
    if i < len(bs) and bs[i] == 0x02:
        out = bytearray(); i += 1
        while True:
            if i >= len(bs):
                raise DiffError("text unclosed")
            x = bs[i]
            if x == 0x10:
                if i + 1 >= len(bs) or bs[i + 1] not in SEVEN:
                    raise DiffError("bad escape")
                out.append(bs[i + 1]); i += 2; continue
            if x == 0x03:
                i += 1; break
            if x in (0x17, 0x04, 0x16, 0x19):
                raise DiffError("framing inside text")
            out.append(x); i += 1
        while i < len(bs) and bs[i] in LAYOUT:
            i += 1
        if i < len(bs) and bs[i] >= 0x20:
            raise DiffError("text spliced")
        return bytes(out), i
    start = i
    while i < len(bs) and bs[i] >= 0x20:
        i += 1
    end = i
    while end > start and bs[end - 1] in LAYOUT:
        end -= 1
    val = bs[start:end]
    if any(c < 0x20 for c in val):
        raise DiffError("layout code inside plain value")
    return bytes(val), i


def _parse_diff(bs):
    """→ list of (path, [ops]); op = ("section", [units]) | ("replace", old, new);
    unit = (anchor_bytes, None) | (old, new)."""
    i = 0; files = []
    if i < len(bs) and bs[i] == 0x16:          # heading
        i += 1
        while True:
            while i < len(bs) and bs[i] in LAYOUT:
                i += 1
            if i < len(bs) and bs[i] == 0x01:
                k, i = _value(bs, i + 1)
                if i >= len(bs) or bs[i] != 0x1F:
                    raise DiffError("key without value")
                v, i = _value(bs, i + 1)
                if k == b"shape" and v != b"diff":
                    raise DiffError("shape is not diff")
            elif i < len(bs) and bs[i] == 0x07:
                _, i = _value(bs, i + 1)
            else:
                break
    cur = None
    while i < len(bs):
        x = bs[i]
        if x in LAYOUT:
            i += 1; continue
        if x == 0x07:                             # note or dead element
            j = i + 1
            while j < len(bs) and bs[j] in LAYOUT:
                j += 1
            if j < len(bs) and bs[j] < 0x20:
                dead_code = bs[j]
                # parse the dead element by recursion on a copy and drop it
                sub, k = _parse_one(bs, j)
                i = k; continue
            _, i = _value(bs, i + 1); continue
        if x == 0x04:
            i += 1; continue
        if x == 0x1C:
            path, i = _value(bs, i + 1)
            cur = (path.decode(), []); files.append(cur); continue
        if x in (0x1D, 0x1E):
            if cur is None:
                raise DiffError("section before any file")
            op, i = _parse_one(bs, i)
            cur[1].append(op); continue
        raise DiffError("unexpected byte %#x" % x)
    return files


def _parse_one(bs, i):
    x = bs[i]
    if x == 0x1D:
        units = []; i += 1
        while True:
            a, i = _value(bs, i)
            if i < len(bs) and bs[i] == 0x1A:
                b, i = _value(bs, i + 1)
                units.append((a, b))
            else:
                units.append((a, None))
            if i < len(bs) and bs[i] == 0x1F:
                i += 1; continue
            break
        return ("section", units), i
    if x == 0x1E:
        old, i = _value(bs, i + 1)
        if i >= len(bs) or bs[i] != 0x1A:
            raise DiffError("replace-all without SUB")
        new, i = _value(bs, i + 1)
        if not old:
            raise DiffError("replace-all with empty old")
        return ("replace", old, new), i
    if x == 0x1C:
        path, i = _value(bs, i + 1)
        return ("file", path), i
    raise DiffError("unexpected byte %#x" % x)


def _apply_file(data, ops):
    # pass 1: decide section matches on the original bytes
    cursor = 0; matches = []        # (start, end, replacement)
    pending_replaces = []           # replaces attached to section index (or -1 for whole file)
    sec_idx = -1
    for op in ops:
        if op[0] == "section":
            units = op[1]
            search = b"".join(a for a, _ in units)
            repl = b"".join(a if b is None else b for a, b in units)
            if not search:
                raise DiffError("empty search text")
            first = data.find(search, cursor)
            if first < 0:
                raise DiffError("pattern not found")
            if data.find(search, first + 1) >= 0:
                raise DiffError("pattern matched more than once")
            matches.append((first, first + len(search), repl))
            cursor = first + len(search); sec_idx += 1
        else:
            pending_replaces.append((sec_idx, op[1], op[2]))
    # scopes: from end of match i to start of match i+1 (or EOF); -1 → 0..start of match 0
    def scope(idx):
        lo = 0 if idx < 0 else matches[idx][1]
        hi = matches[idx + 1][0] if idx + 1 < len(matches) else len(data)
        return lo, hi
    # pass 2: build output from pieces: segments between matches get replace-alls
    pieces = []; pos = 0
    bounds = [(-1, 0, matches[0][0] if matches else len(data))]
    for k, (st, en, repl) in enumerate(matches):
        nxt = matches[k + 1][0] if k + 1 < len(matches) else len(data)
        bounds.append((k, en, nxt))
    out = bytearray()
    seg_text = {}
    for idx, lo, hi in bounds:
        seg = data[lo:hi]
        for sidx, old, new in pending_replaces:
            if sidx == idx:
                n = seg.count(old)
                if n == 0:
                    raise DiffError("replace-all found nothing")
                seg = seg.replace(old, new)
        seg_text[idx] = seg
    out += seg_text[-1]
    for k, (st, en, repl) in enumerate(matches):
        out += repl
        out += seg_text[k]
    return bytes(out)


def apply_diff(files, diff_bytes):
    parsed = _parse_diff(diff_bytes)
    result = dict(files)
    for path, ops in parsed:
        if path not in files:
            raise DiffError("no such file: " + path)
        result[path] = _apply_file(files[path], ops)
    return result


diffs = []


def df(name, desc, files, diff, expect=None, error=False):
    fb = {k: v.encode() for k, v in files.items()}
    try:
        got = apply_diff(fb, b(diff))
        if error:
            raise AssertionError(f"{name}: expected an error, got {got}")
    except DiffError as e:
        if not error:
            raise AssertionError(f"{name}: unexpected error {e}")
        diffs.append({"name": name, "desc": desc, "files": files, "diff": h(diff), "error": True})
        return
    if expect is not None:
        exp = {k: v.encode() for k, v in expect.items()}
        assert got == exp, f"{name}: got {got} expected {exp}"
    diffs.append({"name": name, "desc": desc, "files": files, "diff": h(diff),
                  "result": {k: v.decode() for k, v in got.items()}})


D = "␖␁shape␟diff"
df("simple", "One substitution with anchors on both sides",
   {"greeting.txt": "Hello world!"}, D + "␜greeting.txt␝␂Hello ␃␟world␚universe␟!␄",
   {"greeting.txt": "Hello universe!"})
df("anchor-before-only", "Anchor on one side is enough when it is unique",
   {"app.rb": "class App\n  def run\n  end\nend\n"},
   D + "␜app.rb␝␂class App\n  def ␃␟run␚start␄",
   {"app.rb": "class App\n  def start\n  end\nend\n"})
df("two-substitutions", "Several substitutions in one pattern",
   {"m.txt": "x = 10 + 5\n"}, D + "␜m.txt␝␂x = ␃␟10␚20␟␂ + ␃␟5␚15␄",
   {"m.txt": "x = 20 + 15\n"})
df("insertion", "An empty old part inserts",
   {"a.py": "import os\nprint(1)\n"}, D + "␜a.py␝␂import os␃␟␚␂\nimport sys␃␄",
   {"a.py": "import os\nimport sys\nprint(1)\n"})
df("deletion", "An empty new part deletes",
   {"a.txt": "keep # TODO remove\n"}, D + "␜a.txt␝␂ # TODO remove␃␚␄",
   {"a.txt": "keep\n"})
df("assertion", "A section with no substitution asserts and moves the cursor",
   {"a.txt": "one\ntwo\none\n"}, D + "␜a.txt␝two␝one␚uno␄",
   {"a.txt": "one\ntwo\nuno\n"})
df("sequential-sections", "Each section is searched after the previous match, so a later 'a' is unambiguous",
   {"a.txt": "a b\na c\n"}, D + "␜a.txt␝␂a b␃␚X␝a␚Z␄", {"a.txt": "X\nZ c\n"})
df("ambiguous-after-cursor", "Exactly once means once in the text after the cursor",
   {"a.txt": "a b a b\n"}, D + "␜a.txt␝a␚A␄", error=True)
df("anchor-mismatch", "An anchor that does not match byte for byte (here, extra indentation) refuses",
   {"c.cr": "def run\n  return 0\nend\n"},
   D + "␜c.cr␝␂  def run\n␃␟␂  return 0␃␚␂  return 1␃␄",
   error=True)
df("multiline-text-anchor-ok", "The anchor must match the file's bytes exactly",
   {"c.cr": "def run\n  return 0\nend\n"},
   D + "␜c.cr␝␂def run\n␃␟␂  return 0␃␚␂  return 1␃␄",
   {"c.cr": "def run\n  return 1\nend\n"})
df("replace-all-in-scope", "RS replaces every occurrence between this section's match and the next",
   {"t.rb": "count = 0\ndef tally(items)\n  count = 0\n  items.each { count += 1 }\n  count\nend\ncount\n"},
   D + "␜t.rb␝def tally(items)␞count␚total␝end␄",
   {"t.rb": "count = 0\ndef tally(items)\n  total = 0\n  items.each { total += 1 }\n  total\nend\ncount\n"})
df("replace-all-to-eof", "After the last section the scope runs to the end of the file",
   {"a.txt": "x\n--\nx x\n"}, D + "␜a.txt␝--␞x␚y␄", {"a.txt": "x\n--\ny y\n"})
df("replace-all-whole-file", "RS before any section applies to the whole file (up to the first match)",
   {"a.txt": "x x\n--\nx\n"}, D + "␜a.txt␞x␚y␝--␄", {"a.txt": "y y\n--\nx\n"})
df("replace-all-in-order", "Several RS lines apply in order",
   {"a.txt": "--\na a\n"}, D + "␜a.txt␝--␞a␚b␞b␚c␄", {"a.txt": "--\nc c\n"})
df("two-files", "Several files in one diff",
   {"a.txt": "foo\n", "b.txt": "bar\n"}, D + "␜a.txt␝foo␚FOO␜b.txt␝bar␚BAR␄",
   {"a.txt": "FOO\n", "b.txt": "BAR\n"})
df("note-and-dead-section", "A note is skipped; a dead section is parsed and ignored",
   {"a.txt": "foo bar\n"}, D + "␜a.txt␇ careful␝foo␚FOO␇␝bar␚BAR␄", {"a.txt": "FOO bar\n"})
df("no-match", "A pattern that matches nothing refuses the whole diff",
   {"a.txt": "foo\n", "b.txt": "bar\n"}, D + "␜a.txt␝foo␚FOO␜b.txt␝baz␚BAZ␄", error=True)
df("ambiguous", "A pattern that matches twice refuses",
   {"a.txt": "foo foo\n"}, D + "␜a.txt␝foo␚FOO␄", error=True)
df("replace-all-nothing", "A replace-all with zero occurrences refuses",
   {"a.txt": "--\nfoo\n"}, D + "␜a.txt␝--␞bar␚baz␄", error=True)
df("replace-all-empty-old", "A replace-all needs a non-empty old part",
   {"a.txt": "--\n"}, D + "␜a.txt␝--␞␚x␄", error=True)
df("wrong-shape", "A heading that contradicts the diff tool refuses",
   {"a.txt": "foo\n"}, "␖␁shape␟stream␜a.txt␝foo␚bar␄", error=True)
df("missing-file", "A path that does not exist refuses",
   {"a.txt": "foo\n"}, D + "␜b.txt␝foo␚bar␄", error=True)

# ------------------------------------------------------------------ write
for fname, cases in [("decode", decode), ("encode", encode),
                     ("canonical", canonical), ("invalid", invalid),
                     ("stream", stream), ("nested", nested),
                     ("map-canonical", mapc), ("diff", diffs)]:
    names = [c["name"] for c in cases]
    assert len(names) == len(set(names)), fname
    (OUT / f"{fname}.json").write_text(
        json.dumps({"version": 2, "cases": cases}, ensure_ascii=False, indent=2) + "\n")
    print(fname, len(cases))
