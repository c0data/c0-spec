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


def ref(groups=None, file=None):
    """A reference: a group name (str) or a pattern, reported as the level
    it is written as."""
    if isinstance(groups, str):
        return {"ref": groups}
    return {"ref": {"level": {"files": [{"name": file, "groups": groups}]}}}


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
    "␞a␟␅tags", [g("", [["a", ref("tags")]])])
dec("reference-path", "ENQ with a level is a pattern: group, record id, field name; reported as the level written",
    "␞a␟␅␐␝tags␞001␟label␘", [g("", [["a", ref([g("tags", [["001", "label"]])])]])])
dec("reference-record", "A pattern may stop at the record",
    "␞a␟␅␐␝tags␞001␘", [g("", [["a", ref([g("tags", [["001"]])])]])])
dec("reference-group-pattern", "A pattern that is a bare group is a group reference (legal, not canonical)",
    "␞a␟␅␐␝tags␘", [g("", [["a", ref([g("tags", [])])]])])
dec("reference-file", "A file line in a pattern names the file",
    "␞a␟␅␐␜b␝tags␞001␘", [g("", [["a", ref([g("tags", [["001"]])], "b")]])])
dec("reference-depth", "GS repetition in a pattern is depth, as in the document",
    "␞a␟␅␐␝docs␝␝intro␞3␘",
    [g("", [["a", ref([{"name": "docs", "headers": None, "records": [],
                        "sections": [{"name": "intro", "headers": None, "records": [["3"]]}]}])]])])
dec("reference-keyed-unit", "A keyed unit is named by a keyed unit with an empty value",
    "␞a␟␅␐␝server␞␁host␟␘", [g("", [["a", ref([g("server", [keyed(("host", ""))])])]])])
dec("reference-into-level", "A level in the third unit continues the pattern into the field's level",
    "␞a␟␅␐␝tags␞001␟children␟␐␞2␘␘",
    [g("", [["a", ref([g("tags", [["001", "children", level([["2"]])]])])]])])
dec("reference-note-inside", "A note inside a pattern is a note, not a step",
    "␞a␟␅␐␝tags␇why␞001␘", [g("", [["a", ref([g("tags", [["001"]])])]])])
dec("supersede-unit", "SUB before US: the unit before is superseded by the unit after; a document model reports the result",
    "␞a␟b␚␟c", [g("", [["a", "c"]])])
dec("supersede-deletion", "An empty superseding unit deletes: the result keeps the empty unit",
    "␞old␚␟␞end", [g("", [[""], ["end"]])])
dec("supersede-insertion", "The empty first unit superseded by a value: an insertion",
    "␞␚␟new", [g("", [["new"]])])
dec("supersede-middle", "Arity counts the result: the superseded unit is not counted",
    "␞a␟b␚␟␟c", [g("", [["a", "", "c"]])])
dec("supersede-chain", "Supersessions chain; the last stands",
    "␞a␚␟b␚␟c", [g("", [["c"]])])
dec("supersede-record", "SUB before RS: the record before is superseded by the record after",
    "␞a␟b␚␞a␟c", [g("", [["a", "c"]])])
dec("supersede-keyed-unit", "SUB before SOH: the keyed unit before is superseded",
    "␞␁k␟v␚␁k␟w", [g("", [keyed(("k", "w"))])])
dec("supersede-group", "SUB before GS: the group before, at that depth, is superseded",
    "␝g␞x␚␝g␞y", [g("g", [["y"]])])
dec("supersede-file", "SUB before FS: the file before is superseded",
    "␜f␝g␞x␚␜f␝g␞y", [g("g", [["y"]])], file="f",
    files=[{"name": "f", "groups": [g("g", [["y"]])]}])
dec("supersede-in-heading", "Supersession is legal in the heading too",
    "␖␁schema␟a␚␁schema␟b␞x", [g("", [["x"]])], heading=[["schema", "b"]])
dec("gs-depth", "GS repetition is depth; subsections belong to the group",
    "␝c1␞p1␝␝s1␞p2␝c2␞p3",
    [{"name": "c1", "headers": None, "records": [["p1"]],
      "sections": [{"name": "s1", "headers": None, "records": [["p2"]]}]},
     g("c2", [["p3"]])])
