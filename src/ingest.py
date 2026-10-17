"""PDF -> sections with IDs -> chunks -> embeddings -> Chroma.

    python -m src.ingest              # rebuild the whole index (data/index/, git-ignored)
    python -m src.ingest --no-embed   # parse only: write sections + definitions, print samples

Outputs: sections.jsonl (one whole section per line), definitions.json ({policy: {term: section_id}})
and the Chroma collection of chunks. Deterministic: same PDFs and code give the same index on
every machine. Prints random sample sections per policy so a human can check the parsing.

Each policy has its own parse function (layouts differ); everything else is shared.
"""
import argparse
import json
import random
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf
import yaml

from src.store import CHROMA_DIR, COLLECTION, DEFINITIONS_PATH, EMBED_MODEL, INDEX_DIR, SECTIONS_PATH

ROOT = Path(__file__).resolve().parents[1]
POLICY_DIR = ROOT / "data" / "policies"
TABLES_PATH = POLICY_DIR / "table_transcriptions.yaml"

CHUNK_IF_OVER = 500   # sections up to this many words stay one chunk
CHUNK_WORDS = 400     # otherwise pack paragraphs into chunks of about this size
OVERLAP_WORDS = 50    # carry up to this many words of trailing paragraphs into the next chunk


# ---------------------------------------------------------------- shared helpers

@dataclass
class Line:
    page: int
    x0: float
    y0: float
    x1: float
    y1: float
    size: float
    font: str
    color: int
    text: str
    kind: str = "text"   # "table" for inserted transcriptions
    all_bold: bool = False


@dataclass
class Section:
    policy: str
    title: str
    level: str                       # "chapter" | "h12" | "h10" | "definition" | "limits"
    chapter: str | None = None
    h12: str | None = None
    page: int = 0
    paras: list = field(default_factory=list)   # (page, kind, text); kind: text | sub | table | note
    section_id: str = ""
    type: str = "other"
    path: str = ""

    @property
    def text(self) -> str:
        return "\n".join(t for _, _, t in self.paras)


_PUNCT = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-",
                        "—": "-", "−": "-", " ": " ", "•": "", "": ""})


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s.translate(_PUNCT)).strip()


def slug(s: str, max_len: int = 64) -> str:
    s = re.sub(r"[()']", "", s.lower().replace("&", " and "))
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    if len(s) > max_len:
        s = s[:max_len].rsplit("_", 1)[0]
    return s


def term_aliases(term: str) -> set[str]:
    """'Accident or accidental' -> {'accident or accidental', 'accident', 'accidental'}; 'Child(ren)' -> child, children."""
    t = term.lower()
    out = {t}
    if "(" in t:
        out |= {re.sub(r"\(.*?\)", "", t).strip(), re.sub(r"[()]", "", t)}
    parts = re.split(r",\s*(?:and\s+|or\s+)?|\s+or\s+|\s+and\s+", t)
    if len(parts) > 1:
        out |= {p.strip() for p in parts if p.strip()}
    return out


def page_lines(page, pno: int, header_y: float, footer_y: float, regions: list[dict]) -> tuple[list[Line], Counter]:
    """Text lines of one page (running header/footer and superscripts dropped), with table regions
    replaced by their transcription. Style = the style covering most characters of the line."""
    segments = []   # PyMuPDF can merge side-by-side text (term + definition) into one line: split on wide gaps
    for block in page.get_text("dict")["blocks"]:
        for raw in block.get("lines", []):
            seg, last_x1 = [], None
            for s in raw["spans"]:
                if s["size"] < 6:                                         # footnote markers
                    continue
                if s["text"].strip():
                    if last_x1 is not None and s["bbox"][0] - last_x1 > 8:
                        segments.append(seg)
                        seg = []
                    last_x1 = s["bbox"][2]
                seg.append(s)
            if seg:
                segments.append(seg)

    lines, dropped = [], Counter()
    for spans in segments:
        text = clean("".join(s["text"] for s in spans))
        x0, y0 = min(s["bbox"][0] for s in spans), min(s["bbox"][1] for s in spans)
        x1, y1 = max(s["bbox"][2] for s in spans), max(s["bbox"][3] for s in spans)
        if not text or y0 < header_y or y0 > footer_y:
            continue
        region = next((i for i, r in enumerate(regions) if r["bbox"][0] <= (x0 + x1) / 2 <= r["bbox"][2]
                       and r["bbox"][1] <= (y0 + y1) / 2 <= r["bbox"][3]), None)
        if region is not None:
            dropped[region] += 1
            continue
        style = Counter()
        for s in spans:
            style[(round(s["size"], 1), s["font"], s["color"])] += len(s["text"].strip())
        size, font, color = style.most_common(1)[0][0]
        all_bold = all("Bold" in s["font"] for s in spans if s["text"].strip())
        lines.append(Line(pno, x0, y0, x1, y1, size, font, color, text, all_bold=all_bold))
    for r in regions:
        x0, y0, x1, y1 = r["bbox"]
        lines.append(Line(pno, x0, y0, x1, y1, 9.0, "table", 0, r["text"].strip(), kind="table"))
    return lines, dropped


