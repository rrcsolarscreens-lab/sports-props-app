"""
Modular odds scrapers.
- Kalshi: uses official public API (no key required for market data)
- PrizePicks / Underdog / Sleeper: no public API; stubs with warnings
  (scraping these sites is fragile, often blocked, and may violate ToS)

Prefer The Odds API (already integrated in data_fetcher.py) for DFS lines.
"""
import requests
from typing import List, Dict, Optional
from datetime import datetime
from models.models import PlayerProp, Player, PropLine, Sport, MarketType, Platform


class OddsScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "SportsPropsApp/1.0 (educational)",
            "Accept": "application/json",
        })

    def fetch_all(self, sport: Sport) -> List[PlayerProp]:
        """Try all sources. Returns whatever succeeds."""
        props = []
        props.extend(self._kalshi(sport))
        # DFS sites intentionally left as stubs — use The Odds API instead
        return props

    # ---------- Kalshi (public API) ----------
    def _kalshi(self, sport: Sport) -> List[PlayerProp]:
        """Pull open markets from Kalshi that look like player props or game lines."""
        url = "https://api.elections.kalshi.com/trade-api/v2/markets"
        try:
            resp = self.session.get(
                url,
                params={"status": "open", "limit": 200},
                timeout=15,
            )
            resp.raise_for_status()
            markets = resp.json().get("markets", [])
        except Exception as e:
            print(f"  [Kalshi] failed: {e}")
            return []

        props = []
        sport_keywords = {
            Sport.NBA: ["nba", "basketball", "points", "rebounds", "assists"],
            Sport.NFL: ["nfl", "football", "yards", "touchdown", "reception"],
            Sport.MLB: ["mlb", "baseball", "hits", "strikeouts", "home run"],
            Sport.NHL: ["nhl", "hockey", "goals", "assists", "shots"],
        }.get(sport, [])

        for m in markets:
            title = (m.get("title") or "").lower()
            if not any(k in title for k in sport_keywords):
                continue

            # Very rough extraction — Kalshi titles vary
            line_value = self._guess_line(title)
            if line_value is None:
                continue

            player_name = self._guess_player(title)
            if not player_name:
                continue

            prop = PlayerProp(
                id=f"kalshi-{m.get('ticker', '')}",
                player=Player(
                    id="",
                    name=player_name,
                    team="",
                    position="",
                    sport=sport,
                ),
                market=self._guess_market(title),
                lines=[
                    PropLine(
                        platform=Platform.KALSHI,
                        line=line_value,
                        odds=-110,
                        direction="over",
                        last_updated=datetime.utcnow(),
                    )
                ],
            )
            props.append(prop)

        print(f"  [Kalshi] found {len(props)} potential props")
        return props

    def _guess_line(self, title: str) -> Optional[float]:
        import re
        match = re.search(r"(\d+\.?\d*)", title)
        return float(match.group(1)) if match else None

    def _guess_player(self, title: str) -> Optional[str]:
        # Extremely naive — real parsing needs better logic or an external player list
        words = title.split()
        if len(words) >= 2:
            return " ".join(words[:2]).title()
        return None

    def _guess_market(self, title: str) -> MarketType:
        t = title.lower()
        if "point" in t:
            return MarketType.POINTS
        if "assist" in t:
            return MarketType.ASSISTS
        if "rebound" in t:
            return MarketType.REBOUNDS
        if "yard" in t:
            return MarketType.PASSING_YARDS
        if "hit" in t:
            return MarketType.HITS
        if "strike" in t or "k" in t:
            return MarketType.STRIKEOUTS
        return MarketType.POINTS

    # ---------- DFS stubs (do not scrape) ----------
    def _prizepicks(self, sport: Sport) -> List[PlayerProp]:
        print("  [PrizePicks] no public API — use The Odds API instead")
        return []

    def _underdog(self, sport: Sport) -> List[PlayerProp]:
        print("  [Underdog] no public API — use The Odds API instead")
        return []

    def _sleeper(self, sport: Sport) -> List[PlayerProp]:
        print("  [Sleeper] no public API — use The Odds API instead")
        return []
