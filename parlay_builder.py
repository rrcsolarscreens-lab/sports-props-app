"""
Parlay builder: generates 2-6 leg combinations from top-ranked props.
"""
from typing import List
from itertools import combinations
from models.models import PlayerProp, Parlay, ParlayLeg, Platform, Recommendation
from analysis.analyzer import PropAnalyzer


class ParlayBuilder:
    def __init__(self):
        self.analyzer = PropAnalyzer()
    
    def build_parlays(
        self,
        props: List[PlayerProp],
        sizes: List[int] = None,
        max_per_size: int = 5,
        min_edge: float = 0.15
    ) -> List[Parlay]:
        """
        Generate suggested parlays of different sizes.
        Currently greedy: takes top props and combines them, avoiding same-player stacks.
        """
        if sizes is None:
            sizes = [2, 3, 4, 5, 6]
        
        recs = self.analyzer.get_recommendations(props, top_n=30, min_edge=min_edge)
        if len(recs) < 2:
            return []
        
        parlays = []
        used_players = set()
        
        for size in sizes:
            candidates = [r for r in recs if r.prop.player.id not in used_players]
            if len(candidates) < size:
                continue
            
            # Take the top unique-player props for this size
            selected = []
            players_in_parlay = set()
            for rec in candidates:
                if rec.prop.player.id not in players_in_parlay:
                    selected.append(rec)
                    players_in_parlay.add(rec.prop.player.id)
                if len(selected) == size:
                    break
            
            if len(selected) < size:
                continue
            
            legs = []
            total_edge = 0.0
            platforms = []
            
            for rec in selected:
                best = rec.prop.best_line("over")
                if not best:
                    continue
                legs.append(ParlayLeg(
                    prop=rec.prop,
                    direction="over",
                    platform=best.platform,
                    line=best.line,
                    edge_score=rec.edge_score
                ))
                total_edge += rec.edge_score
                platforms.append(best.platform)
            
            if len(legs) < size:
                continue
            
            # Recommend the platform that appears most often, or the one with best average line
            from collections import Counter
            platform_counts = Counter(platforms)
            recommended = platform_counts.most_common(1)[0][0] if platforms else None
            
            # Rough probability estimate (independent assumption — refine later)
            avg_hit = sum(r.prop.hit_rate_last_10 or 0.5 for r in selected) / len(selected)
            est_prob = avg_hit ** size
            
            parlays.append(Parlay(
                legs=legs,
                total_edge=total_edge,
                estimated_hit_probability=est_prob,
                recommended_platform=recommended
            ))
            
            # Mark players as used so later parlays don't overlap too much (optional)
            # for r in selected:
            #     used_players.add(r.prop.player.id)
        
        return sorted(parlays, key=lambda p: p.total_edge, reverse=True)
    
    def format_parlay(self, parlay: Parlay) -> str:
        """Pretty-print a parlay for display or export."""
        lines = [
            f"{parlay.size}-leg parlay (edge: {parlay.total_edge:.2f}, est. hit: {parlay.estimated_hit_probability:.1%})",
            f"Recommended platform: {parlay.recommended_platform.value if parlay.recommended_platform else 'Any'}",
            "-" * 50
        ]
        for i, leg in enumerate(parlay.legs, 1):
            lines.append(
                f"{i}. {leg.prop.player.name} ({leg.prop.player.team}) "
                f"{leg.prop.market.value} {leg.direction.upper()} {leg.line} "
                f"@ {leg.platform.value}  [edge {leg.edge_score:.2f}]"
            )
        return "\n".join(lines)
