"""
Free ESPN public API client (no key required).
Covers NFL, CFL, NBA, WNBA, MLB, NHL and more.

Base: https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/...
"""
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta


class ESPNClient:
    BASE = "https://site.api.espn.com/apis/site/v2/sports"

    # sport / league slugs
    LEAGUES = {
        "NFL": ("football", "nfl"),
        "CFL": ("football", "cfl"),
        "NBA": ("basketball", "nba"),
        "WNBA": ("basketball", "wnba"),
        "MLB": ("baseball", "mlb"),
        "NHL": ("hockey", "nhl"),
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "SportsPropsApp/1.0"})

    def scoreboard(self, sport: str, league: str, date: Optional[str] = None) -> List[Dict]:
        """Get games for a date (YYYYMMDD) or today."""
        url = f"{self.BASE}/{sport}/{league}/scoreboard"
        params = {}
        if date:
            params["dates"] = date
        try:
            resp = self.session.get(url, params=params, timeout=12)
            resp.raise_for_status()
            data = resp.json()
            return data.get("events", [])
        except Exception:
            return []

    def teams(self, sport: str, league: str) -> List[Dict]:
        url = f"{self.BASE}/{sport}/{league}/teams"
        try:
            resp = self.session.get(url, timeout=12)
            resp.raise_for_status()
            return resp.json().get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
        except Exception:
            return []

    def game_summary(self, sport: str, league: str, event_id: str) -> Optional[Dict]:
        """Full summary including box score when available."""
        url = f"{self.BASE}/{sport}/{league}/summary"
        try:
            resp = self.session.get(url, params={"event": event_id}, timeout=12)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None

    def recent_games(self, sport: str, league: str, days_back: int = 7) -> List[Dict]:
        """Pull scoreboards for the last N days."""
        games = []
        today = datetime.utcnow().date()
        for i in range(days_back):
            d = (today - timedelta(days=i)).strftime("%Y%m%d")
            games.extend(self.scoreboard(sport, league, d))
        return games

    def league_for_sport(self, sport_name: str) -> Optional[tuple]:
        return self.LEAGUES.get(sport_name.upper())