def _rows(lines: list[Line], tol: float = 3.0) -> list[Line]:
    """Sort top to bottom; lines starting within `tol` points of each other are one row, left to right."""
    out, row = [], []
    for ln in sorted(lines, key=lambda l: (l.y0, l.x0)):
        if row and ln.y0 - row[0].y0 > tol:
            out += sorted(row, key=lambda l: l.x0)
            row = []
        row.append(ln)
    return out + sorted(row, key=lambda l: l.x0)


def reading_order(lines: list[Line], gutter: float) -> list[Line]:
    """Two-column pages: full-width bands (lines crossing the gutter) split the page into slices;
    each slice is read left column then right column, each band row by row."""
    wide = sorted((l.y0 - 1, l.y1 + 1) for l in lines if l.x0 < gutter < l.x1 - 8)
    bands = []
    for a, b in wide:
        if bands and a <= bands[-1][1] + 6:
            bands[-1][1] = max(bands[-1][1], b)
        else:
            bands.append([a, b])
    groups: dict[tuple, list[Line]] = {}
    for ln in lines:
        cy = (ln.y0 + ln.y1) / 2
        band = next((i for i, (a, b) in enumerate(bands) if a <= cy <= b), None)
        if band is not None:
            key = (2 * band + 1, 0)
        else:
            above = sum(1 for _, b in bands if b < cy)
            key = (2 * above, 0 if ln.x0 < gutter else 1)
        groups.setdefault(key, []).append(ln)
    return [ln for key in sorted(groups) for ln in _rows(groups[key])]


def continues(prev: Line | None, ln: Line, gutter: float) -> bool:
    """Is `ln` the next line of the same paragraph as `prev`?"""
    if prev is None or prev.kind == "table":
        return False
    rel = lambda l: l.x0 - (gutter + 14 if l.x0 >= gutter else 40)   # indent within its column
    if abs(rel(prev) - rel(ln)) > 3:
        return False
    if ln.page != prev.page or (prev.x0 < gutter) != (ln.x0 < gutter) or ln.y0 < prev.y0:
        return not prev.text.endswith((".", ":", ";", "!", "?"))       # continues in next column/page
    return ln.y0 - prev.y0 <= ln.size * 1.35


def join(a: str, b: str) -> str:
    return a + b if re.search(r"[A-Za-z]-$", a) else f"{a} {b}"


def chunk_section(sec: Section) -> list[tuple[int, str]]:
    """[(page, body)]. A long benefit sharing a block with others (see FWD_GROUPS) is cut where the shared
    block starts, so that block yields identical chunks in every member and search can drop the copies.
    Short ones stay whole: each is a complete, distinct section."""
    split = next((i for i, p in enumerate(sec.paras) if p[1] == "note"), None)
    long = len(sec.text.split()) > CHUNK_IF_OVER
    parts = [sec.paras[:split], sec.paras[split:]] if split and long else [sec.paras]
    return [chunk for paras in parts for chunk in _chunk_paras(paras)]


def _chunk_paras(paras: list) -> list[tuple[int, str]]:
    """Whole text if short, else paragraph-packed chunks with a small overlap."""
    units = []
    for page, _, text in paras:
        words = text.split()
        if len(words) <= CHUNK_WORDS:
            units.append((page, text, len(words)))
        else:
            step = CHUNK_WORDS - OVERLAP_WORDS
            for i in range(0, len(words), step):
                units.append((page, " ".join(words[i:i + CHUNK_WORDS]), len(words[i:i + CHUNK_WORDS])))
    if sum(n for *_, n in units) <= CHUNK_IF_OVER:
        return [(paras[0][0], "\n".join(t for _, _, t in paras))]
    chunks, cur = [], []
    for unit in units:
        if cur and sum(n for *_, n in cur) + unit[2] > CHUNK_WORDS:
            chunks.append(cur)
            keep = []
            for u in reversed(cur):
                if sum(n for *_, n in keep) + u[2] > OVERLAP_WORDS:
                    break
                keep.insert(0, u)
            cur = keep
        cur.append(unit)
    chunks.append(cur)
    return [(c[0][0], "\n".join(t for _, t, _ in c)) for c in chunks]


# ---------------------------------------------------------------- FWD

FWD_NAME = "FWD Travel Insurance"
ORANGE, DARK, WHITE = 0xE87722, 0x183028, 0xFFFFFF
COVERED, OPTIONAL, EXCLUSIONS = "What you're covered for", "Optional covers", "General exclusions"
FWD_SKIP = {1, 2}                 # cover page, quick-reference contents
FWD_LIMIT_PAGES = range(5, 10)    # "Quick summary of your benefits" benefit-limit tables
FWD_DEFINITION_PAGES = range(43, 46)
FWD_OPTIONAL_COVERS = {"You need to pay extra", "Pre-existing medical conditions", "Cancel for any reason",
                       "Car rental excess", "Pet care", "Sports equipment protector", "Home contents"}
# Benefits printed one after another that share a single What we pay / What you should know /
# What is not covered block. Each member gets its own trigger text plus a copy of the shared block.
FWD_GROUPS = [["Trip cancellation and loss of deposit", "Trip postponement", "Trip cut short"],
              ["Trip diversion", "Travel delay", "Missed connections"],
              ["Hospitalisation visit", "Child companion", "Compassionate travel"]]
