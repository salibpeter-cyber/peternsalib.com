#!/usr/bin/env python3
"""
Build peternsalib.com from content/*.json into public/.

Python standard library only, on purpose. No npm, no static-site generator, no
theme. The point of this site is that it still builds in five years without a
dependency archaeology session, and that updating the CV and updating the site
are one action.

    python3 build.py          # writes public/
    python3 build.py --check  # exits non-zero if anything is missing a link

Content lives in content/. Nothing in public/ should ever be hand-edited; it is
generated and committed so the host needs no build step.
"""

import json
import os
import re
import shutil
import sys
from html import escape

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(ROOT, "content")
PUBLIC = os.path.join(ROOT, "public")
ASSETS = os.path.join(ROOT, "assets")


def load(name):
    with open(os.path.join(CONTENT, name), encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- formatting


def link(text, url, cls=""):
    """External links get noopener; internal ones don't need it."""
    if not url:
        return text
    c = f' class="{cls}"' if cls else ""
    ext = ' target="_blank" rel="noopener"' if url.startswith("http") else ""
    return f'<a href="{escape(url, quote=True)}"{c}{ext}>{text}</a>'


def coauthor_html(names, links):
    """'With A, B and C', each linked only where we have a verified homepage."""
    if not names:
        return ""
    parts = [link(escape(n), links.get(n, "")) for n in names]
    if len(parts) == 1:
        joined = parts[0]
    elif len(parts) == 2:
        joined = f"{parts[0]} and {parts[1]}"
    else:
        joined = ", ".join(parts[:-1]) + f" and {parts[-1]}"
    return f"With {joined}"


def citation(p):
    """
    Venue, volume/pages, year — with status as a parenthetical rather than a
    badge. 'Cambridge University Press (forthcoming 2027)' should read the same
    way as 'Michigan Law Review 123:800 (2025)'.
    """
    venue = f"<em>{escape(p['venue'])}</em>" if p.get("venue") else ""
    bits = [venue]

    if p.get("editors"):
        bits.append(f"({escape(p['editors'])})")

    vol, pages = p.get("volume"), p.get("pages")
    if vol and pages:
        bits.append(f"{vol}:{pages}")
    elif vol:
        bits.append(str(vol))

    status, year = p.get("status"), p.get("year")
    if status == "forthcoming":
        bits.append(f"(forthcoming {year})" if year else "(forthcoming)")
    elif status == "accepted":
        bits.append(f"(accepted, {year})" if year else "(accepted)")
    elif year:
        bits.append(f"({year})")

    out = " ".join(b for b in bits if b)
    if p.get("peer_reviewed"):
        out += " &nbsp;·&nbsp; peer reviewed"
    return out


def entry_html(p, links, kind_label=None, show_syn=True, show_notes=True):
    """One publication block: title, meta line, synopsis, then any notes.

    Drafted synopses stay in publications.json even when they are not shown, so
    turning them back on is a one-line change in site.json rather than a rewrite.
    """
    title = escape(p["title"])
    body = [f'<article class="pub{" book" if p.get("kind") == "book" else ""}">']

    if kind_label:
        body.append(f'<span class="kind">{escape(kind_label)}</span>')

    body.append(f'<span class="t">{link(title, p.get("url", ""))}</span>')

    meta = [x for x in (coauthor_html(p.get("coauthors", []), links), citation(p)) if x]
    if p.get("ssrn") and p.get("url") and "ssrn" not in p["url"]:
        meta.append(link("SSRN", p["ssrn"]))
    if meta:
        body.append(f'<p class="meta">{" &nbsp;·&nbsp; ".join(meta)}</p>')

    if show_syn and p.get("synopsis"):
        body.append(f'<p class="syn">{p["synopsis"]}</p>')

    # The homepage is a highlight reel; prizes and workshop selections belong on
    # the full research list rather than under the five featured pieces.
    if show_notes:
        for n in p.get("notes", []):
            body.append(f'<p class="note">{escape(n)}</p>')

    body.append("</article>")
    return "\n".join(body)


# ------------------------------------------------------------------- shell


def page(site, title, main, path, description=None, nav_on=None):
    desc = description or site["meta_description"]
    sz = site.get("portrait_size", 148)
    canonical = site["domain"] + path
    nav = []
    for n in site["nav"]:
        on = ' class="on"' if n["label"] == nav_on else ""
        ext = ' target="_blank" rel="noopener"' if n.get("external") else ""
        nav.append(f'<a href="{n["href"]}"{on}{ext}>{escape(n["label"])}</a>')

    ld = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": site["name"],
        "url": site["domain"],
        "email": site["email"],
        "jobTitle": "W. Ronald Robins Professor of Law",
        "affiliation": {"@type": "Organization", "name": "University of Houston Law Center"},
        "sameAs": site["same_as"],
    }

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<meta name="description" content="{escape(desc, quote=True)}">
<meta property="og:title" content="{escape(title, quote=True)}">
<meta property="og:description" content="{escape(desc, quote=True)}">
<meta property="og:type" content="profile">
<meta property="og:image" content="{site['domain']}/og-image.jpg">
<meta property="og:url" content="{canonical}">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{canonical}">
<link rel="stylesheet" href="/style.css">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.png" sizes="64x64" type="image/png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<script type="application/ld+json">{json.dumps(ld)}</script>
</head>
<body>
<div class="shell">
  <aside class="rail">
    <img class="portrait" src="{site['headshot']}" alt="{escape(site['name'], quote=True)}" width="{sz}" height="{sz}">
    <h1 class="brand"><a href="/">{escape(site['name'])}</a></h1>
    <nav>{"".join(nav)}</nav>
  </aside>
  <main>
{main}
  </main>
