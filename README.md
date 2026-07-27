# peternsalib.com

Static site. Content lives in `content/*.json`; `build.py` turns it into `public/`,
which is committed so the host needs no build step.

## Updating

1. Edit the JSON in `content/`.
2. `python3 build.py`
3. Commit and push. Live in about 40 seconds.

Never hand-edit anything in `public/` — it is generated and will be overwritten.

## Files

| Path | What it is |
|---|---|
| `content/publications.json` | Every paper. The single source of truth. |
| `content/site.json` | Bio, nav, affiliation links, verified coauthor homepages. |
| `content/talks.json` | Presentations and media appearances. |
| `assets/` | Stylesheet, headshot, CV PDF, favicon, social card. Copied verbatim into `public/`. |
| `build.py` | The generator. Python standard library only, deliberately. |

## Checks

```
python3 build.py --check
```

Lists entries with no link and no synopsis, and exits non-zero if anything is
unlinked. Entries carrying a `no_link_reason` are reported as decisions, not
errors. Run before pushing.

```
python3 drift.py
```

Parses the CV and diffs it against `content/publications.json`, exiting non-zero
on any unexplained difference in either direction. **Run this after every CV
edit** — it is what makes "update the CV, update the site" one action rather
than a good intention. Differences that are deliberate go in `EXPECTED_OFF_SITE`
at the top of the file, with a reason.

## Conventions worth keeping

- **One colour scheme.** Light only. If the site adapted to the visitor's device you
  would never know what impression a reader actually got.
- **Status is a parenthetical, not a badge.** "Cambridge University Press
  (forthcoming 2027)" reads the same way as "Michigan Law Review 123:800 (2025)".
- **Only link a coauthor after verifying them by name *and* field.** An unlinked name
  beats a link to the wrong person. Verified links live in `site.json`.
- **`mailto:` links stay wrapped in `<!--email_off-->` / `<!--email_on-->`.** Cloudflare
  otherwise rewrites them into a script-decoded placeholder that a strict CSP blocks,
  and the address renders as "[email protected]" to every visitor, permanently.
- **`404.html` must exist.** Otherwise Cloudflare Pages serves the homepage with a 200
  for unmatched paths and every typo becomes a soft 404 indexed as duplicate content.
- **No blog, no news feed.** Stale content is worse than absent content.