FWD_CHAPTER_TYPES = {"About your policy": "condition", COVERED: "benefit", EXCLUSIONS: "exclusion",
                     "Making a claim": "condition", "Starting or ending your policy": "condition",
                     "Important things to know": "condition", "How to reach us": "other"}
FWD_OTHER_TITLES = {"Easy to read", "Words with special meaning"}
GUTTER, HEADER_Y, FOOTER_Y = 297, 56, 800


def fwd_kind(ln: Line) -> str:
    if ln.kind == "table":
        return "table"
    strong = any(w in ln.font for w in ("Bold", "Black", "Medium"))
    if ln.color == ORANGE and ln.size >= 24:
        return "chapter"
    if ln.color == ORANGE and 11.5 <= ln.size < 14:
        return "h12"
    if ln.color == ORANGE and 9.5 <= ln.size < 11 and strong:
        return "h10"
    if ln.size < 9.5 and strong and ln.color in (ORANGE, DARK):
        return "sub"
    return "text"


def merge_headings(lines: list[Line], kind) -> list[Line]:
    """Join headings that wrap onto a second line (same style, directly below)."""
    out = []
    for ln in lines:
        k = kind(ln)
        prev = out[-1] if out else None
        if (prev and k in ("chapter", "h12", "h10", "sub") and kind(prev) == k and prev.page == ln.page
                and abs(prev.x0 - ln.x0) < 3 and 0 < ln.y0 - prev.y0 < ln.size * 1.6):
            prev.text, prev.y0 = join(prev.text, ln.text), ln.y0   # y0 moves down so a 3rd line can join
            continue
        out.append(ln)
    return out


def fwd_main_flow(doc, regions: dict, dropped: Counter) -> list[Section]:
    lines = []
    for pno in range(1, doc.page_count + 1):
        if pno in FWD_SKIP or pno in FWD_LIMIT_PAGES or pno in FWD_DEFINITION_PAGES:
            continue
        page_regions = regions.get(pno, [])
        lns, d = page_lines(doc[pno - 1], pno, HEADER_Y, FOOTER_Y, page_regions)
        dropped.update({(pno, i): n for i, n in d.items()})
        lines += reading_order(lns, GUTTER)
    lines = merge_headings(lines, fwd_kind)

    sections, cur, chapter, h12, prev = [], None, None, None, None

    def start(ln: Line, level: str) -> Section:
        sec = Section("fwd", ln.text, level, chapter, h12, ln.page)
        sections.append(sec)
        return sec

    for ln in lines:
        k = fwd_kind(ln)
        if k == "h10" and chapter == COVERED and h12 == OPTIONAL and ln.text not in FWD_OPTIONAL_COVERS:
            k = "sub"   # benefits inside an optional cover (e.g. Pre-existing medical conditions)
        if k == "chapter":
            chapter, h12 = ln.text, None
            cur = start(ln, "chapter")
        elif k == "h12":
            h12 = ln.text
            cur = start(ln, "h12")
        elif k == "h10":
            cur = start(ln, "h10")
        elif k == "table":
            cur.paras += [(ln.page, "table", t) for t in ln.text.splitlines() if t.strip()]
        elif k == "sub":
            cur.paras.append((ln.page, "sub", ln.text))
        elif cur.paras and cur.paras[-1][1] == "text" and continues(prev, ln, GUTTER):
            page, _, text = cur.paras[-1]
            cur.paras[-1] = (page, "text", join(text, ln.text))
        else:
            cur.paras.append((ln.page, "text", ln.text))
        prev = ln if k == "text" else None
    return [s for s in sections if s.paras]


def fwd_apply_groups(sections: list[Section]) -> None:
    by_title = {s.title: s for s in sections if s.chapter == COVERED and s.h12 != OPTIONAL and s.level == "h10"}
    for group in FWD_GROUPS:
        members = [by_title[t] for t in group]
        idx = [sections.index(m) for m in members]
        assert idx == list(range(idx[0], idx[0] + len(idx))), f"group not consecutive: {group}"
        last = members[-1]
        split = next(i for i, p in enumerate(last.paras) if p[1] in ("sub", "table"))
        shared, last.paras = last.paras[split:], last.paras[:split]
        names = ", ".join(group[:-1]) + " and " + group[-1]
        for m in members:
            m.paras += [(shared[0][0], "note", f"[The following applies to {names}.]")] + shared


