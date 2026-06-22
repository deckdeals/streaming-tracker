#!/usr/bin/env python3
"""
Streaming & TV Tracker — static site builder.

Fetches this week's streaming premieres and TV schedule from the free TVmaze API
and generates a static website into ./public. No API key needed.

Data source: https://www.tvmaze.com/api  (free; no key)

Run locally:   python3 build.py
The GitHub Action runs this daily and publishes ./public to the web.
"""

import html
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta

API = "https://api.tvmaze.com"
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "public")

SITE_NAME = "What's New on Streaming"
TAGLINE = "New streaming releases, season premieres, and what's on TV — updated daily."

SITE_URL = (os.environ.get("SITE_URL") or "https://deckdeals.github.io/streaming-tracker").rstrip("/")
ADSENSE_CLIENT = os.environ.get("ADSENSE_CLIENT", "").strip()
GOOGLE_VERIFY = os.environ.get("GOOGLE_VERIFY", "").strip()

USER_AGENT = "StreamingTracker/1.0 (static site generator)"


def fetch_json(url, retries=4):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last}")


def fetch_range(path_tmpl, days):
    """Fetch a TVmaze schedule endpoint across several dates, concatenated."""
    out = []
    for d in days:
        try:
            out.extend(fetch_json(path_tmpl.format(date=d.isoformat())))
        except Exception as e:
            print(f"warning: schedule {d} failed ({e})", file=sys.stderr)
        time.sleep(0.4)  # polite to TVmaze
    return out


def get_show(item):
    return item.get("show") or (item.get("_embedded") or {}).get("show") or {}


def platform(show):
    wc = show.get("webChannel") or {}
    nw = show.get("network") or {}
    return wc.get("name") or nw.get("name") or ""


def dedup_by_show(items, premieres_first=True):
    seen, out = set(), []
    ordered = items
    if premieres_first:
        ordered = sorted(items, key=lambda it: 0 if it.get("number") == 1 else 1)
    for it in ordered:
        s = get_show(it)
        sid = s.get("id")
        if not sid or sid in seen:
            continue
        seen.add(sid)
        out.append(it)
    return out


def show_card(item):
    s = get_show(item)
    name = html.escape(s.get("name", "Untitled"))
    img = html.escape((s.get("image") or {}).get("medium") or (s.get("image") or {}).get("original") or "")
    url = html.escape(s.get("url", "#"))
    plat = html.escape(platform(s))
    genres = ", ".join(html.escape(g) for g in (s.get("genres") or [])[:3])
    rating = (s.get("rating") or {}).get("average")
    is_premiere = item.get("number") == 1
    badges = ""
    if is_premiere:
        badges += '<span class="prem">Premiere</span>'
    if rating:
        badges += f'<span class="rating">★ {rating}</span>'
    poster = f'<img class="poster" src="{img}" alt="{name}" loading="lazy">' if img else '<div class="poster ph"></div>'

    return f"""
    <a class="card" href="{url}" rel="nofollow noopener" target="_blank">
      <div class="poster-wrap">{poster}<div class="badges">{badges}</div></div>
      <div class="body">
        <div class="title">{name}</div>
        <div class="plat">{plat}</div>
        <div class="genres">{genres}</div>
      </div>
    </a>"""