dec("header-not-inherited", "A header row names its own group's fields; a subsection inherits nothing",
    "␝c␁␞a␟b␞1␟2␝␝s␞3␟4",
    [{"name": "c", "headers": ["a", "b"], "records": [["1", "2"]],
      "sections": [{"name": "s", "headers": None, "records": [["3", "4"]]}]}])
dec("gs-depth-skipped", "A skipped depth is reported as nothing: c is at depth three, no group at depth two",
    "␝a␝␝␝c␞1",
    [{"name": "a", "headers": None, "records": [],
      "sections": [{"name": None, "headers": None, "records": [],
                    "sections": [{"name": "c", "headers": None, "records": [["1"]]}]}]}])
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
    "␖␁schema␟ledger␁version␟1␞a␟b",
    [g("", [["a", "b"]])], heading=[["schema", "ledger"], ["version", "1"]])
dec("header-row-note", "A header row is a record of names and admits notes like any record",
    "␁␞a␇n␟b␞1␟2", [g("", [["1", "2"]], ["a", "b"])])
dec("heading-duplicate-key", "Duplicate heading keys are reported as written (a reader takes the last, with a loud warning)",
    "␖␁schema␟a␁schema␟b␞x", [g("", [["x"]])], heading=[["schema", "a"], ["schema", "b"]])
dec("heading-schema-record", "schema may be a level holding one keyed record of name, url and hash",
    "␖␁schema␟␐␞␁name␟ledger␁url␟https://example.org/ledger/1␁hash␟sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08␘␞a",
    [g("", [["a"]])], heading=[["schema", level([keyed(("name", "ledger"), ("url", "https://example.org/ledger/1"), ("hash", "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"))])]])
dec("heading-schema-pinned", "url and hash: fetchable and pinned",
    "␖␁schema␟␐␞␁url␟https://example.org/ledger/1␁hash␟sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08␘␞a",
    [g("", [["a"]])], heading=[["schema", level([keyed(("url", "https://example.org/ledger/1"), ("hash", "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"))])]])
dec("heading-schema-hash-only", "A hash alone is a content-addressed schema",
    "␖␁schema␟␐␞␁hash␟sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08␘␞a",
    [g("", [["a"]])], heading=[["schema", level([keyed(("hash", "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"))])]])
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
dec("comment-dead-group", "A dead group takes its records with it",
    "␝g1␞1␇␝g2␞2", [g("g1", [["1"]])])
dec("comment-dead-group-with-header", "A dead group takes its header row and records; the next live group is unaffected",
    "␝g1␞1␇␝g2␁␞x␞2␝g3␞4", [g("g1", [["1"]]), g("g3", [["4"]])])
dec("comment-dead-group-subsections", "A dead group ends where a live one would, so its deeper subsections die with it",
    "␝g1␞1␇␝g2␞2␝␝s␞3␝g3␞4", [g("g1", [["1"]]), g("g3", [["4"]])])
dec("comment-label-in-note", "A group line inside a text note is gone and its records fall through to the group before",
    "␝g1␞1␇␂␝g2␃␞2", [g("g1", [["1"], ["2"]])])
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
dec("comment-dead-file", "A dead file takes its groups and records with it, up to the next FS or the end",
    "␜a␝x␞1␇␜b␞2␝y␞3",
    [g("x", [["1"]])], file="a",
    files=[{"name": "a", "groups": [g("x", [["1"]])]}])
dec("comment-dead-file-then-live", "A dead file ends at the next file line",
    "␜a␝x␞1␇␜b␞2␜c␝y␞3",
    [g("x", [["1"]])], file="a",
    files=[{"name": "a", "groups": [g("x", [["1"]])]}, {"name": "c", "groups": [g("y", [["3"]])]}])
dec("comment-note-after-value", "A note after a value is skipped and is not a unit",
    "␞a␇n␟b", [g("", [["a", "b"]])])
dec("comment-notes-after-text", "Notes may follow a text value, in a positional or a keyed unit; several notes are still one unit",
    "␞␂a b␃␇n1␇n2␟c␞␁k␟␂v␃␇n",
    [g("", [["a b", "c"], keyed(("k", "v"))])])
dec("comment-all-keyed-units-dead", "A keyed record whose units are all dead is an empty map",
    "␞␇␁k␟v␞x", [g("", [keyed(), ["x"]])])
dec("comment-note-only-record", "A record holding nothing but a note is positional: one empty unit (a record is keyed only by a keyed unit, live or dead)",
    "␞␇n␞x", [g("", [[""], ["x"]])])