def fwd_limit_tables(doc) -> list[Section]:
    """Benefit-limit tables: one section per table group (e.g. Protecting your travel plans)."""
    sections, cur = [], None
    for pno in FWD_LIMIT_PAGES:
        lines, _ = page_lines(doc[pno - 1], pno, HEADER_Y, FOOTER_Y, [])
        white = [l for l in lines if l.color == WHITE]
        plans = [l for l in white if l.x0 >= GUTTER and "Maximum benefit" not in l.text]
        top = min(l.y0 for l in white)
        intro = " ".join(l.text for l in sorted(lines, key=lambda l: l.y0) if l.y0 < top and l.size < 11)
        body = sorted((l for l in lines if l.y0 > top and l.color != WHITE), key=lambda l: (l.y0, l.x0))
        labels = [l for l in body if l.x0 < GUTTER]
        values = [l for l in body if l.x0 >= GUTTER]
        groups = sorted((l for l in white if l.x0 < GUTTER and "Maximum benefit" not in l.text), key=lambda l: l.y0)

        bold = [l for l in labels if "Bold" in l.font]   # a bold label wrapping onto a 2nd line is still one row
        heads = [h for i, h in enumerate(bold)
                 if not (i and abs(h.x0 - bold[i - 1].x0) < 2 and h.y0 - bold[i - 1].y0 <= 12)]
        blocks = []   # (group title, parent head, [label lines], [value lines])
        parent = None
        for i, h in enumerate(heads):
            end = heads[i + 1].y0 - 4 if i + 1 < len(heads) else 1e9
            g = [x for x in groups if x.y0 < h.y0]
            gtitle = g[-1].text if g else (cur.title.removeprefix("Benefit limits: ") if cur else "")
            if h.x0 < 53:
                parent = h.text
            blocks.append((gtitle, parent if h.x0 >= 53 else None,
                           [l for l in labels if h.y0 - 4 <= l.y0 < end],
                           [v for v in values if h.y0 - 4 <= v.y0 < end]))

        joined = []   # a value cell drawn across two rows (merged cell) is one limit shared by both rows
        for gtitle, parent, labs, vals in blocks:
            prev = joined[-1] if joined else None
            if (not vals and prev and prev[3] and prev[1] == parent
                    and max((v.y0 + v.y1) / 2 for v in prev[3]) > max(l.y1 for l in prev[2])):
                prev[2][0].text = f"{prev[2][0].text} and {labs[0].text} (one combined limit)"
                prev[2].extend(labs[1:])
                continue
            joined.append((gtitle, parent, labs, vals))

        for gtitle, parent, labs, vals in joined:
            merged, last_y0 = [], None   # a label that wraps onto a second line (11pt below) is one label
            for l in labs:
                if (merged and abs(l.x0 - merged[-1].x0) < 2 and l.y0 - last_y0 <= 12
                        and ("Bold" in l.font) == ("Bold" in merged[-1].font)):
                    merged[-1] = Line(l.page, merged[-1].x0, merged[-1].y0, max(l.x1, merged[-1].x1), l.y1,
                                      l.size, merged[-1].font, l.color, join(merged[-1].text, l.text))
                else:
                    merged.append(l)
                last_y0 = l.y0
            labs = merged
            if cur is None or cur.title != f"Benefit limits: {gtitle}":
                cur = Section("fwd", f"Benefit limits: {gtitle}", "limits", "Quick summary of your benefits", None, pno)
                cur.paras.append((pno, "text", intro))
                sections.append(cur)
            clusters = []
            for v in sorted(vals, key=lambda v: v.y0):
                if clusters and v.y0 - clusters[-1][-1].y0 <= 7:
                    clusters[-1].append(v)
                else:
                    clusters.append([v])

            def fmt(cluster) -> str:
                cells = {}
                for v in cluster:
                    plan = min(plans, key=lambda p: abs((p.x0 + p.x1) / 2 - (v.x0 + v.x1) / 2)).text
                    cells[plan] = join(cells[plan], v.text) if plan in cells else v.text
                return ", ".join(f"{p.text} {cells[p.text]}" for p in sorted(plans, key=lambda p: p.x0) if p.text in cells)

            attach = {}
            for c in clusters:
                cy = sum(v.y0 + v.y1 for v in c) / (2 * len(c))
                target = labs[0] if len(clusters) == 1 else min(labs, key=lambda l: abs((l.y0 + l.y1) / 2 - cy))
                attach.setdefault(id(target), []).append(fmt(c))
            parts = [l.text + (f" [{'; '.join(attach[id(l)])}]" if id(l) in attach else "") for l in labs]
            head = (f"{parent} > " if parent else "") + parts[0]
            cur.paras.append((labs[0].page, "text", head + (": " + "; ".join(parts[1:]) if parts[1:] else "")))
    return sections


def fwd_definitions(doc) -> list[Section]:
    sections = []
    for pno in FWD_DEFINITION_PAGES:
        lines, _ = page_lines(doc[pno - 1], pno, HEADER_Y, FOOTER_Y, [])
        terms = sorted((l for l in lines if fwd_kind(l) == "h10" and l.x0 < 190), key=lambda l: l.y0)
        defs = sorted((l for l in lines if l.x0 >= 190), key=lambda l: (l.y0, l.x0))
        starts = []   # [(start y, Section)]
        for t in terms:
            if starts and starts[-1][1].page == pno and t.y0 - last_y < 16:
                starts[-1][1].title = join(starts[-1][1].title, t.text)
            else:
                sec = Section("fwd", t.text, "definition", "Important words and phrases", None, pno)
                sections.append(sec)
                starts.append((t.y0, sec))
            last_y = t.y0
        prev = None
        for d in defs:
            owner = [s for y, s in starts if y <= d.y0 + 4]
            sec = owner[-1] if owner else sections[-len(starts) - 1]   # continues from previous page
            if sec.paras and sec.paras[-1][1] == "text" and continues(prev, d, 9999):
                page, _, text = sec.paras[-1]
                sec.paras[-1] = (page, "text", join(text, d.text))
            else:
                sec.paras.append((d.page, "text", d.text))
            prev = d
        unexpected = [l.text for l in lines if l.x0 < 190 and fwd_kind(l) not in ("h10", "chapter") and l.size < 11.5]
        if unexpected:
            print(f"  WARNING p{pno}: unassigned lines in definitions: {unexpected}")
    return sections


