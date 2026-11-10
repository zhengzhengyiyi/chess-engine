#!/usr/bin/env python3
"""Simple test for analyzer with C++ engine without GUI."""

import chess
from source.cpp_engine_wrapper import CppChessEngine

def test_cpp_analyzer_logic():
    print("Testing C++ engine analyzer logic...")
    
    # Create engine
    engine = CppChessEngine(depth=2, quiet=True)
    
    # Test starting position
    board = chess.Board()
    
    # Search
    best_move = engine.search(board)
    print(f"Best move: {best_move}")
    
    # Get analysis
    analysis = engine.get_current_analysis()
    print(f"Analysis: {analysis}")
    
    # Check legal
    if best_move and best_move in board.legal_moves:
        print(f"✓ Best move is legal")
    else:
        print(f"✗ Best move is NOT legal")
    
    # Test with black to move
    board.push_san("e4")
    board.push_san("e5")
    board.push_san("Nf3")  # White moves
    board.push_san("Nc6")  # Black moves
    
    print(f"Turn: {board.turn} (True=White, False=Black)")
    print(f"Legal moves: {list(board.legal_moves)[:5]}")
    
    best_move = engine.search(board)
    print(f"Best move for {'white' if board.turn else 'black'}: {best_move}")
    
    if best_move and best_move in board.legal_moves:
        print(f"✓ Black's best move is legal")
    else:
        print(f"✗ Black's best move is NOT legal")
    
    print("✓ C++ analyzer logic test completed")

if __name__ == "__main__":
    test_cpp_analyzer_logic()