dec("comment-dead-header-then-live", "A dead header row does not take the header slot",
    "␝g␇␁␞x␟y␁␞p␟q␞1␟2", [g("g", [["1", "2"]], ["p", "q"])])
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
enc("keyed-record-order", "A map encodes as a keyed record with entries in the order given",
    doc([g("", [keyed(("port", "5432"), ("host", "localhost"))])]),
    "␞␁port␟5432␁host␟localhost")
enc("keyed-not-sorted", "An encoder never sorts keys: 'b' before 'a' stays so",
    doc([g("", [keyed(("b", "1"), ("a", "2"))])]), "␞␁b␟1␁a␟2")
enc("nested-list", "A list is a level holding one record",
    doc([g("", [["Alice", level([["Admin", "Editor"]])]])]),
    "␞Alice␟␐␞Admin␟Editor␘")
enc("nested-empty", "An empty list is an empty level", doc([g("", [[level([])]])]), "␞␐␘")
enc("nested-one-empty", "A list of one empty string is a level with one empty record",
    doc([g("", [[level([[""]])]])]), "␞␐␞␘")
enc("nested-empty-level", "An empty level is DLE CAN", doc([g("", [[level([]), "x"]])]), "␞␐␘␟x")
enc("reference-plain", "A group reference is plain; a path is a level pattern",
    doc([g("", [[ref("tags"), ref([g("tags", [["001"]])])]])]), "␞␅tags␟␅␐␝tags␞001␘")
enc("nested-map", "A map value is a level holding one keyed record, order kept",
    doc([g("", [["cfg", level([keyed(("b", "2"), ("a", "1"))])]])]),
    "␞cfg␟␐␞␁b␟2␁a␟1␘")
enc("nested-table-header", "A nested table with a header row",
    doc([g("", [[level([["1 Main", "Springfield"]], ["street", "city"])]])]),
    "␞␐␁␞street␟city␞1 Main␟Springfield␘")
enc("file-two-groups", "Document with FS name and two groups; the canonical unit has no framing",
    doc([g("g1", [["a"]]), g("g2", [["b"]], ["x"])], file="db"),
    "␜db␝g1␞a␝g2␁␞x␞b")
enc("heading-written", "With a heading the file is SYN, heading as given, body, EOT; the canonical unit is the body",
    doc([g("g", [["a"]])], heading=[["version", "1"], ["schema", "ledger"]]),
    "␝g␞a", bytes_="␖␁version␟1␁schema␟ledger␝g␞a␄")

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
can("note-between-gs", "A note between two GS: two groups at depth one, well-formed, not canonical; stripping the note would read as depth two, so a canonicaliser refuses rather than change depth",
    "␝␇n␝b␞x", True, False)