def jsonld(items):
    li = []
    for i, it in enumerate(items[:20], start=1):
        s = get_show(it)
        li.append({"@type": "ListItem", "position": i, "name": s.get("name", ""),
                   "url": s.get("url", "")})
    data = {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": li}
    return '<script type="application/ld+json">' + json.dumps(data) + "</script>"


def adsense_head():
    if not ADSENSE_CLIENT:
        return ""
    return ('<script async crossorigin="anonymous" '
            f'src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={html.escape(ADSENSE_CLIENT)}">'
            "</script>")


CSS = """
:root{--bg:#0a0f0d;--card:#13201b;--text:#eaf3ee;--muted:#94b3a6;--accent:#34d399;--accent2:#10b981}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);
font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
a{color:inherit;text-decoration:none}
header{padding:28px 20px 8px;text-align:center}
header h1{margin:0;font-size:1.7rem}
header p{color:var(--muted);margin:.4rem 0 0}
nav{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;padding:16px 14px}
nav a{background:var(--card);padding:8px 14px;border-radius:999px;font-size:.9rem;border:1px solid #22382e}
nav a:hover,nav a.active{background:var(--accent2);color:#04231a;border-color:var(--accent2)}
main{max-width:1100px;margin:0 auto;padding:8px 16px 40px}
.intro{color:var(--muted);max-width:760px;margin:6px auto 18px;text-align:center}
.updated{color:var(--muted);font-size:.82rem;text-align:center;margin-bottom:18px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:16px}
.card{background:var(--card);border-radius:12px;overflow:hidden;border:1px solid #20342b;
transition:transform .08s ease,border-color .08s ease}
.card:hover{transform:translateY(-3px);border-color:var(--accent2)}
.poster-wrap{position:relative;aspect-ratio:2/3;background:#0f1814;overflow:hidden}
.poster{width:100%;height:100%;object-fit:cover;display:block}
.poster.ph{background:#16241d}
.badges{position:absolute;top:8px;left:8px;right:8px;display:flex;justify-content:space-between;gap:6px}
.prem{background:var(--accent2);color:#04231a;font-size:.72rem;font-weight:700;padding:3px 7px;border-radius:6px}
.rating{margin-left:auto;background:rgba(0,0,0,.75);color:#ffd86b;font-size:.76rem;font-weight:700;padding:3px 7px;border-radius:6px}
.body{padding:10px 12px 13px}
.title{font-weight:600;font-size:.95rem;line-height:1.25;
display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-height:2.4em}
.plat{color:var(--accent);font-size:.8rem;margin-top:6px}
.genres{color:var(--muted);font-size:.78rem;margin-top:4px;
display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden}
footer{color:var(--muted);font-size:.8rem;text-align:center;padding:28px 16px;border-top:1px solid #1a2b23;margin-top:20px}
footer a{color:var(--accent)}
.empty{text-align:center;color:var(--muted);padding:60px 20px}
"""


def render_page(page, items, pages, now):
    nav = "".join(
        f'<a href="{("index.html" if p["slug"]=="index" else p["slug"]+".html")}" '
        f'class="{"active" if p["slug"]==page["slug"] else ""}">{html.escape(p["h1"])}</a>'
        for p in pages)
    canonical = f'{SITE_URL}/{"" if page["slug"]=="index" else page["slug"]+".html"}'
    verify_meta = (f'<meta name="google-site-verification" content="{html.escape(GOOGLE_VERIFY)}">'
                   if GOOGLE_VERIFY else "")
    cards = "".join(show_card(it) for it in items) if items else \
        '<div class="empty">Nothing loaded this run — check back after the next update.</div>'

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
{verify_meta}
<title>{html.escape(page["title"])}</title>
<meta name="description" content="{html.escape(page["desc"])}">
<link rel="canonical" href="{html.escape(canonical)}">
<meta property="og:title" content="{html.escape(page["title"])}">
<meta property="og:description" content="{html.escape(page["desc"])}">
<meta property="og:type" content="website">
{adsense_head()}
<style>{CSS}</style>
{jsonld(items)}
</head>
<body>
<header><h1>{html.escape(page["h1"])}</h1><p>{html.escape(TAGLINE)}</p></header>
<nav>{nav}</nav>
<main>
  <p class="intro">{html.escape(page["intro"])}</p>
  <p class="updated">Last updated {now.strftime('%B %d, %Y at %H:%M UTC')}</p>
  <div class="grid">{cards}</div>
</main>
<footer>
  <p>Updated automatically every day.</p>
  <p>TV &amp; streaming data from <a href="https://www.tvmaze.com" rel="noopener" target="_blank">TVmaze</a>.</p>
</footer>
</body>
</html>"""


def write_sitemap(pages, now):
    urls = []
    for p in pages:
        loc = f'{SITE_URL}/{"" if p["slug"]=="index" else p["slug"]+".html"}'
        urls.append(f"<url><loc>{html.escape(loc)}</loc>"
                    f"<lastmod>{now.strftime('%Y-%m-%d')}</lastmod>"
                    f"<changefreq>daily</changefreq></url>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(urls) + "</urlset>")
    with open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(xml)
    with open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")


def main():
    os.makedirs(OUT, exist_ok=True)
    now = datetime.now(timezone.utc)
    today = now.date()
    week = [today + timedelta(days=i) for i in range(7)]

    web_week = fetch_range(API + "/schedule/web?date={date}", week)
    us_week = fetch_range(API + "/schedule?country=US&date={date}", week)

    streaming = dedup_by_show(web_week, premieres_first=True)[:60]
    today_tv = dedup_by_show([it for it in us_week if it.get("airdate") == today.isoformat()],
                             premieres_first=False)[:60]
    premieres = dedup_by_show([it for it in (web_week + us_week) if it.get("number") == 1],
                              premieres_first=True)[:60]

    pages = [
        {"slug": "index", "items": streaming,
         "h1": "New on Streaming This Week",
         "title": "What's New on Streaming This Week — Netflix, Prime & More",
         "desc": "New streaming releases and episodes dropping this week across "
                 "Netflix, Prime Video, Disney+, Hulu and more. Updated daily.",
         "intro": "New shows and episodes hitting streaming this week, premieres first."},
        {"slug": "tv-tonight", "items": today_tv,
         "h1": "On TV Tonight",
         "title": "What's On TV Tonight — US TV Schedule",
         "desc": "Tonight's US TV schedule — what's airing today across all networks. "
                 "Updated daily.",
         "intro": "Everything airing on US TV today."},
        {"slug": "season-premieres", "items": premieres,
         "h1": "Season & Series Premieres This Week",
         "title": "Season & Series Premieres This Week (TV & Streaming)",
         "desc": "Every season and series premiere this week across TV and streaming. "
                 "Updated daily.",
         "intro": "Brand-new shows and returning seasons premiering this week."},
    ]

    for page in pages:
        fname = "index.html" if page["slug"] == "index" else f'{page["slug"]}.html'
        with open(os.path.join(OUT, fname), "w", encoding="utf-8") as f:
            f.write(render_page(page, page["items"], pages, now))
        print(f"built {fname} ({len(page['items'])} shows)")

    write_sitemap(pages, now)
    print(f"done -> {OUT}")


if __name__ == "__main__":
    main()