def fwd_finish(sec: Section) -> None:
    """Assign section_id, type and breadcrumb path."""
    if sec.level == "definition":
        sec.section_id, sec.type = f"fwd:definitions:{slug(sec.title)}", "definition"
        sec.path = f"{FWD_NAME} > Important words and phrases > {sec.title}"
        return
    if sec.level == "limits":
        group = sec.title.removeprefix("Benefit limits: ")
        sec.section_id, sec.type = f"fwd:benefit_limits:{slug(group)}", "benefit"
        sec.path = f"{FWD_NAME} > Quick summary of your benefits > {group}"
        return
    s = slug(sec.title)
    if sec.chapter == EXCLUSIONS and sec.level == "h10":
        s = f"general_exclusions:{s}"
    elif sec.chapter == COVERED and sec.h12 == OPTIONAL and sec.level == "h10":
        s = f"optional:{s}"
    sec.section_id = f"fwd:{s}"
    t = sec.title.lower()
    if sec.chapter == EXCLUSIONS or "not covered" in t or "no cover" in t:
        sec.type = "exclusion"
    elif sec.level == "chapter" or sec.title in FWD_OTHER_TITLES or (sec.chapter == COVERED and sec.level == "h12"):
        sec.type = "other"
    else:
        sec.type = FWD_CHAPTER_TYPES[sec.chapter]
    crumbs = [FWD_NAME, sec.chapter] + ([sec.h12] if sec.level == "h10" and sec.h12 else []) + [sec.title]
    sec.path = " > ".join(dict.fromkeys(crumbs))


def parse_fwd(pdf_path: Path, tables: list[dict]) -> list[Section]:
    doc = pymupdf.open(pdf_path)
    regions: dict[int, list] = {}
    for t in tables:
        regions.setdefault(t["page"], []).append(t)
    dropped = Counter()
    main = fwd_main_flow(doc, regions, dropped)
    for pno, rs in regions.items():
        for i, r in enumerate(rs):
            if not dropped[(pno, i)]:
                raise RuntimeError(f"table region on p{pno} ({r['what']}) matched no text; has the PDF changed?")
    fwd_apply_groups(main)
    sections = sorted(fwd_limit_tables(doc) + main + fwd_definitions(doc), key=lambda s: s.page)
    for s in sections:
        fwd_finish(s)
    print(f"  {len(tables)} transcribed tables inserted, {sum(dropped.values())} extracted lines replaced")
    return sections


# ---------------------------------------------------------------- MSIG

MSIG_NAME = "MSIG TravelEasy Insurance"
MSIG_HEADER_Y, MSIG_FOOTER_Y = 80, 785   # page 1 letterhead / "QTD052510 | Page N of 70"
# Chapter bars (white text) -> type of their sections; None = skip (contents pages).
MSIG_CHAPTERS = {"A GUIDE TO THE POLICY": None, "IMPORTANT CONDITIONS": "condition",
                 "DEFINITION OF WORDS": "definition", "THE BENEFITS": "benefit", "EXCLUSIONS": "exclusion",
                 "GENERAL EXCLUSIONS": "exclusion", "GENERAL CONDITIONS": "condition",
                 "CLAIM CONDITIONS": "condition", "PREMIUM WARRANTY": "condition", "USEFUL PROCEDURES": "other"}
MSIG_NUMBERED = {"GENERAL EXCLUSIONS": "general_exclusion", "GENERAL CONDITIONS": "general_condition",
                 "CLAIM CONDITIONS": "claim_condition"}   # one section per top-level numbered item
TIGHT = 13.5   # MSIG line spacing is ~12.3pt inside a paragraph and ~25pt between paragraphs


@dataclass
class Row:
    page: int
    y0: float
    cells: list   # Lines left to right

    @property
    def text(self) -> str:
        return " | ".join(c.text for c in self.cells)


def msig_rows(doc) -> list[Row]:
    rows = []
    for pno in range(1, doc.page_count + 1):
        lines, _ = page_lines(doc[pno - 1], pno, MSIG_HEADER_Y, MSIG_FOOTER_Y, [])
        cur = []
        for ln in sorted(lines, key=lambda l: (l.y0, l.x0)):
            if cur and ln.y0 - cur[0].y0 > 3:
                rows.append(Row(pno, cur[0].y0, sorted(cur, key=lambda l: l.x0)))
                cur = []
            cur.append(ln)
        if cur:
            rows.append(Row(pno, cur[0].y0, sorted(cur, key=lambda l: l.x0)))
    return rows