can("keyed-unique", "Keyed record with unique keys", "␞␁a␟1␁b␟2", True, True)
can("keyed-any-order", "Key order is data, not a canonicality question", "␞␁b␟1␁a␟2", True, True)
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
can("supersession-kept", "Supersession is content: kept and canonical", "␞a␚␟b", True, True)
can("supersession-side-spelling", "Each side of a supersession is in its one spelling: text around plain is not canonical", "␞␂a␃␚␟b", True, False)
can("group-reference-pattern", "A group reference written as a pattern: not canonical", "␞␅␐␝tags␘", True, False)
can("reference-pattern", "A pattern with a record is canonical", "␞␅␐␝tags␞001␘", True, True)
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
inv("dead-header-row-mid-group", "A dead header row is parsed as if live, so out of place it is the same error", "␝g␞1␇␁␞x␞2")
inv("two-header-rows", "A group has one header row", "␝g␁␞a␞1␁␞b␞2")
inv("us-after-keyed-value", "US after a keyed value is a mixed record", "␞␁a␟1␟2")
inv("sub-before-value", "SUB qualifies the separator after it; before a value it matches nothing", "␞a␚b")
inv("sub-before-text", "SUB before STX is an error", "␞a␚␂b␃")
inv("sub-at-eof", "SUB at the end of input has nothing to qualify", "␞a␚")
inv("sub-before-bel", "SUB next to BEL is an error", "␞a␟b␚␇␞c")
inv("bel-before-sub", "BEL before SUB is an error: SUB is not an element", "␞a␇␚␟b")
inv("sub-record-nothing-before", "A record supersession needs a record before it in the group", "␝g␚␞x")
inv("sub-group-nothing-before", "A group supersession needs an earlier group at that depth", "␚␝g␞x")
inv("sub-file-nothing-before", "A file supersession needs an earlier file", "␚␜f␞x")
inv("sub-first-keyed-unit", "The first keyed unit of a record has nothing to supersede", "␞␚␁k␟v")
inv("bytes-after-eot", "After EOT only layout, SYN or EM may follow", "␖␞a␄x")
inv("heading-schema-positional", "A schema level holds a keyed record, not a positional one", "␖␁schema␟␐␞a␟b␘␞x")
inv("heading-schema-two-records", "A schema level holds one record", "␖␁schema␟␐␞␁name␟a␞␁name␟b␘␞x")
inv("heading-schema-unknown-key", "A schema record's keys are name, url and hash", "␖␁schema␟␐␞␁name␟a␁version␟1␘␞x")
inv("heading-schema-empty", "schema needs a value", "␖␁schema␟␞x")
inv("reference-empty-name", "A reference needs a name", "␞␅␟x")
inv("reference-text", "ENQ followed by text is an error: every step of a path is a plain name", "␞␅␂tags␟001␃")
inv("reference-step-not-name", "Every step of a pattern is a name: no edge whitespace, no control bytes", "␞␅␐␝tags␞␂ b␃␘")
inv("reference-empty-pattern", "An empty level is not a reference", "␞␅␐␘")
inv("reference-no-group", "A pattern begins with a file or group line", "␞␅␐␞001␘")
inv("reference-two-records", "A pattern is one branch: two records at one depth", "␞␅␐␝tags␞001␞002␘")
inv("reference-two-groups", "A pattern is one branch: two groups at one depth", "␞␅␐␝a␝b␘")
inv("reference-group-after-record", "Nothing follows the record in a pattern", "␞␅␐␝a␞1␝b␘")
inv("reference-four-units", "A pattern record holds at most id, field name and a level", "␞␅␐␝a␞1␟b␟c␟d␘")
inv("reference-third-unit-not-level", "The third unit of a pattern record is a level", "␞␅␐␝a␞1␟b␟c␘")
inv("reference-keyed-with-value", "A keyed unit in a pattern has no value", "␞␅␐␝s␞␁host␟x␘")
inv("reference-two-keyed-units", "A keyed record in a pattern holds one keyed unit", "␞␅␐␝s␞␁a␟␁b␟␘")
inv("reference-header-row", "A header row is not a step", "␞␅␐␝a␁␞x␞1␘")
inv("reference-dead-step", "A dead element is not a step", "␞␅␐␝a␇␞1␘")
inv("em-inside-level", "EM while a level is open", "␞␐␞a␙raw")
inv("em-inside-text", "EM cuts through text; raw EM inside text is an error for a document reader", "␞␂a␙b␃")
inv("bel-before-us", "BEL before US: US is not an element", "␞a␇␟b")
inv("bel-before-etb", "Framing cannot be commented out", "␞a␇␗")
inv("bel-before-can", "BEL before CAN", "␞␐␞a␇␘")
inv("bel-before-enq", "A reference is not an element", "␞a␟␇␅tags")
inv("bel-before-bel", "BEL is not an element", "␇␇␞x")
inv("bel-at-end", "A note needs content", "␞a␇")
inv("second-document-without-syn", "After EOT only SYN, EM or layout may follow", "␖␞a␄␞b")
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
st("malformed-block-damaged", "Any error inside a committed block damages that block alone; its bounds come from the ETB",
   "␞a␗␞b␟␇␅tags␗␞c␗", 16, False, ["␞a", "␞b␟␇␅tags", "␞c"], [["a"], ["c"]], damaged=[1])
st("late-header-row-damaged", "A header row after records is an error, so its block is damaged",
   "␞a␗␁␞x␗␞b␗", 10, False, ["␞a", "␁␞x", "␞b"], [["a"], ["b"]], damaged=[1])
st("batch-block-damaged", "A batch with one bad record is one damaged block: its sound records are not delivered",
   "␞a␞b␟␇␅t␗␞c␗", 12, False, ["␞a␞b␟␇␅t", "␞c"], [["c"]], damaged=[0])
st("payload-then-text-damaged", "What follows a payload begins the next block; text with no record there is an error, so that block is damaged",
   "␞a␗p␂x␃␗␞b␗", 11, False, ["␞a", "␂x␃", "␞b"], [["a"], ["b"]], damaged=[1])
