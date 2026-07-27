#!/usr/bin/env python3
"""
Compare the CV against the site's publication data and report what has drifted.

    python3 drift.py                 # uses the default CV path
    python3 drift.py path/to/CV.docx

Exits non-zero when the CV contains something the site does not, or vice versa,
unless the difference is recorded as deliberate in EXPECTED_OFF_SITE below.

Why this exists: the point of the rebuild was that updating the CV and updating
the site become one action. That is only true if something notices when they
disagree. Run it after every CV edit.

On parsing: entries in the CV are '<hyperlinked title>, <SMALL CAPS VENUE> (date)
(with coauthors).' The title is the hyperlink text where there is one, and the
run of text before the first small-caps run where there is not. This was written
against the actual XML rather than a guess about it — three parsers written
against an assumed format all returned nonsense.
"""

import json
import os
import re
import sys
import unicodedata

try:
    import docx
    from docx.oxml.ns import qn
except ImportError:
    sys.exit("needs python-docx:  pip3 install python-docx")

ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CV = "/Users/petersalib/Library/CloudStorage/Dropbox/CV-PeterSalib.docx"

# Sections of the CV that correspond to things the site lists.
PUB_SECTIONS = {
    "works in progress", "book", "print articles", "online articles",
    "student comment", "selected general audience",
}
STOP_AT = {"education", "clerkship", "appointments", "selected presentations"}

# Titles that appear in one place but deliberately not the other. Keeping these
# explicit is what stops a real decision from looking like an error.
EXPECTED_OFF_SITE = {
    # "some title": "why it is not on the site",
}
EXPECTED_OFF_CV = {
}


def norm(s):
    """Fold case, quotes, dashes and spacing so titles compare sanely."""
    s = unicodedata.normalize("NFKD", s)
    s = s.replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = re.sub(r"[‐-―]", "-", s)
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def cv_titles(path):
    """Yield (section, title) for every publication entry in the CV."""
    d = docx.Document(path)
    section, out = None, []

    for p in d.paragraphs:
        text = p.text.strip()
        if not text:
            continue

        low = norm(text)
        if low in PUB_SECTIONS:
            section = low
            continue
        if low in STOP_AT or (section and low.isupper() and len(low) < 40):
            if low in STOP_AT:
                section = None
            continue
        if section is None:
            continue

        # Award and conference notes are bulleted list paragraphs, not entries.
        pPr = p._p.find(qn("w:pPr"))
        if pPr is not None and pPr.find(qn("w:numPr")) is not None:
            continue

        # A single paragraph can hold more than one entry, separated by line
        # breaks rather than paragraph marks — so take every hyperlink in it.
        links = p._p.findall(qn("w:hyperlink"))
        if links:
            titles = ["".join(t.text or "" for t in hl.iter(qn("w:t"))).strip()
                      for hl in links]
        else:
            # No link: everything before the first small-caps run is the title.
            # Works in progress have no venue at all, so nothing breaks the loop
            # and we fall through to the parenthetical strip below.
            buf = ""
            for r in p._p.findall(qn("w:r")):
                rpr = r.find(qn("w:rPr"))
                if rpr is not None and rpr.find(qn("w:smallCaps")) is not None:
                    break
                buf += "".join(t.text or "" for t in r.iter(qn("w:t")))
            titles = [buf]

        for title in titles:
            # drop '(with X & Y)', '(forthcoming 2026)', '(symposium)' etc.
            title = re.sub(r"\s*\((with|forthcoming|invited|peer|symposium)[^)]*\)",
                           "", title, flags=re.I)
            title = title.rstrip(",. ").strip()
            if len(title) > 3:
                out.append((section, title))
    return out


def site_titles():
    with open(os.path.join(ROOT, "content", "publications.json"), encoding="utf-8") as f:
        d = json.load(f)
    return [(g, e["title"]) for g in ("publications", "works_in_progress", "popular")
            for e in d[g]]


def main():
    cv_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CV
    if not os.path.exists(cv_path):
        sys.exit(f"no CV at {cv_path}")

    cv = cv_titles(cv_path)
    site = site_titles()
    cv_map = {norm(t): t for _, t in cv}
    site_map = {norm(t): t for _, t in site}

    only_cv = [cv_map[k] for k in cv_map.keys() - site_map.keys()
               if cv_map[k] not in EXPECTED_OFF_SITE]
    only_site = [site_map[k] for k in site_map.keys() - cv_map.keys()
                 if site_map[k] not in EXPECTED_OFF_CV]

    print(f"CV: {len(cv)} entries   Site: {len(site)} entries   "
          f"matched: {len(cv_map.keys() & site_map.keys())}")

    if only_cv:
        print(f"\nIn the CV but not on the site ({len(only_cv)}):")
        for t in sorted(only_cv):
            print(f"  + {t}")
    if only_site:
        print(f"\nOn the site but not in the CV ({len(only_site)}):")
        for t in sorted(only_site):
            print(f"  - {t}")
    if EXPECTED_OFF_SITE:
        print("\nDeliberately off the site:")
        for t, why in EXPECTED_OFF_SITE.items():
            print(f"  · {t} — {why}")

    if not only_cv and not only_site:
        print("\nNo drift.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
