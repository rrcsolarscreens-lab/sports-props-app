"""
Free stats enricher — daily-updated sources.
Pulls recent game logs so live props can compute hit rates.

Sources (all free):
- NFL: nflverse player stats (GitHub releases, updated nightly)
- NBA: nba_api (official stats.nba.com via community library) or balldontlie
- MLB: statsapi.mlb.com (no key)
- NHL: api-web.nhle.com (no key)
- Fallback: TheSportsDB (free test key)
"""
import os
import io
import requests
import pandas as pd
from typing import List, Optional
from datetime import datetime
from models.models import PlayerProp, HistoricalStat, Sport, MarketType
from data.espn_client import ESPNClient


class StatsEnricher:
    def __init__(self):
        self.balldontlie_key = os.getenv("BALLDONTLIE_API_KEY")
        self.sportsdb_key = os.getenv("SPORTSDB_API_KEY", "3")  # free test key
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "SportsPropsApp/1.0"})
        self._nfl_cache = None

    def enrich(self, props: List[PlayerProp], max_games: int = 10) -> List[PlayerProp]:
        """Attach recent historical stats to each prop where possible."""
        for prop in props:
            try:
                logs = self._get_recent_logs(prop, max_games)
                if logs:
                    prop.historical = logs
            except Exception as e:
                print(f"  [Stats] Could not enrich {prop.player.name}: {e}")
        return props

    def _get_recent_logs(self, prop: PlayerProp, max_games: int) -> List[HistoricalStat]:
        sport = prop.player.sport
        if sport == Sport.NFL:
            return self._nfl_logs(prop, max_games)
        elif sport == Sport.NBA:
            return self._nba_logs(prop, max_games)
        elif sport == Sport.MLB:
            return self._mlb_logs(prop, max_games)
        elif sport == Sport.NHL:
            return self._nhl_logs(prop, max_games)
        return []

    def _normalize_name(self, name: str) -> str:
        """Normalize player names for better matching."""
        import re
        name = name.lower().strip()
        # Remove common suffixes
        name = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?", "", name)
        # Remove punctuation
        name = re.sub(r"[^a-z\s]", "", name)
        # Collapse whitespace
        name = re.sub(r"\s+", " ", name).strip()
        return name

    def _match_nfl_player(self, df: pd.DataFrame, name: str) -> pd.DataFrame:
        """Try several matching strategies for NFL player names."""
        norm = self._normalize_name(name)
        parts = norm.split()
        if not parts:
            return pd.DataFrame()

        last = parts[-1]
        first = parts[0] if len(parts) > 1 else ""

        # 1. Exact normalized match
        df_norm = df["player_display_name"].apply(self._normalize_name)
        exact = df[df_norm == norm]
        if not exact.empty:
            return exact

        # 2. Last name + first initial
        if first:
            initial = first[0]
            mask = df_norm.str.contains(last) & df_norm.str.startswith(initial)
            matches = df[mask]
            if not matches.empty:
                return matches

        # 3. Last name only (if unique enough)
        mask = df_norm.str.contains(last)
        matches = df[mask]
        if len(matches["player_display_name"].unique()) == 1:
            return matches

        # 4. Contains full normalized name
        mask = df_norm.str.contains(norm)
        return df[mask]

    # ---------- NFL (nflverse daily CSVs) ----------
    def _nfl_logs(self, prop: PlayerProp, max_games: int) -> List[HistoricalStat]:
        df = self._load_nfl_player_stats()
        if df is None or df.empty:
            return []

        player_rows = self._match_nfl_player(df, prop.player.name)
        if player_rows.empty:
            return []

        # Prefer most recent season
        season = player_rows["season"].max()
        player_rows = player_rows[player_rows["season"] == season]
        player_rows = player_rows.sort_values("week", ascending=False).head(max_games)

        logs = []
        for _, row in player_rows.iterrows():
            value = self._extract_nfl_value(row, prop.market)
            if value is None:
                continue
            logs.append(
                HistoricalStat(
                    date=str(row.get("week", "")),
                    value=float(value),
                    opponent=str(row.get("opponent_team", "UNK")),
                    home=True,
                )
            )
        return logs

    def _load_nfl_player_stats(self) -> Optional[pd.DataFrame]:
        """Load latest nflverse weekly player stats (updated nightly)."""
        if self._nfl_cache is not None:
            return self._nfl_cache

        # Try current season first, then previous
        year = datetime.now().year
        urls = [
            f"https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{year}.csv.gz",
            f"https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{year-1}.csv.gz",
        ]
        for url in urls:
            try:
                resp = self.session.get(url, timeout=20)
                if resp.status_code == 200:
                    df = pd.read_csv(io.BytesIO(resp.content), compression="gzip")
                    self._nfl_cache = df
                    return df
            except Exception:
                continue
        return None

    def _extract_nfl_value(self, row, market: MarketType) -> Optional[float]:
        mapping = {
            MarketType.PASSING_YARDS: "passing_yards",
            MarketType.RUSHING_YARDS: "rushing_yards",
            MarketType.RECEIVING_YARDS: "receiving_yards",
            MarketType.RECEPTIONS: "receptions",
        }
        col = mapping.get(market)
        return row.get(col) if col and col in row.index else None

    # ---------- NBA ----------
    def _nba_logs(self, prop: PlayerProp, max_games: int) -> List[HistoricalStat]:
        # Prefer nba_api if installed, else balldontlie
        try:
            return self._nba_api_logs(prop, max_games)
        except Exception:
            return self._balldontlie_logs(prop, max_games)

    def _nba_api_logs(self, prop: PlayerProp, max_games: int) -> List[HistoricalStat]:
        """Uses nba_api library (pip install nba_api)."""
        from nba_api.stats.endpoints import playergamelog
        from nba_api.stats.static import players

        # Find player ID with better matching
        all_players = players.get_players()
        norm_target = self._normalize_name(prop.player.name)
        match = None
        for p in all_players:
            if self._normalize_name(p["full_name"]) == norm_target:
                match = p
                break
        if not match:
            # fallback contains
            for p in all_players:
                if norm_target in self._normalize_name(p["full_name"]):
                    match = p
                    break
        if not match:
            return []

        season = f"{datetime.now().year-1}-{str(datetime.now().year)[-2:]}"
        gamelog = playergamelog.PlayerGameLog(player_id=match["id"], season=season)
        df = gamelog.get_data_frames()[0].head(max_games)

        logs = []
        for _, row in df.iterrows():
            value = self._extract_nba_value_from_api(row, prop.market)
            if value is None:
                continue
            logs.append(
                HistoricalStat(
                    date=str(row.get("GAME_DATE", "")),
                    value=float(value),
                    opponent=str(row.get("MATCHUP", "")),
                    home=True,
                )
            )
        return logs

    def _extract_nba_value_from_api(self, row, market: MarketType) -> Optional[float]:
        mapping = {
            MarketType.POINTS: "PTS",
            MarketType.REBOUNDS: "REB",
            MarketType.ASSISTS: "AST",
            MarketType.THREES: "FG3M",
        }
        col = mapping.get(market)
        return row.get(col) if col else None

    def _balldontlie_logs(self, prop: PlayerProp, max_games: int) -> List[HistoricalStat]:
        """Fallback balldontlie."""
        search_url = "https://api.balldontlie.io/v1/players"
        headers = {"Authorization": self.balldontlie_key} if self.balldontlie_key else {}
        resp = self.session.get(
            search_url,
            params={"search": prop.player.name.split()[-1]},
            headers=headers,
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        players = resp.json().get("data", [])
        if not players:
            return []
        player = players[0]

        season = datetime.now().year if datetime.now().month >= 10 else datetime.now().year - 1
        stats_url = "https://api.balldontlie.io/v1/stats"
        resp = self.session.get(
            stats_url,
            params={"player_ids[]": player["id"], "seasons[]": season, "per_page": max_games},
            headers=headers,
            timeout=10,
        )
        if resp.status_code != 200:
            return []

        logs = []
        for row in resp.json().get("data", [])[:max_games]:
            value = self._extract_nba_value(row, prop.market)
            if value is None:
                continue
            game = row.get("game", {})
            logs.append(
                HistoricalStat(
                    date=game.get("date", "")[:10],
                    value=float(value),
                    opponent=row.get("team", {}).get("abbreviation", "UNK"),
                    home=True,
                )
            )
        return logs

    def _extract_nba_value(self, row: dict, market: MarketType) -> Optional[float]:
        mapping = {
            MarketType.POINTS: "pts",
            MarketType.REBOUNDS: "reb",
            MarketType.ASSISTS: "ast",
            MarketType.THREES: "fg3m",
        }
        key = mapping.get(market)
        return row.get(key) if key else None

    # ---------- MLB (unchanged, free official) ----------
    def _mlb_logs(self, prop: PlayerProp, max_games: int) -> List[HistoricalStat]:
        search_url = "https://statsapi.mlb.com/api/v1/people/search"
        resp = self.session.get(search_url, params={"names": prop.player.name}, timeout=10)
        if resp.status_code != 200:
            return []
        people = resp.json().get("people", [])
        if not people:
            return []
        player_id = people[0]["id"]

        season = datetime.now().year
        log_url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats"
        group = "hitting" if prop.market == MarketType.HITS else "pitching"
        resp = self.session.get(
            log_url,
            params={"stats": "gameLog", "season": season, "group": group},
            timeout=10,
        )
        if resp.status_code != 200:
            return []

        splits = resp.json().get("stats", [{}])[0].get("splits", [])
        logs = []
        for split in splits[:max_games]:
            stat = split.get("stat", {})
            value = self._extract_mlb_value(stat, prop.market)
            if value is None:
                continue
            logs.append(
                HistoricalStat(
                    date=split.get("date", ""),
                    value=float(value),
                    opponent=split.get("opponent", {}).get("name", "UNK"),
                    home=split.get("isHome", True),
                )
            )
        return logs

    def _extract_mlb_value(self, stat: dict, market: MarketType) -> Optional[float]:
        if market == MarketType.HITS:
            return stat.get("hits")
        if market == MarketType.STRIKEOUTS:
            return stat.get("strikeOuts")
        return None

    # ---------- NHL (placeholder, free official) ----------
    def _nhl_logs(self, prop: PlayerProp, max_games: int) -> List[HistoricalStat]:
        # Name → ID lookup is non-trivial; return empty for now.
        # Can be extended with TheSportsDB or a local cache.
        return []