st("heading-committed", "The SYN heading is committed with the first ETB like anything else",
   "␖␁shape␟stream␗␞a␗", 18, False, ["␖␁shape␟stream", "␞a"], [["a"]])
st("header-row-committed", "A header row is committed like a record",
   "␁␞x␟y␗␞1␟2␗", 11, False, ["␁␞x␟y", "␞1␟2"], [["1", "2"]])
st("payload-in-committed-region", "ETB payload extends committed_end but is excluded from the block",
   "␞a␗sha256:00␞b␗", 15, False, ["␞a", "␞b"], [["a"], ["b"]])
st("torn-open-text", "A tail that leaves text open is torn", "␞a␗␞␂b", 3, True, ["␞a"], [["a"]])
st("torn-lone-dle", "A tail ending in a lone DLE is torn", "␞a␗␞␂b␐", 3, True, ["␞a"], [["a"]])
st("em-tail-not-torn", "EM after the last commit opens the raw region, which is not data of the log: not torn", "␞a␗␙raw", 3, False, ["␞a"], [["a"]])
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

# ------------------------------------------------------------------- diff
# A small reference applier, so the expected outputs are computed from the
# rules in DIFF.md rather than typed by hand. It parses the base grammar as
# far as a diff may use it (SYN heading, FS, RS, US, SUB US, text, notes,
# commits, EOT) and refuses everything DIFF.md lists under "What a diff may
# not hold".
SEVEN = {0x02, 0x03, 0x10, 0x17, 0x04, 0x16, 0x19}
LAYOUT = {0x09, 0x0A, 0x0D, 0x20}


class DiffError(Exception):
    pass


def _skip_layout(bs, i):
    while i < len(bs) and bs[i] in LAYOUT:
        i += 1
    return i


def _value(bs, i):
    """Read one value (plain or text) starting at i; return (bytes, next i).
    An empty value is allowed (nothing before the next code)."""
    i = _skip_layout(bs, i)
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
        i = _skip_layout(bs, i)
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


def _name(bs, i):
    i = _skip_layout(bs, i)
    if i < len(bs) and bs[i] == 0x02:
        raise DiffError("a name cannot be text")
    return _value(bs, i)


def _skip_notes(bs, i):
    """Skip notes (BEL + value). A BEL before a code is a dead marker: an error in a diff."""
    while True:
        j = _skip_layout(bs, i)
        if j < len(bs) and bs[j] == 0x07:
            k = _skip_layout(bs, j + 1)
            if k >= len(bs):
                raise DiffError("BEL at end of input")
            if bs[k] >= 0x20 or bs[k] == 0x02:
                _, i = _value(bs, k); continue
            raise DiffError("dead element in a diff")
        return i


def _parse_heading(bs, i):
    """After SYN. Returns next i. Checks shape; tolerates dead keys and notes."""
    while True:
        i = _skip_layout(bs, i)
        if i < len(bs) and bs[i] == 0x01:
            k, i = _name(bs, i + 1)
            if i >= len(bs) or bs[i] != 0x1F:
                raise DiffError("key without value")
            v, i = _value(bs, i + 1)
            if k == b"shape" and v != b"diff":
                raise DiffError("shape is not diff")
        elif i < len(bs) and bs[i] == 0x07:
            j = _skip_layout(bs, i + 1)
            if j < len(bs) and bs[j] == 0x01:          # dead heading key
                _, j = _name(bs, j + 1)
                if j >= len(bs) or bs[j] != 0x1F:
                    raise DiffError("key without value")
                _, i = _value(bs, j + 1)
            elif j < len(bs) and bs[j] < 0x20 and bs[j] != 0x02:
                return i                                 # dead body element: body's business
            else:
                _, i = _value(bs, j)
        else:
            return i