def parse_msig(pdf_path: Path, tables: list[dict]) -> list[Section]:
    doc = pymupdf.open(pdf_path)
    rows = msig_rows(doc)
    sections, def_rows = [], []
    st = dict(cur=None, chapter=None, label=None, prev=None, table=None, last_tr=None, heads=[], group=[])

    def start(row: Row, title: str, sid: str, typ: str) -> None:
        close_group()
        sec = Section("msig", title, "msig", st["label"], None, row.page, section_id=f"msig:{sid}", type=typ)
        sec.path = " > ".join(dict.fromkeys(x for x in (MSIG_NAME, st["label"], title) if x))
        sections.append(sec)
        st.update(cur=sec, prev=None, table=None, last_tr=None, heads=[])

    def render_tr(tr: dict) -> str:
        vals = "; ".join(f"{p} {tr['vals'][p]}" for p, _ in st["table"] if p in tr["vals"])
        return tr["label"] + (f" [{vals}]" if vals else "")

    def close_group() -> None:
        """Rows of one benefit (after a label-only row such as 'Section 2 ...'). A plan with a value on
        exactly one of them and blanks elsewhere is a merged cell drawn across all the rows."""
        group, st["group"] = st.get("group", []), []
        if len(group) < 2 or not st["table"]:
            return
        for plan, _ in st["table"]:
            have = [tr for tr in group if plan in tr["vals"]]
            if len(have) == 1:
                for tr in group:
                    tr["vals"].setdefault(plan, have[0]["vals"][plan])
        for tr in group:
            st["cur"].paras[tr["i"]] = (tr["page"], "text", render_tr(tr))

    def table_row(row: Row) -> bool:
        """Rows of a plan table become 'label [Lite Plan $x; ...]'. Returns False if the table has ended."""
        cols = st["table"]
        first_x, last_x = cols[0][1], cols[-1][1]
        cells = row.cells
        if len(cells) == 1 and cells[0].x0 < first_x - 60 and cells[0].x1 > last_x - 10 and not cells[0].all_bold:
            close_group()
            st["table"] = None   # a full-width paragraph: the table is over
            return False
        labels = [c for c in cells if (c.x0 + c.x1) / 2 < first_x - 25]
        vals = {}
        for c in cells:
            if c not in labels:
                plan = min(cols, key=lambda p: abs(p[1] - (c.x0 + c.x1) / 2))[0]
                vals[plan] = join(vals[plan], c.text) if plan in vals else c.text
        label = " ".join(c.text for c in labels)
        tr, sec = st["last_tr"], st["cur"]
        if tr and not label and vals:                                         # 2nd line of value cells
            for p, v in vals.items():
                tr["vals"][p] = join(tr["vals"][p], v) if p in tr["vals"] else v
            if tr not in st["group"]:
                st["group"].append(tr)
        elif tr and label[:1].islower() and not vals and row.page == tr["page"] and row.y0 - tr["y"] <= TIGHT:
            tr["label"] = join(tr["label"], label)                           # label wraps onto a 2nd line
        else:
            if not vals:
                close_group()                                                # label-only row starts a benefit
            tr = dict(label=label, vals=vals, page=row.page, i=len(sec.paras))
            sec.paras.append((row.page, "text", ""))
            st["last_tr"] = tr
            if vals:
                st["group"].append(tr)
        tr["y"] = row.y0
        sec.paras[tr["i"]] = (tr["page"], "text", render_tr(tr))
        return True

    def header_row(row: Row) -> bool:
        """Bold/white rows may be plan-table headers, possibly split over two lines ('Pre-Ex Elite' / 'Plan')."""
        if not all(c.all_bold or c.color == WHITE for c in row.cells):
            return False
        st["heads"] = [r for r in st["heads"] if r.page == row.page and row.y0 - r.y0 <= 30] + [row]
        cells = [c for r in st["heads"] for c in r.cells]
        plans = [c for c in cells if c.x0 > 150 and c.text.endswith("Plan")]
        if len(plans) < 3 or not any(c.text.endswith("Plan") for c in row.cells):
            return all(c.color == WHITE for c in row.cells)   # other white header cells: decoration, skip
        close_group()
        cols = {}
        for c in plans:
            name = c.text
            if name == "Plan":
                above = [a for a in cells if 0 < c.y0 - a.y0 <= 16 and abs((a.x0 + a.x1) - (c.x0 + c.x1)) < 40]
                name = f"{above[-1].text} Plan" if above else name
            xc = (c.x0 + c.x1) / 2
            if all(abs(xc - x) > 20 for x in cols.values()):
                cols[name] = xc
        st["table"], st["last_tr"] = sorted(cols.items(), key=lambda kv: kv[1]), None
        return True

    for row in rows:
        first, single, t = row.cells[0], len(row.cells) == 1, row.text
        if single and first.color == WHITE and t in MSIG_CHAPTERS:
            st.update(chapter=t, label=t.capitalize(), in_defs=False)
            if MSIG_CHAPTERS[t] and t != "DEFINITION OF WORDS":
                start(row, t.capitalize(), slug(t), "other" if t == "THE BENEFITS" else MSIG_CHAPTERS[t])
            else:
                st["cur"] = None
            continue
        if st["chapter"] == "A GUIDE TO THE POLICY":
            continue
        if st["chapter"] == "DEFINITION OF WORDS":
            def_rows.append(row)
            continue
        cur, prev = st["cur"], st["prev"]
        tight = bool(single and prev and cur and cur.paras and cur.paras[-1][1] == "text" and (
            (row.page == prev.page and 0 < row.y0 - prev.y0 <= TIGHT)
            or (row.page != prev.page and not cur.paras[-1][2].endswith((".", ":", ";")))))
        m_sec = re.match(r"SECTION (\d+) - (.+)", t)
        if single and first.size >= 9.9 and first.all_bold and not t.startswith(("MSIG Assist", "+65")):
            if m_sec:
                start(row, f"Section {m_sec[1]} - {m_sec[2].capitalize()}", f"section_{m_sec[1]}", "benefit")
            elif "Benefits Summary" in t or t.startswith("COVID-19 COVER"):
                label = "COVID-19 cover" if t.startswith("COVID") else t
                st.update(chapter=label, label=label)
                start(row, label, slug(label), "benefit")
            else:
                start(row, t.capitalize() if t.isupper() else t, slug(t),
                      "condition" if "LIMIT" in t else "other")
            continue
        if single and first.all_bold and t.isupper() and len(t) > 6 and not tight:
            covid = st["chapter"] == "COVID-19 cover"
            start(row, t.capitalize(), ("covid_19_" if covid and "COVID" not in t else "") + slug(t),
                  "condition" if any(w in t for w in ("CONDITION", "TERMS", "LIMIT")) else ("benefit" if covid else "other"))
            continue
        if st["chapter"] == "EXCLUSIONS" and single and first.all_bold and t.startswith("Exclusions which apply"):
            start(row, t, "exclusions_sections_" + "_".join(re.findall(r"\d+", t)), "exclusion")
            continue
        m_num = re.match(r"(\d+)\.?\s+(.+)", first.text)
        if st["chapter"] in MSIG_NUMBERED and first.x0 < 50 and m_num:
            kind = MSIG_NUMBERED[st["chapter"]]
            short = m_num[2] if len(m_num[2]) <= 70 else m_num[2][:70].rsplit(" ", 1)[0] + " ..."
            start(row, f"{kind.replace('_', ' ').capitalize()} {m_num[1]}: {short.rstrip('.;:')}",
                  f"{kind}_{m_num[1]}", MSIG_CHAPTERS[st["chapter"]])
            st["cur"].paras.append((row.page, "text", t))
            st["prev"] = row
            continue
        if cur is None:
            continue
        if header_row(row):
            continue
        if st["table"] and table_row(row):
            continue
        if tight:
            page, _, text = cur.paras[-1]
            cur.paras[-1] = (page, "text", join(text, t))
        elif single and first.all_bold:
            cur.paras.append((row.page, "sub", t))
        else:
            cur.paras.append((row.page, "text", t))
        st["prev"] = row if cur.paras[-1][1] == "text" else None
    close_group()

    defs = msig_definitions(doc, def_rows)
    return sorted(defs + [s for s in sections if s.paras], key=lambda s: s.page)


