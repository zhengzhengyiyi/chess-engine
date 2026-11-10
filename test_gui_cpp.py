#!/usr/bin/env python3
"""Test C++ engine with GUI-like flow."""

import chess
from source.cpp_engine_wrapper import CppChessEngine

def test_gui_flow():
    print("Testing C++ engine with GUI flow...")
    
    # Create engine
    engine = CppChessEngine(depth=2, quiet=True)
    
    # Create board
    board = chess.Board()
    
    # Simulate GUI flow
    for i in range(5):
        print(f"\n--- Move {i+1} ---")
        print(f"Turn: {'White' if board.turn == chess.WHITE else 'Black'}")
        
        # Sync engine to board
        engine.chess_to_custom_board(board)
        
        # Search for best move
        best_move = engine.search(board)
        print(f"Best move: {best_move}")
        
        if best_move and best_move in board.legal_moves:
            board.push(best_move)
            print(f"Move applied. New FEN: {board.fen()[:50]}...")
        else:
            print(f"Invalid move: {best_move}")
            break
    
    print("\n✓ GUI flow test completed")

if __name__ == "__main__":
    test_gui_flow()
