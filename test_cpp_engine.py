#!/usr/bin/env python3
"""Test script for C++ chess engine integration."""

import chess
from source.cpp_engine_wrapper import CppChessEngine

def test_cpp_engine():
    print("Testing C++ chess engine...")
    
    try:
        # Create engine instance
        print("Creating C++ engine...")
        engine = CppChessEngine(depth=2, quiet=False)
        print("Engine created successfully!")
        
        # Test with starting position
        print("\nTesting with starting position...")
        board = chess.Board()
        
        # Sync board
        print("Syncing board to engine...")
        engine.chess_to_custom_board(board)
        
        # Search
        print("Searching for best move...")
        best_move = engine.search(board)
        print(f"Best move: {best_move}")
        
        # Get evaluation
        eval_score = engine.get_evaluation()
        print(f"Evaluation: {eval_score}")
        
        # Check if move is legal
        if best_move:
            if best_move in board.legal_moves:
                print(f"✓ Move {best_move} is legal!")
            else:
                print(f"✗ Move {best_move} is NOT legal!")
                print(f"Legal moves: {list(board.legal_moves)[:5]}...")
        else:
            print("✗ No move returned")
        
        # Test get_current_analysis
        print("\nTesting get_current_analysis...")
        analysis = engine.get_current_analysis()
        print(f"Analysis: {analysis}")
        
        print("\n✓ C++ engine test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n✗ C++ engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_cpp_engine()
    exit(0 if success else 1)
