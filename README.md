# Sports Props Analysis App

Scaffold for a player-props analysis and line-shopping tool.

Supports **live data** from The Odds API (PrizePicks, Underdog, Sleeper, Kalshi and more) with automatic fallback to mock data.

## Quick start (mock data)

```bash
cd sports_props_app
pip install -r requirements.txt
python main.py
```

## Live data (The Odds API)

1. Get a free API key: https://the-odds-api.com/
2. Copy `.env.example` to `.env` and add your key:
   ```
   ODDS_API_KEY=your_key_here
   ```
3. Run again: `python main.py`

**Notes on free tier:**
- Free plans are limited (credits per month).
- Full player-prop coverage (especially DFS sites) often requires a paid plan.
- The app automatically falls back to mock data if the key is missing or the API returns an error.

## Project structure

```
sports_props_app/
├── main.py
├── .env.example
├── requirements.txt
├── models/models.py
├── data/
│   ├── data_fetcher.py      # Real API + mock
│   └── mock_props.json
└── analysis/
    ├── analyzer.py
    └── parlay_builder.py
```

## Free daily sources (including ESPN)
| Sport | Primary free source | Notes |
|-------|---------------------|-------|
| All   | **ESPN public API** (`site.api.espn.com`) | No key. Scoreboards, teams, summaries for NFL, CFL, NBA, MLB, NHL, WNBA |
| NFL   | nflverse weekly CSVs + ESPN | Nightly player stats |
| NBA   | nba_api or balldontlie + ESPN | |
| MLB   | statsapi.mlb.com + ESPN | |
| NHL   | api-web.nhle.com + ESPN | |

## Web UI (Streamlit)
```bash
pip install -r requirements.txt
streamlit run ui.py
```
Opens in your browser. No Terminal needed after that.
| Source | Method | Status |
|--------|--------|--------|
| The Odds API | Official API (free tier) | Preferred — already integrated |
| Kalshi | Official public market API | Working (no key) |
| PrizePicks / Underdog / Sleeper | No public API | Not scraped (ToS + blocks) |

See `data/odds_scraper.py`. Use The Odds API key in `.env` for reliable DFS lines.
Pull scores and schedules into CSVs with no API key:

```bash
python daily_export.py                  # today, all leagues
python daily_export.py --days 3         # last 3 days
python daily_export.py --leagues NFL,NBA
```

Files are written to `data/exports/YYYY-MM-DD_<league>.csv`.

Schedule it daily with cron, Windows Task Scheduler, or a simple loop.

## Next steps
- Add a free stats source for historical hit rates (balldontlie, MLB Stats API, etc.)
- FastAPI or Streamlit UI
- Smarter correlation and under-side analysis
- Export to CSV/JSON

## Disclaimer
Analysis tool only — not financial or gambling advice. Include responsible-gambling messaging in any production version.
