#!/usr/bin/env python3
"""Test script to verify analyzer integration works correctly"""

import sys
sys.path.append('engine')
from engine.Engine import ChessEngine
import chess

def test_engine_search():
    """Test that engine search generates proper PV lines and top moves"""
    engine = ChessEngine(depth=3)
    
    # Create a starting position
    board = chess.Board()
    
    print("Testing engine search...")
    print(f"Starting position: {board.fen()}")
    
    # Run search
    best_move = engine.search(board)
    
    print(f"\nBest move: {best_move}")
    print(f"Best move UCI: {best_move.uci() if best_move else None}")
    
    # Check top moves
    top_moves = engine.get_top_moves()
    print(f"\nTop moves count: {len(top_moves)}")
    for i, (move, score) in enumerate(top_moves[:5]):
        print(f"  {i+1}. {move.uci()}: {score}")
    
    # Check principal variations
    pv_lines = engine.get_principal_variations()
    print(f"\nPrincipal variations count: {len(pv_lines)}")
    for i, pv in enumerate(pv_lines[:3]):
        print(f"  PV {i+1}: {' '.join(pv)}")
    
    # Check current analysis
    analysis = engine.get_current_analysis()
    print(f"\nCurrent analysis:")
    print(f"  Best move: {analysis['best_move']}")
    print(f"  Evaluation: {analysis['evaluation']}")
    print(f"  Depth: {analysis['depth']}")
    
    # Verify we have meaningful data
    if best_move and len(top_moves) > 0 and len(pv_lines) > 0:
        print("\n✓ Engine search working correctly")
        return True
    else:
        print("\n✗ Engine search not working correctly")
        return False

if __name__ == "__main__":
    success = test_engine_search()
    sys.exit(0 if success else 1)
