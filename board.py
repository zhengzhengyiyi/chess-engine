"""Board wrapper for chess analyzer compatibility."""

import chess

class Board:
    """Wrapper class for chess.Board to match analyzer interface."""
    
    def __init__(self, fen=None):
        """Initialize board with optional FEN string."""
        if fen:
            self.board = chess.Board(fen)
        else:
            self.board = chess.Board()
    
    def clone(self):
        """Create a copy of the board."""
        new_board = Board(self.board.fen())
        return new_board
    
    def apply_move(self, move):
        """Apply a move to the board."""
        self.board.push(move)
    
    def reset(self):
        """Reset to starting position."""
        self.board = chess.Board()