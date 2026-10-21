"""
Daily CSV export using free ESPN public endpoints.
Run once a day (cron, Task Scheduler, or manually) to pull scores and schedules.

Usage:
  python daily_export.py              # today's games for all leagues
  python daily_export.py --days 3     # last 3 days
  python daily_export.py --leagues NFL,NBA

Output: data/exports/YYYY-MM-DD_<league>.csv
"""
import argparse
import csv
from datetime import datetime, timedelta
from pathlib import Path
from data.espn_client import ESPNClient

EXPORT_DIR = Path(__file__).parent / "data" / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

LEAGUES = {
    "NFL": ("football", "nfl"),
    "CFL": ("football", "cfl"),
    "NBA": ("basketball", "nba"),
    "WNBA": ("basketball", "wnba"),
    "MLB": ("baseball", "mlb"),
    "NHL": ("hockey", "nhl"),
}


def flatten_event(event: dict) -> dict:
    """Turn an ESPN scoreboard event into a flat row."""
    competitions = event.get("competitions", [{}])
    comp = competitions[0] if competitions else {}
    competitors = comp.get("competitors", [])

    home = next((c for c in competitors if c.get("homeAway") == "home"), {})
    away = next((c for c in competitors if c.get("homeAway") == "away"), {})

    status = event.get("status", {}).get("type", {})

    return {
        "event_id": event.get("id"),
        "date": event.get("date", "")[:10],
        "name": event.get("name"),
        "short_name": event.get("shortName"),
        "status": status.get("name"),
        "status_detail": status.get("detail"),
        "completed": status.get("completed", False),
        "home_team": home.get("team", {}).get("displayName"),
        "home_abbrev": home.get("team", {}).get("abbreviation"),
        "home_score": home.get("score"),
        "away_team": away.get("team", {}).get("displayName"),
        "away_abbrev": away.get("team", {}).get("abbreviation"),
        "away_score": away.get("score"),
        "venue": comp.get("venue", {}).get("fullName"),
        "broadcast": ", ".join(
            b.get("names", [""])[0] for b in comp.get("broadcasts", []) if b.get("names")
        ),
    }


def export_league(client: ESPNClient, league_name: str, days: int = 1) -> int:
    sport, league = LEAGUES[league_name]
    rows = []
    today = datetime.utcnow().date()

    for i in range(days):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
        events = client.scoreboard(sport, league, d)
        for ev in events:
            row = flatten_event(ev)
            row["league"] = league_name
            rows.append(row)

    if not rows:
        print(f"  {league_name}: no games")
        return 0

    filename = EXPORT_DIR / f"{today.isoformat()}_{league_name.lower()}.csv"
    fieldnames = list(rows[0].keys())

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"  {league_name}: {len(rows)} games → {filename.name}")
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description="Daily ESPN scoreboard CSV export")
    parser.add_argument("--days", type=int, default=1, help="How many days back to pull")
    parser.add_argument(
        "--leagues",
        type=str,
        default=",".join(LEAGUES.keys()),
        help="Comma-separated list (e.g. NFL,NBA,NHL)",
    )
    args = parser.parse_args()

    leagues = [l.strip().upper() for l in args.leagues.split(",") if l.strip()]
    client = ESPNClient()

    print(f"Exporting last {args.days} day(s) for: {', '.join(leagues)}")
    print(f"Output folder: {EXPORT_DIR}\n")

    total = 0
    for name in leagues:
        if name not in LEAGUES:
            print(f"  Skipping unknown league: {name}")
            continue
        total += export_league(client, name, args.days)

    print(f"\nDone. {total} total rows written.")


if __name__ == "__main__":
    main()
