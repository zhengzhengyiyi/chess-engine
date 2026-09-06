#!/usr/bin/env python3
"""Debug script to check analyzer state"""

import sys
sys.path.append('.')
from analyzer import ChessAnalyzer

def test_analyzer_state():
    """Test analyzer to see what data it's generating"""
    analyzer = ChessAnalyzer(quiet=False)
    
    # Wait a bit for analysis to run
    import time
    time.sleep(5)
    
    print(f"\n=== Analyzer State ===")
    print(f"Best move: {analyzer.best_move}")
    print(f"Second best: {analyzer.second_best_move}")
    print(f"Third best: {analyzer.third_best_move}")
    print(f"Evaluation: {analyzer.evaluation}")
    print(f"Analysis depth: {analyzer.analysis_depth}")
    print(f"Principal variations: {analyzer.principal_variations}")
    print(f"Analyzing: {analyzer.analyzing}")
    
    # Check engine state
    print(f"\n=== Engine State ===")
    top_moves = analyzer.engine.get_top_moves()
    print(f"Top moves count: {len(top_moves)}")
    for i, (move, score) in enumerate(top_moves[:5]):
        print(f"  {i+1}. {move.uci() if move else None}: {score}")
    
    print(f"Engine current_search_depth: {analyzer.engine.current_search_depth}")
    print(f"Engine depth: {analyzer.engine.depth}")
    print(f"Engine top moves cache: {len(analyzer.engine.top_moves_cache)}")
    
    # Manually call analyze_position to see what happens
    print(f"\n=== Manual Analysis Call ===")
    analyzer.analyze_position()
    print(f"After manual call - Analysis depth: {analyzer.analysis_depth}")
    
    # Stop the analyzer
    analyzer.stop_analysis.set()
    if analyzer.analysis_thread:
        analyzer.analysis_thread.join(timeout=1)
    pygame.quit()

if __name__ == "__main__":
    import pygame
    test_analyzer_state()
