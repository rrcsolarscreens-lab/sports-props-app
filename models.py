"""
Core data models for the Sports Props Analysis App.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal
from datetime import datetime
from enum import Enum


class Sport(str, Enum):
    NFL = "NFL"
    CFL = "CFL"
    NBA = "NBA"
    MLB = "MLB"
    NHL = "NHL"


class Platform(str, Enum):
    PRIZEPICKS = "PrizePicks"
    UNDERDOG = "Underdog"
    SLEEPER = "Sleeper"
    KALSHI = "Kalshi"
    DRAFTKINGS = "DraftKings"
    FANDUEL = "FanDuel"


class MarketType(str, Enum):
    POINTS = "points"
    REBOUNDS = "rebounds"
    ASSISTS = "assists"
    THREES = "threes"
    PASSING_YARDS = "passing_yards"
    RUSHING_YARDS = "rushing_yards"
    RECEIVING_YARDS = "receiving_yards"
    RECEPTIONS = "receptions"
    GOALS = "goals"
    SHOTS = "shots"
    STRIKEOUTS = "strikeouts"
    HITS = "hits"
    # Add more as needed


@dataclass
class Player:
    id: str
    name: str
    team: str
    position: str
    sport: Sport


@dataclass
class HistoricalStat:
    """One game's stat for hit-rate calculation."""
    date: str
    value: float
    opponent: str
    home: bool = True


@dataclass
class PropLine:
    """A single line from one platform."""
    platform: Platform
    line: float
    odds: Optional[float] = None  # American odds if available; None for pure DFS projections
    direction: Literal["over", "under"] = "over"
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PlayerProp:
    """A player prop market with lines from multiple platforms + historical data."""
    id: str
    player: Player
    market: MarketType
    lines: List[PropLine] = field(default_factory=list)
    historical: List[HistoricalStat] = field(default_factory=list)
    
    # Computed fields
    hit_rate_last_10: Optional[float] = None
    hit_rate_season: Optional[float] = None
    avg_last_5: Optional[float] = None
    edge_score: Optional[float] = None  # higher = better value
    confidence: Optional[float] = None
    
    def best_line(self, direction: Literal["over", "under"] = "over") -> Optional[PropLine]:
        """Return the most favorable line for the given direction."""
        relevant = [l for l in self.lines if l.direction == direction]
        if not relevant:
            return None
        if direction == "over":
            # For overs, lower line is better (easier to hit)
            return min(relevant, key=lambda x: x.line)
        else:
            # For unders, higher line is better
            return max(relevant, key=lambda x: x.line)


@dataclass
class ParlayLeg:
    prop: PlayerProp
    direction: Literal["over", "under"]
    platform: Platform
    line: float
    edge_score: float = 0.0


@dataclass
class Parlay:
    legs: List[ParlayLeg]
    total_edge: float = 0.0
    estimated_hit_probability: float = 0.0
    recommended_platform: Optional[Platform] = None
    
    @property
    def size(self) -> int:
        return len(self.legs)


@dataclass
class Recommendation:
    """Top recommendation output."""
    prop: PlayerProp
    direction: Literal["over", "under"]
    best_platform: Platform
    best_line: float
    reason: str
    edge_score: float
    confidence: float