def msig_definitions(doc, def_rows: list[Row]) -> list[Section]:
    """TERM | DEFINITION table. A term can be vertically centred in its cell (first definition line above
    it), so lines are grouped by the table's horizontal rules rather than by reading order."""
    rules: dict[int, list[float]] = {}

    def band(page: int, ln: Line) -> int:
        if page not in rules:
            ys = set()
            for d in doc[page - 1].get_drawings():
                for it in d["items"]:
                    if it[0] == "re" and it[1].width > 300 and it[1].height < 2:
                        ys.add(it[1].y0)
                    elif it[0] == "l" and abs(it[1].y - it[2].y) < 1 and abs(it[1].x - it[2].x) > 300:
                        ys.add(it[1].y)
            rules[page] = sorted(ys)
        return sum(1 for y in rules[page] if y <= (ln.y0 + ln.y1) / 2)

    cells, started = {}, False   # (page, band) -> ([term lines], [definition lines]), in reading order
    for row in def_rows:
        if row.text == "TERM | DEFINITION":
            started = True
            continue
        if started:   # (rows before the first header are the chapter intro)
            for c in row.cells:
                cells.setdefault((row.page, band(row.page, c)), ([], []))[0 if c.x0 < 190 else 1].append(c)

    sections = []
    for (page, _), (terms, lines) in cells.items():
        if terms:
            title = terms[0].text
            for t in terms[1:]:
                title = join(title, t.text)
            sec = Section("msig", title, "definition", "Definition of words", None, page, type="definition",
                          section_id=f"msig:definitions:{slug(title)}",
                          path=f"{MSIG_NAME} > Definition of words > {title}")
            sections.append(sec)
        elif sections:
            sec = sections[-1]        # a definition continued from the previous page
        else:
            continue
        prev = None
        for c in sorted(lines, key=lambda l: l.y0):
            continued = prev is None and not terms and sec.paras and not sec.paras[-1][2].endswith((".", ":", ";"))
            if sec.paras and ((prev and 0 < c.y0 - prev.y0 <= TIGHT) or continued):
                sec.paras[-1] = (sec.paras[-1][0], "text", join(sec.paras[-1][2], c.text))
            else:
                sec.paras.append((c.page, "text", c.text))
            prev = c
    return sections


