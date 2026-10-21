"""
Analysis engine: hit rates, edge scoring, ranking.
"""
from typing import List, Literal
from models.models import PlayerProp, Recommendation, Platform


class PropAnalyzer:
    """Computes hit rates, edges, and ranks props."""
    
    def analyze(self, props: List[PlayerProp]) -> List[PlayerProp]:
        """Compute metrics on a list of props and return them sorted by edge."""
        for prop in props:
            self._compute_hit_rates(prop)
            self._compute_edge(prop)
        return sorted(props, key=lambda p: p.edge_score or 0, reverse=True)
    
    def _compute_hit_rates(self, prop: PlayerProp):
        if not prop.historical or not prop.lines:
            return
        
        # Use the best over line as the threshold for hit rate
        best = prop.best_line("over")
        if not best:
            return
        line = best.line
        
        recent = prop.historical[:10]
        if recent:
            hits = sum(1 for h in recent if h.value > line)
            prop.hit_rate_last_10 = hits / len(recent)
        
        all_hits = sum(1 for h in prop.historical if h.value > line)
        prop.hit_rate_season = all_hits / len(prop.historical) if prop.historical else None
        
        last_5 = prop.historical[:5]
        if last_5:
            prop.avg_last_5 = sum(h.value for h in last_5) / len(last_5)
    
    def _compute_edge(self, prop: PlayerProp):
        """
        Simple edge score:
        - Higher hit rate is better
        - Line shopping advantage (difference between best and worst line)
        - Recent form vs line
        """
        if prop.hit_rate_last_10 is None:
            # Small baseline so props still appear when stats are missing
            prop.edge_score = 0.05
            prop.confidence = 0.2
            return
        
        # Base from hit rate (0.5 = neutral)
        hit_component = (prop.hit_rate_last_10 - 0.5) * 2  # -1 to +1
        
        # Line shopping component
        over_lines = [l.line for l in prop.lines if l.direction == "over"]
        line_spread = 0.0
        if len(over_lines) >= 2:
            line_spread = max(over_lines) - min(over_lines)
            # Normalize roughly (bigger spread = more shopping opportunity)
            line_component = min(line_spread / 5.0, 1.0) * 0.3
        else:
            line_component = 0.0
        
        # Form component
        form_component = 0.0
        if prop.avg_last_5 and over_lines:
            best_line = min(over_lines)
            if prop.avg_last_5 > best_line:
                form_component = min((prop.avg_last_5 - best_line) / best_line, 0.5)
        
        prop.edge_score = max(0.0, hit_component * 0.6 + line_component + form_component)
        prop.confidence = min(1.0, prop.hit_rate_last_10 * 0.7 + (0.3 if len(prop.historical) >= 5 else 0.1))
    
    def get_recommendations(
        self,
        props: List[PlayerProp],
        top_n: int = 15,
        min_edge: float = 0.1
    ) -> List[Recommendation]:
        analyzed = self.analyze(props)
        recs = []
        
        for prop in analyzed:
            if (prop.edge_score or 0) < min_edge:
                continue
            
            best = prop.best_line("over")
            if not best:
                continue
            
            reason_parts = []
            if prop.hit_rate_last_10:
                reason_parts.append(f"{prop.hit_rate_last_10:.0%} hit rate last 10")
            if prop.avg_last_5:
                reason_parts.append(f"avg {prop.avg_last_5:.1f} last 5")
            if len(prop.lines) > 1:
                lines_str = ", ".join(f"{l.platform.value} {l.line}" for l in prop.lines if l.direction == "over")
                reason_parts.append(f"lines: {lines_str}")
            
            recs.append(Recommendation(
                prop=prop,
                direction="over",
                best_platform=best.platform,
                best_line=best.line,
                reason="; ".join(reason_parts),
                edge_score=prop.edge_score or 0,
                confidence=prop.confidence or 0
            ))
            
            if len(recs) >= top_n:
                break
        
        return recs