def _parse_record(bs, i):
    """After RS. Returns ([(search_part, repl_part)], next i). A unit is
    (a, a) for an anchor and (old, new) for a substitution."""
    units = []
    prev_sub = False
    while True:
        a, i = _value(bs, i)
        i = _skip_notes(bs, i)
        if i < len(bs) and bs[i] in (0x01, 0x05, 0x10):
            raise DiffError("keyed unit, reference or level in a diff record")
        if i < len(bs) and bs[i] == 0x1A:               # supersession
            j = _skip_layout(bs, i + 1)
            if j >= len(bs):
                raise DiffError("SUB at end of input")
            if bs[j] != 0x1F:
                raise DiffError("supersession at a grain other than the unit")
            if prev_sub:
                raise DiffError("chained supersession")
            new, i = _value(bs, j + 1)
            i = _skip_notes(bs, i)
            if i < len(bs) and bs[i] in (0x01, 0x05, 0x10):
                raise DiffError("keyed unit, reference or level in a diff record")
            if i < len(bs) and bs[i] == 0x1A:
                j = _skip_layout(bs, i + 1)
                if j < len(bs) and bs[j] == 0x1F:
                    raise DiffError("chained supersession")
            if not a and not new:
                raise DiffError("substitution of nothing by nothing")
            units.append((a, new)); prev_sub = True
        else:
            units.append((a, a)); prev_sub = False
        if i < len(bs) and bs[i] == 0x1F:
            i += 1; continue
        break
    return units, i


def _parse_diff(bs):
    """→ list of (path, [record]); record = [(search_part, repl_part)]."""
    i = _skip_layout(bs, 0)
    if i < len(bs) and bs[i] == 0x16:
        i = _parse_heading(bs, i + 1)
    cur = None; files = []
    while i < len(bs):
        x = bs[i]
        if x in LAYOUT:
            i += 1; continue
        if x == 0x07:
            i = _skip_notes(bs, i); continue
        if x == 0x04:
            i = _skip_layout(bs, i + 1)
            if i < len(bs) and bs[i] not in (0x16, 0x19):
                raise DiffError("bytes after EOT")
            break
        if x == 0x17:                                   # commit: tolerated
            i = _skip_layout(bs, i + 1)
            while i < len(bs) and bs[i] >= 0x20:
                i += 1
            continue
        if x == 0x1A:                                   # SUB before FS/GS/RS/SOH
            raise DiffError("supersession at a grain other than the unit")
        if x == 0x1C:
            path, i = _name(bs, i + 1)
            if not path:
                raise DiffError("empty path")
            if any(f[0] == path.decode() for f in files):
                raise DiffError("same path twice")
            cur = (path.decode(), []); files.append(cur); continue
        if x == 0x1D:
            raise DiffError("GS in a diff")
        if x == 0x01:
            raise DiffError("header row or keyed unit in a diff")
        if x == 0x1E:
            if cur is None:
                raise DiffError("record before any file")
            units, i = _parse_record(bs, i + 1)
            cur[1].append(units); continue
        raise DiffError("unexpected byte %#x" % x)
    return files


def _apply_file(data, records):
    cursor = 0; matches = []
    for units in records:
        search = b"".join(a for a, _ in units)
        repl = b"".join(n for _, n in units)
        if not search:
            raise DiffError("empty search text")
        first = data.find(search, cursor)
        if first < 0:
            raise DiffError("pattern not found")
        if data.find(search, first + 1) >= 0:
            raise DiffError("pattern matched more than once")
        matches.append((first, first + len(search), repl))
        cursor = first + len(search)
    out = bytearray(); pos = 0
    for st, en, repl in matches:
        out += data[pos:st]; out += repl; pos = en
    out += data[pos:]
    return bytes(out)


def apply_diff(files, diff_bytes):
    parsed = _parse_diff(diff_bytes)
    result = dict(files)
    for path, records in parsed:
        if path not in files:
            raise DiffError("no such file: " + path)
        result[path] = _apply_file(files[path], records)
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
   {"greeting.txt": "Hello world!"}, D + "␜greeting.txt␞␂Hello ␃␟world␚␟universe␟!␄",
   {"greeting.txt": "Hello universe!"})
df("anchor-before-only", "Anchor on one side is enough when it is unique",
   {"app.rb": "class App\n  def run\n  end\nend\n"},
   D + "␜app.rb␞␂class App\n  def ␃␟run␚␟start␄",
   {"app.rb": "class App\n  def start\n  end\nend\n"})
df("two-substitutions", "Several substitutions in one record",
   {"m.txt": "x = 10 + 5\n"}, D + "␜m.txt␞␂x = ␃␟10␚␟20␟␂ + ␃␟5␚␟15␄",
   {"m.txt": "x = 20 + 15\n"})
