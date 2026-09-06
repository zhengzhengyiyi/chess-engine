#!/usr/bin/env python3
"""Test script to verify move generation works correctly"""

import sys
sys.path.append('engine')
from Engine import ChessEngine

def test_move_generation():
    """Test that legal moves are generated correctly"""
    engine = ChessEngine(depth=3)
    
    # Test starting position
    print("Testing starting position...")
    legal_moves = engine.generate_legal_moves()
    print(f"Number of legal moves in starting position: {len(legal_moves)}")
    
    # Should be 20 legal moves in starting position
    if len(legal_moves) == 20:
        print("✓ Starting position has correct number of moves (20)")
    else:
        print(f"✗ Expected 20 moves, got {len(legal_moves)}")
    
    # Print first few moves
    print("\nFirst 5 legal moves:")
    for i, move in enumerate(legal_moves[:5]):
        print(f"  {i+1}. {move}")
    
    # Test after a move
    print("\n\nTesting after e2e4...")
    e2e4 = ((6, 4), (4, 4), None)
    if engine.make_move(e2e4):
        legal_moves = engine.generate_legal_moves()
        print(f"Number of legal moves after e2e4: {len(legal_moves)}")
        
        # Should be 20 legal moves for black after e2e4
        if len(legal_moves) == 20:
            print("✓ After e2e4 has correct number of moves (20)")
        else:
            print(f"✗ Expected 20 moves, got {len(legal_moves)}")
        
        # Print first few moves
        print("\nFirst 5 legal moves for black:")
        for i, move in enumerate(legal_moves[:5]):
            print(f"  {i+1}. {move}")
    else:
        print("✗ Failed to make e2e4 move")
    
    # Test best move calculation
    print("\n\nTesting best move calculation...")
    engine.reset_board()
    best_move = engine.get_best_move()
    print(f"Best move from starting position: {best_move}")
    
    if best_move:
        print("✓ Successfully calculated best move")
    else:
        print("✗ Failed to calculate best move")
    
    print("\n\nAll tests completed!")

if __name__ == "__main__":
    test_move_generation()
