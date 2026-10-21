"""
Demo script: load data, analyze, build parlays, and print results.
Run with: python main.py

Set ODDS_API_KEY in the environment (or .env) to use live data.
Otherwise it uses mock data.
"""
import sys
import os
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional

from models.models import Sport
from data.data_fetcher import DataFetcher
from analysis.analyzer import PropAnalyzer
from analysis.parlay_builder import ParlayBuilder


def main():
    print("=== Sports Props Analysis App — Live/Mock Demo ===\n")
    
    api_key = os.getenv("ODDS_API_KEY")
    if api_key:
        print(f"ODDS_API_KEY detected — attempting live data from The Odds API")
    else:
        print("No ODDS_API_KEY found — using mock data")
        print("(Create a .env file with ODDS_API_KEY=... or export it)")
    
    fetcher = DataFetcher()  # auto-detects mock vs live
    analyzer = PropAnalyzer()
    builder = ParlayBuilder()
    
    for sport in [Sport.NBA, Sport.NFL]:
        print(f"\n{'='*60}")
        print(f"  {sport.value} TOP PROPS")
        print(f"{'='*60}")
        
        props = fetcher.get_player_props(sport)
        if not props:
            print("  No data available for this sport yet.")
            continue
        
        recs = analyzer.get_recommendations(props, top_n=8)
        
        if not recs:
            print("  No recommendations above threshold.")
            # Still show raw props if analysis has nothing
            for p in props[:5]:
                lines_str = ", ".join(f"{l.platform.value} {l.line}" for l in p.lines[:3])
                print(f"  • {p.player.name} {p.market.value} — {lines_str}")
            continue
        
        for i, rec in enumerate(recs, 1):
            print(f"\n{i}. {rec.prop.player.name} ({rec.prop.player.team}) — {rec.prop.market.value}")
            print(f"   Best: {rec.best_platform.value} {rec.best_line} ({rec.direction})")
            print(f"   Edge: {rec.edge_score:.2f} | Confidence: {rec.confidence:.0%}")
            print(f"   Why: {rec.reason}")
        
        print(f"\n{'-'*60}")
        print(f"  SUGGESTED PARLAYS ({sport.value})")
        print(f"{'-'*60}")
        
        parlays = builder.build_parlays(props, sizes=[2, 3, 4], max_per_size=3)
        if not parlays:
            print("  Not enough high-edge props for parlays yet.")
        else:
            for p in parlays[:4]:
                print("\n" + builder.format_parlay(p))
    
    print("\n\n=== Demo complete ===")
    print("To use live data:")
    print("  1. Get a free key: https://the-odds-api.com/")
    print("  2. Create .env with: ODDS_API_KEY=your_key")
    print("  3. pip install requests python-dotenv")
    print("  4. Re-run: python main.py")


if __name__ == "__main__":
    main()