</div>
</body>
</html>
"""


# ------------------------------------------------------------------- pages


def build_index(site, pubs):
    links = site["coauthor_links"]
    show = site.get("show_synopses", True)

    bio = []
    for para in site["bio"]:
        t = para
        for key, (label, url) in site["bio_links"].items():
            t = t.replace("{" + key + "}", link(escape(label), url))
        # Cloudflare rewrites mailto: into a script-decoded placeholder. With a
        # strict CSP that script is blocked and the address renders as
        # "[email protected]" to every visitor, permanently.
        t = t.replace(
            "{email}",
            f'<!--email_off--><a href="mailto:{site["email"]}">{site["email"]}</a><!--email_on-->',
        )
        bio.append(f"<p>{t}</p>")

    # Works in progress can be featured too, labelled so they do not read as
    # published work.
    highlights = [(p, "Book" if p.get("kind") == "book" else None)
                  for p in pubs["publications"] if p.get("highlight")]
    highlights += [(p, "Work in progress")
                   for p in pubs["works_in_progress"] if p.get("highlight")]
    body = [f'<section class="intro">\n{chr(10).join(bio)}\n</section>']
    body.append('<section>\n<h2 class="section">Selected work</h2>')
    for p, label in highlights:
        body.append(entry_html(p, links, label, show, show_notes=False))
    body.append('<p class="more">' + link("All research →", "/research/") + "</p>")
    body.append("</section>")
    return "\n".join(body)


def build_research(site, pubs):
    links = site["coauthor_links"]
    show = site.get("show_synopses", True)
    themes = pubs["_themes"]
    body = ['<section>\n<h1 class="section">Research</h1>']

    wip = pubs["works_in_progress"]
    if wip:
        body.append('<h3 class="group">Works in progress</h3>')
        for p in sorted(wip, key=lambda x: x["title"]):
            body.append(entry_html(p, links, None, show))

    def sort_key(p):
        # forthcoming first, then most recent
        return (0 if p.get("status") in ("forthcoming", "accepted") else 1, -(p.get("year") or 0))

    for key, label in themes.items():
        group = [p for p in pubs["publications"] if p.get("theme") == key]
        if not group:
            continue
        body.append(f'<h3 class="group">{escape(label)}</h3>')
        for p in sorted(group, key=sort_key):
            body.append(entry_html(p, links, "Book" if p.get("kind") == "book" else None, show))

    body.append("</section>")
    return "\n".join(body)


def build_writing(site, pubs):
    links = site["coauthor_links"]
    body = ['<section>\n<h1 class="section">Public writing</h1>']
    for p in sorted(pubs["popular"], key=lambda x: (-(x.get("year") or 0), x["title"])):
        title = escape(p["title"])
        meta = [x for x in (coauthor_html(p.get("coauthors", []), links),
                            f"<em>{escape(p['venue'])}</em> ({escape(p.get('date') or str(p.get('year')))})") if x]
        body.append(
            f'<article class="pub">\n<span class="t">{link(title, p.get("url", ""))}</span>\n'
            f'<p class="meta">{" &nbsp;·&nbsp; ".join(meta)}</p>\n</article>'
        )
    body.append("</section>")
    return "\n".join(body)


def build_talks(site, data):
    body = ['<section>\n<h1 class="section">Talks</h1>']
    for t in sorted(data["talks"], key=lambda x: x["sort"], reverse=True):
        body.append(
            f'<div class="talk"><div class="w">{escape(t["work"])} '
            f'<span>{escape(t["venue"])}</span></div>'
            f'<div class="d">{escape(t["date"])}</div></div>'
        )
    body.append("</section>")

    body.append('<section>\n<h2 class="section">Selected media</h2>')
    for m in sorted(data["media"], key=lambda x: x["sort"], reverse=True):
        w = link(escape(m["work"]), m.get("url", ""))
        who = f'{escape(m["byline"])}, ' if m.get("byline") else ""
        body.append(
            f'<div class="talk"><div class="w">{w} '
            f'<span>{who}{escape(m["venue"])}</span></div>'
            f'<div class="d">{escape(m["date"])}</div></div>'
        )
    body.append("</section>")
    return "\n".join(body)


# -------------------------------------------------------------------- main


def write(path, text):
    full = os.path.join(PUBLIC, path.lstrip("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(text)
    return full


def main():
    site, pubs, talks = load("site.json"), load("publications.json"), load("talks.json")

    if "--check" in sys.argv:
        pubs_by_id = {e["id"]: e for g in ("publications", "works_in_progress", "popular")
                      for e in pubs[g]}
        # An entry with no_link_reason is a decision, not an omission. Keeping
        # them explicit is what stops --check from crying wolf on every run.
        missing_url, missing_syn, deliberate = [], [], []
        for grp in ("publications", "works_in_progress", "popular"):
            for p in pubs[grp]:
                if not p.get("url"):
                    (deliberate if p.get("no_link_reason") else missing_url).append(p["id"])
                if grp != "popular" and not p.get("synopsis"):
                    missing_syn.append(p["id"])
        print(f"{len(missing_url)} without a link: {', '.join(missing_url) or '—'}")
        for i in deliberate:
            print(f"  (deliberately unlinked: {i} — {pubs_by_id[i]['no_link_reason']})")
        print(f"{len(missing_syn)} without a synopsis: {', '.join(missing_syn) or '—'}")
        return 1 if missing_url else 0

    os.makedirs(PUBLIC, exist_ok=True)

    write("index.html", page(site, site["name"],
          build_index(site, pubs), "/"))
    write("research/index.html", page(site, f"Research — {site['name']}",
          build_research(site, pubs), "/research/", nav_on="Research"))
    write("writing/index.html", page(site, f"Public writing — {site['name']}",
          build_writing(site, pubs), "/writing/", nav_on="Public writing"))
    write("talks/index.html", page(site, f"Talks — {site['name']}",
          build_talks(site, talks), "/talks/", nav_on="Talks"))

    # Cloudflare Pages serves the homepage with a 200 for unmatched paths, so
    # every typo becomes a soft 404 that search engines index as duplicate
    # content. A real 404.html makes it return a real 404.
    write("404.html", page(site, f"Not found — {site['name']}",
          '<section class="intro"><p>That page does not exist. '
          '<a href="/">Return to the homepage</a>.</p></section>', "/404.html"))

    for f in os.listdir(ASSETS):
        if not f.startswith("."):
            shutil.copy2(os.path.join(ASSETS, f), os.path.join(PUBLIC, f))

    n = sum(len(pubs[g]) for g in ("publications", "works_in_progress", "popular"))
    linked = len(re.findall(r'href="http', open(os.path.join(PUBLIC, "research/index.html")).read()))
    print(f"built {n} entries across 5 pages; {linked} outbound links on /research/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