df("insertion", "An empty old inserts after its anchor",
   {"a.py": "import os\nprint(1)\n"}, D + "␜a.py␞␂import os␃␟␚␟␂\nimport sys␃␄",
   {"a.py": "import os\nimport sys\nprint(1)\n"})
df("deletion", "An empty new deletes",
   {"a.txt": "keep # TODO remove\n"}, D + "␜a.txt␞␂ # TODO remove␃␚␟␄",
   {"a.txt": "keep\n"})
df("assertion", "A record with no substitution asserts and moves the cursor",
   {"a.txt": "one\ntwo\none\n"}, D + "␜a.txt␞two␞one␚␟uno␄",
   {"a.txt": "one\ntwo\nuno\n"})
df("sequential-records", "Each record is searched after the previous match, so a later 'a' is unambiguous",
   {"a.txt": "a b\na c\n"}, D + "␜a.txt␞␂a b␃␚␟X␞a␚␟Z␄", {"a.txt": "X\nZ c\n"})
df("ambiguous-after-cursor", "Exactly once means once in the text after the cursor",
   {"a.txt": "a b a b\n"}, D + "␜a.txt␞a␚␟A␄", error=True)
df("anchor-mismatch", "An anchor that does not match byte for byte (here, extra indentation) refuses",
   {"c.cr": "def run\n  return 0\nend\n"},
   D + "␜c.cr␞␂  def run\n␃␟␂  return 0␃␚␟␂  return 1␃␄",
   error=True)
df("multiline-text-anchor-ok", "The anchor must match the file's bytes exactly",
   {"c.cr": "def run\n  return 0\nend\n"},
   D + "␜c.cr␞␂def run\n␃␟␂  return 0␃␚␟␂  return 1␃␄",
   {"c.cr": "def run\n  return 1\nend\n"})
df("expanded-replace-all", "Replace-all is written out: one anchored record per occurrence, in order",
   {"t.rb": "count = 0\ndef tally(items)\n  count = 0\n  items.each { count += 1 }\n  count\nend\ncount\n"},
   D + "␜t.rb␞def tally(items)␞␂  ␃␟count␚␟total␟␂ = 0␃␞␂{ ␃␟count␚␟total␟␂ +=␃␞␂  ␃␟count␚␟total␟␂\nend␃␄",
   {"t.rb": "count = 0\ndef tally(items)\n  total = 0\n  items.each { total += 1 }\n  total\nend\ncount\n"})
df("two-files", "Several files in one diff",
   {"a.txt": "foo\n", "b.txt": "bar\n"}, D + "␜a.txt␞foo␚␟FOO␜b.txt␞bar␚␟BAR␄",
   {"a.txt": "FOO\n", "b.txt": "BAR\n"})
df("note-between-records", "A note between records is skipped",
   {"a.txt": "foo bar\n"}, D + "␜a.txt␇ careful␞foo␚␟FOO␄", {"a.txt": "FOO bar\n"})
df("note-holds-hunk", "A hunk kept without applying is written inside a text note",
   {"a.txt": "foo bar\n"}, D + "␜a.txt␞foo␚␟FOO␇␂␞bar␚␟BAR␃␄", {"a.txt": "FOO bar\n"})
df("no-match", "A pattern that matches nothing refuses the whole diff",
   {"a.txt": "foo\n", "b.txt": "bar\n"}, D + "␜a.txt␞foo␚␟FOO␜b.txt␞baz␚␟BAZ␄", error=True)
df("ambiguous", "A pattern that matches twice refuses",
   {"a.txt": "foo foo\n"}, D + "␜a.txt␞foo␚␟FOO␄", error=True)
df("bare-insertion", "An insertion needs an anchor: empty search text refuses",
   {"a.txt": "--\n"}, D + "␜a.txt␞␚␟x␄", error=True)
df("empty-record", "An empty record has empty search text and refuses",
   {"a.txt": "--\n"}, D + "␜a.txt␞␄", error=True)
df("empty-substitution", "A substitution of nothing by nothing refuses",
   {"a.txt": "ab\n"}, D + "␜a.txt␞a␟␚␟␟b␄", error=True)
df("wrong-shape", "A heading that contradicts the diff tool refuses",
   {"a.txt": "foo\n"}, "␖␁shape␟stream␜a.txt␞foo␚␟bar␄", error=True)
df("dead-record-refused", "A dead record is an error in a diff: what is written applies",
   {"a.txt": "foo bar\n"}, D + "␜a.txt␞foo␚␟FOO␇␞bar␚␟BAR␄", error=True)
