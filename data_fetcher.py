"""
Data fetching layer with real The Odds API support + mock fallback.
"""
import os
import json
import requests
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from data.stats_enricher import StatsEnricher
from models.models import (
    Player, PlayerProp, PropLine, HistoricalStat,
    Sport, Platform, MarketType
)

DATA_DIR = Path(__file__).parent

# The Odds API sport keys
SPORT_KEY_MAP = {
    Sport.NBA: "basketball_nba",
    Sport.NFL: "americanfootball_nfl",
    Sport.MLB: "baseball_mlb",
    Sport.NHL: "icehockey_nhl",
    Sport.CFL: "americanfootball_cfl",
}

# Markets we care about per sport (The Odds API keys)
MARKET_MAP = {
    Sport.NBA: {
        "player_points": MarketType.POINTS,
        "player_rebounds": MarketType.REBOUNDS,
        "player_assists": MarketType.ASSISTS,
        "player_threes": MarketType.THREES,
    },
    Sport.NFL: {
        "player_pass_yds": MarketType.PASSING_YARDS,
        "player_rush_yds": MarketType.RUSHING_YARDS,
        "player_reception_yds": MarketType.RECEIVING_YARDS,
        "player_receptions": MarketType.RECEPTIONS,
    },
    Sport.MLB: {
        "batter_hits": MarketType.HITS,
        "pitcher_strikeouts": MarketType.STRIKEOUTS,
    },
    Sport.NHL: {
        "player_goals": MarketType.GOALS,
        "player_shots_on_goal": MarketType.SHOTS,
    },
}

# Bookmaker keys we want (The Odds API keys)
TARGET_BOOKS = {
    "prizepicks": Platform.PRIZEPICKS,
    "underdog": Platform.UNDERDOG,
    "underdogfantasy": Platform.UNDERDOG,
    "sleeper": Platform.SLEEPER,
    "kalshi": Platform.KALSHI,
}


class DataFetcher:
    """Pulls player props from The Odds API or falls back to mock data."""

    def __init__(self, use_mock: bool = None, api_key: str = None):
        self.api_key = api_key or os.getenv("ODDS_API_KEY")
        # Auto-decide: use mock if no key
        if use_mock is None:
            self.use_mock = not bool(self.api_key)
        else:
            self.use_mock = use_mock
        self.base_url = "https://api.the-odds-api.com/v4"
        self.enricher = StatsEnricher()

    def get_player_props(self, sport: Sport, limit: int = 40) -> List[PlayerProp]:
        if self.use_mock or not self.api_key:
            print(f"[DataFetcher] Using mock data for {sport.value} (no ODDS_API_KEY or forced mock)")
            return self._load_mock_props(sport, limit)

        try:
            return self._fetch_odds_api(sport, limit)
        except Exception as e:
            print(f"[DataFetcher] Real API failed ({e}). Falling back to mock data.")
            return self._load_mock_props(sport, limit)

    def _fetch_odds_api(self, sport: Sport, limit: int) -> List[PlayerProp]:
        """Fetch live props from The Odds API and map to our models."""
        sport_key = SPORT_KEY_MAP.get(sport)
        if not sport_key:
            raise ValueError(f"No sport key mapped for {sport}")

        markets = list(MARKET_MAP.get(sport, {}).keys())
        if not markets:
            raise ValueError(f"No markets defined for {sport}")

        # 1. Get upcoming events
        events_url = f"{self.base_url}/sports/{sport_key}/events"
        resp = requests.get(events_url, params={"apiKey": self.api_key}, timeout=15)
        resp.raise_for_status()
        events = resp.json()[:8]  # limit events to control credit usage

        props_dict: Dict[str, PlayerProp] = {}

        for event in events:
            event_id = event["id"]
            # 2. Get player props for this event
            odds_url = f"{self.base_url}/sports/{sport_key}/events/{event_id}/odds"
            params = {
                "apiKey": self.api_key,
                "regions": "us,us_dfs",
                "markets": ",".join(markets),
                "oddsFormat": "american",
                "bookmakers": "prizepicks,underdog,underdogfantasy,sleeper,kalshi",
            }
            try:
                odds_resp = requests.get(odds_url, params=params, timeout=15)
                odds_resp.raise_for_status()
                data = odds_resp.json()
            except Exception as e:
                print(f"  Skipping event {event_id}: {e}")
                continue

            # Parse bookmakers → props
            for bookmaker in data.get("bookmakers", []):
                book_key = bookmaker.get("key", "").lower()
                platform = TARGET_BOOKS.get(book_key)
                if not platform:
                    continue

                for market in bookmaker.get("markets", []):
                    market_key = market.get("key")
                    market_type = MARKET_MAP.get(sport, {}).get(market_key)
                    if not market_type:
                        continue

                    for outcome in market.get("outcomes", []):
                        player_name = outcome.get("description") or outcome.get("name")
                        if not player_name or player_name.lower() in ("over", "under"):
                            continue

                        point = outcome.get("point")
                        if point is None:
                            continue

                        direction = "over" if "over" in (outcome.get("name") or "").lower() else "under"
                        # Some DFS books only return one side
                        if "over" not in (outcome.get("name") or "").lower() and "under" not in (outcome.get("name") or "").lower():
                            direction = "over"

                        prop_id = f"{sport.value}_{player_name}_{market_type.value}".replace(" ", "_").lower()

                        if prop_id not in props_dict:
                            props_dict[prop_id] = PlayerProp(
                                id=prop_id,
                                player=Player(
                                    id=player_name.lower().replace(" ", "_"),
                                    name=player_name,
                                    team=event.get("home_team", "UNK"),  # rough; improve later
                                    position="",
                                    sport=sport,
                                ),
                                market=market_type,
                                lines=[],
                                historical=[],  # stats source can be added later
                            )

                        props_dict[prop_id].lines.append(
                            PropLine(
                                platform=platform,
                                line=float(point),
                                odds=outcome.get("price"),
                                direction=direction,
                            )
                        )

            if len(props_dict) >= limit:
                break

        props = list(props_dict.values())[:limit]
        # Attach historical stats for hit rates
        props = self.enricher.enrich(props)
        print(f"[DataFetcher] Fetched {len(props)} live props for {sport.value}")
        return props

    def _load_mock_props(self, sport: Sport, limit: int) -> List[PlayerProp]:
        mock_file = DATA_DIR / "mock_props.json"
        if not mock_file.exists():
            return self._generate_sample_props(sport)

        with open(mock_file) as f:
            raw = json.load(f)

        props = []
        for item in raw.get(sport.value, [])[:limit]:
            player = Player(
                id=item["player"]["id"],
                name=item["player"]["name"],
                team=item["player"]["team"],
                position=item["player"]["position"],
                sport=sport,
            )
            lines = [
                PropLine(
                    platform=Platform(l["platform"]),
                    line=l["line"],
                    odds=l.get("odds"),
                    direction=l.get("direction", "over"),
                )
                for l in item.get("lines", [])
            ]
            historical = [
                HistoricalStat(
                    date=h["date"],
                    value=h["value"],
                    opponent=h["opponent"],
                    home=h.get("home", True),
                )
                for h in item.get("historical", [])
            ]
            props.append(
                PlayerProp(
                    id=item["id"],
                    player=player,
                    market=MarketType(item["market"]),
                    lines=lines,
                    historical=historical,
                )
            )
        return props

    def _generate_sample_props(self, sport: Sport) -> List[PlayerProp]:
        # kept for completeness; mock file is preferred
        return []