# ---------------------------------------------------------------- main

POLICIES = {   # policy key -> (PDF file in data/policies/, parser)
    "fwd": ("fwd_travel_policy_wording.pdf", parse_fwd),
    "msig": ("msig_traveleasy_policy.pdf", parse_msig),
}


def build(embed: bool, samples: int, seed: int) -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    tables = yaml.safe_load(TABLES_PATH.read_text(encoding="utf-8"))
    all_sections, definitions = [], {}
    for policy, (filename, parse) in POLICIES.items():
        print(f"[{policy}] parsing {filename}")
        sections = parse(POLICY_DIR / filename, tables.get(policy, []))
        seen = Counter()
        for s in sections:   # keep IDs unique and stable: a repeated id gets _2, _3, ... in document order
            seen[s.section_id] += 1
            if seen[s.section_id] > 1:
                print(f"  WARNING duplicate id {s.section_id} ('{s.title}', p{s.page}) -> _{seen[s.section_id]}")
                s.section_id = f"{s.section_id}_{seen[s.section_id]}"
        lookup = {}
        for s in sections:
            if s.type == "definition":
                for alias in sorted(term_aliases(s.title)):
                    lookup.setdefault(alias, s.section_id)
        definitions[policy] = lookup
        all_sections += sections
        types = Counter(s.type for s in sections)
        print(f"  {len(sections)} sections ({', '.join(f'{k} {v}' for k, v in sorted(types.items()))}), "
              f"{len(lookup)} defined-term aliases")

    with SECTIONS_PATH.open("w", encoding="utf-8") as f:
        for s in all_sections:
            f.write(json.dumps({"section_id": s.section_id, "policy": s.policy, "title": s.title, "type": s.type,
                                "page": s.page, "page_end": max(p for p, _, _ in s.paras), "path": s.path,
                                "text": s.text}, ensure_ascii=False) + "\n")
    DEFINITIONS_PATH.write_text(json.dumps(definitions, indent=1, sort_keys=True), encoding="utf-8")

    chunks = []
    for s in all_sections:
        for n, (page, body) in enumerate(chunk_section(s)):
            chunks.append({"id": f"{s.section_id}#{n}", "text": f"{s.path}\n{body}",
                           "meta": {"policy": s.policy, "section_id": s.section_id, "title": s.title,
                                    "type": s.type, "page": page}})
    sizes = sorted(len(c["text"].split()) for c in chunks)
    print(f"{len(all_sections)} sections -> {len(chunks)} chunks (words: min {sizes[0]}, "
          f"median {sizes[len(sizes) // 2]}, max {sizes[-1]})")

    if embed:
        import chromadb
        from chromadb.config import Settings
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(EMBED_MODEL, device="cpu")
        vectors = model.encode([c["text"] for c in chunks], batch_size=32, normalize_embeddings=True,
                               show_progress_bar=False)
        client = chromadb.PersistentClient(path=str(CHROMA_DIR), settings=Settings(anonymized_telemetry=False))
        try:
            client.delete_collection(COLLECTION)
        except Exception:   # first build: nothing to delete (exception type differs across chromadb versions)
            pass
        col = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
        col.add(ids=[c["id"] for c in chunks], embeddings=vectors.tolist(),
                documents=[c["text"] for c in chunks], metadatas=[c["meta"] for c in chunks])
        print(f"Embedded with {EMBED_MODEL} (cpu) into Chroma at {CHROMA_DIR.relative_to(ROOT)} "
              f"(collection '{COLLECTION}', {col.count()} chunks)")
    print(f"Wrote {SECTIONS_PATH.relative_to(ROOT)} and {DEFINITIONS_PATH.relative_to(ROOT)}")

    rng = random.Random(seed)
    for policy in POLICIES:
        pool = [s for s in all_sections if s.policy == policy]
        picks = sorted(rng.sample(pool, min(samples, len(pool))), key=all_sections.index)
        print(f"\n===== {samples} random {policy} sections (seed {seed}) =====")
        for s in picks:
            n_chunks = len(chunk_section(s))
            text = s.text if len(s.text) <= 700 else s.text[:700] + " ..."
            print(f"\n--- {s.section_id}  [{s.type}, p{s.page}, {len(s.text.split())} words, {n_chunks} chunk(s)]")
            print(f"    path: {s.path}")
            print("    " + text.replace("\n", "\n    "))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-embed", action="store_true", help="parse only; skip embeddings and Chroma")
    ap.add_argument("--samples", type=int, default=10, help="random sections to print per policy")
    ap.add_argument("--seed", type=int, default=0, help="seed for picking the sample sections")
    args = ap.parse_args()
    build(embed=not args.no_embed, samples=args.samples, seed=args.seed)


if __name__ == "__main__":
    main()
