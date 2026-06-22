# What's New on Streaming

Automated, $0 site listing new streaming releases, season premieres, and what's
on TV — updated daily. Same engine as the game-deals site.

- **Data:** [TVmaze API](https://www.tvmaze.com/api) — free, no key.
- **Build:** `build.py` (Python standard library only).
- **Hosting + daily cron:** GitHub Actions → GitHub Pages (free).
- **Money:** Google AdSense + where-to-watch affiliate (later).

Run locally: `python3 build.py`, then open `public/index.html`.

Optional repo Variables (Settings → Secrets and variables → Actions → Variables):
`SITE_URL`, `ADSENSE_CLIENT`, `GOOGLE_VERIFY` — all optional; the site builds
without them.

TV & streaming data from TVmaze.
