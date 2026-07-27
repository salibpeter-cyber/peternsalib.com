# Notes for an agent working on peternsalib.com

Written 27 July 2026, at the end of the rebuild that moved this site off Google Sites.
`README.md` covers the mechanics of building and deploying. This file covers the things
you cannot read off the code: where the source material lives, which decisions were
deliberate, and which traps cost hours the first time.

Peter is a law professor, not a full-time engineer. He reads and edits JSON happily. He
does not want to run a toolchain.

---

## The premise

The old site was not ugly. It was unreachable — the content lived in a Google Sites admin
panel, so keeping it in step with the CV was manual work that never got done. By the time
we rebuilt it the site was missing five publications, three coauthor credits, all 26 talks
and all 20 media appearances.

**The goal is not a prettier site. It is that a CV update and a site update are one action.**
`drift.py` is what makes that true rather than aspirational. If you change how publications
are stored, keep it working.

---

## Where things live

| What | Where |
|---|---|
| This repo | `~/Library/CloudStorage/Dropbox/Claude/Website Update/peternsalib.com` |
| GitHub | `github.com/salibpeter-cyber/peternsalib.com` (public) |
| The CV, canonical | `~/Library/CloudStorage/Dropbox/CV-PeterSalib.docx` (+ `.pdf`) |
| Paper drafts | `~/Library/CloudStorage/Dropbox/Papers/<paper name>/` |
| **Peter's prose style guide** | `~/Library/CloudStorage/Dropbox/Papers/STYLE.md` |
| Original handoff brief | `../Handoff - website rebuild brief for Peter Salib.md` |

**Read `Papers/STYLE.md` before drafting any prose in Peter's voice.** Its governing rule
here: *never edit text Peter wrote himself.* Abstracts and intros are the calibration
target, not the object. Flag typos in them; do not fix them.

`assets/cv.pdf` is a copy. When the CV changes, copy the new PDF over it and rebuild — it
does not update itself.

---

## Infrastructure

- **Registrar:** Automattic / WordPress.com. *Not* Squarespace — the handoff brief assumes
  Squarespace because Simon was on it. Only the domain registration lives there now.
- **DNS:** Cloudflare. Nameservers `brynne.ns.cloudflare.com`, `vern.ns.cloudflare.com`.
- **Hosting:** Cloudflare **Workers Static Assets**, not Pages. The account was only
  offered the Workers path. Config is `wrangler.json`; there is no Worker script, just
  `public/` served as assets.
- **Worker:** `peternsalib-com`, staging URL `peternsalib-com.salib-peter.workers.dev`.
- **Custom domains:** apex and `www`, both attached to the Worker. A Redirect Rule sends
  `www` → apex. Canonical host is the **apex**.
- Push to `main` deploys automatically. Cost: zero.

🛑 **The five Google MX records on this zone are Peter's live email.** Never delete DNS
records without checking what they are. Only three records were ever web-related.

---

## Decisions that were deliberate

Do not "fix" these without asking.

- **Synopses are written but hidden.** 26 entries have a drafted one-line synopsis in
  `publications.json`; `show_synopses: false` in `site.json` keeps them off the page. Peter
  asked for them to come off "for now." Flip the boolean to bring them all back.
- **Coauthors are linked only when verified by name *and* field.** Currently Goldstein,
  Arbel and Krishnamurthi. An unlinked name beats a link to the wrong person. Peter's old
  site is where the verified URLs came from.
- **Two entries are deliberately unlinked**, with reasons recorded in `no_link_reason`:
  AI Nationalization (draft not public yet) and the Dorf on Law post. `build.py --check`
  reports these as decisions, not errors.
- **One colour scheme, light only.** If the site adapted to the visitor's device you would
  never know what impression a funder actually got.
- **Status is a parenthetical, never a badge.** Badges shout.
- **No blog, no news feed.** Stale content is worse than absent content.
- **Layout is adapted from simondgoldstein.com with Simon's explicit permission**; the
  palette (Charter, oxblood) is deliberately different so the two read as siblings.

---

## Traps, in the order they cost time

**Read the source before writing a parser.** The CV parser in `drift.py` was wrong three
ways on the first attempt: award notes are numbered list paragraphs and parsed as titles;
works in progress have no venue and a trailing `(with …)`; and one paragraph holds *two*
entries separated by line breaks rather than paragraph marks. Each was found by dumping the
actual XML. If you touch `cv_titles()`, verify against a known-good state — 54 entries
matching 54 — rather than trusting it.

**Lawfare blocks WebFetch and curl** with a 403. Its contributor page must be read through
a real browser. **SSRN rate-limits** after roughly one scripted request; prefer the local
PDFs in `Papers/` for abstracts.

**Negative DNS caching will lie to you.** After DNS records change, a shell that queried
during the gap caches "no such host" and keeps reporting the site down when it is fine. Use
`curl --resolve host:443:<ip>` to bypass it. Verify the mechanism — the registry, the DNS
answer, the served bytes — rather than waiting and assuming.

**The edge cache lies right after a deploy.** Append a cache-busting query string before
believing any result.

**Peter's Word is the sandboxed App Store build** and its AppleScript dictionary has no
`save as` or `save`. You cannot convert the CV to PDF programmatically. There is no
LibreOffice and no LaTeX on the machine. Ask him to export it, or install something first.

**`escape(url, quote=True)` turns apostrophes into `&#x27;`.** Browsers decode this
correctly; naive link checkers do not. One Lawfare URL will always look broken and isn't.

**Cloudflare's Rules UI cannot see Worker custom domain records.** It will warn that `www`
is not proxied when it is. Choose "ignore and deploy anyway"; creating a second DNS record
would conflict with the one the custom domain owns.

**The www-to-root redirect template's `${1}` already captures path and query.** Leave
"preserve query string" **off** or the query string is duplicated.

---

## Before publishing anything new

Ask whether any funding, affiliation or in-progress work is confidential. On Simon's build
a funder had asked in writing not to be named and it nearly went on the page. Peter has
confirmed everything currently in the CV is public, including CLAIR's funding figure — but
that answer was about today's CV, not tomorrow's.

## Routine

```bash
python3 drift.py        # after every CV edit — must print "No drift."
python3 build.py        # regenerate public/
python3 build.py --check
git add -A && git commit && git push    # live in ~40s
```

Never hand-edit `public/`. It is generated and will be overwritten.