df("dead-file-line-refused", "A dead file line is an error in a diff",
   {"a.txt": "foo baz\n"}, D + "␜a.txt␞foo␚␟FOO␇␜b.txt␞baz␚␟BAZ␄", error=True)
df("text-note-in-body", "A text note between records is skipped",
   {"a.txt": "foo\n"}, D + "␜a.txt␇␂note ␞ with codes␃␞foo␚␟bar␄", {"a.txt": "bar\n"})
df("note-in-pattern", "A note after a unit is not a unit",
   {"a.txt": "ab\n"}, D + "␜a.txt␞a␇n␟b␚␟c␄", {"a.txt": "ac\n"})
df("note-after-substitution", "A note after a superseding unit is a note",
   {"a.txt": "ab\n"}, D + "␜a.txt␞a␟b␚␟c␇n␄", {"a.txt": "ac\n"})
df("commit-tolerated", "An ETB between records is a no-op",
   {"a.txt": "foo\n"}, D + "␜a.txt␞foo␚␟bar␗␄", {"a.txt": "bar\n"})
df("overlapping-ambiguous", "Matches are counted at every position: aa occurs twice in aaa",
   {"a.txt": "aaa\n"}, D + "␜a.txt␞aa␚␟b␄", error=True)
df("same-path-twice", "The same path twice in one diff refuses",
   {"a.txt": "foo bar\n"}, D + "␜a.txt␞foo␚␟FOO␜a.txt␞bar␚␟BAR␄", error=True)
df("bytes-after-eot", "Bytes after EOT refuse",
   {"a.txt": "foo bar\n"}, D + "␜a.txt␞foo␚␟FOO␄␞bar␚␟BAR", error=True)
df("text-path", "A path is a name, never text",
   {"a.txt": "foo\n"}, D + "␜␂a.txt␃␞foo␚␟bar␄", error=True)
df("empty-path", "A path is never empty",
   {"a.txt": "foo\n"}, D + "␜␞foo␚␟bar␄", error=True)
df("dead-heading-key", "A dead heading key is ignored; the FS after it is live",
   {"a.txt": "foo\n"}, "␖␁shape␟diff␇␁x␟y␜a.txt␞foo␚␟bar␄", {"a.txt": "bar\n"})
df("missing-file", "A path that does not exist refuses",
   {"a.txt": "foo\n"}, D + "␜b.txt␞foo␚␟bar␄", error=True)
df("record-before-file", "A record before the first FS refuses",
   {"a.txt": "foo\n"}, D + "␞foo␚␟bar␜a.txt␄", error=True)
df("gs-refused", "GS has no meaning in a diff and refuses",
   {"a.txt": "foo\n"}, D + "␜a.txt␝s␞foo␚␟bar␄", error=True)
df("header-row-refused", "A header row refuses",
   {"a.txt": "foo\n"}, D + "␜a.txt␁␞x␞foo␚␟bar␄", error=True)
df("keyed-unit-refused", "A keyed unit refuses",
   {"a.txt": "foo\n"}, D + "␜a.txt␞␁k␟foo␚␁k␟bar␄", error=True)
df("level-refused", "A level refuses",
   {"a.txt": "foo\n"}, D + "␜a.txt␞␐␞foo␘␚␟bar␄", error=True)
df("reference-refused", "A reference refuses",
   {"a.txt": "foo\n"}, D + "␜a.txt␞␅foo␚␟bar␄", error=True)
df("chained-supersession-refused", "A chained supersession refuses: the file never held the middle",
   {"a.txt": "foo\n"}, D + "␜a.txt␞foo␚␟bar␚␟baz␄", error=True)
df("record-grain-refused", "Supersession at the record grain is reserved and refuses",
   {"a.txt": "foo\n"}, D + "␜a.txt␞foo␚␞bar␄", error=True)

# ------------------------------------------------------------------ write
for fname, cases in [("decode", decode), ("encode", encode),
                     ("canonical", canonical), ("invalid", invalid),
                     ("stream", stream), ("nested", nested), ("diff", diffs)]:
    names = [c["name"] for c in cases]
    assert len(names) == len(set(names)), fname
    (OUT / f"{fname}.json").write_text(
        json.dumps({"version": 2, "cases": cases}, ensure_ascii=False, indent=2) + "\n")
    print(fname, len(cases))
