"""
C++ Chess Engine Wrapper
Handles integration between Python and C++ chess engine
"""

import ctypes
from pathlib import Path
import chess

# Library path
LIB_PATH = Path(__file__).parent / "libchess_engine.dylib"
# Fallback to repository root
if not LIB_PATH.exists():
    LIB_PATH = Path(__file__).parent.parent / "libchess_engine.dylib"

class CppChessEngine:
    def __init__(self, depth=2, use_backward_search=False, search_time=1.0, 
                 realtime=False, quiet=False):
        self.depth = depth
        self.use_backward_search = use_backward_search
        self.search_time = search_time
        self.realtime = realtime
        self.quiet = quiet
        
        # Load the C++ library
        self.lib = ctypes.CDLL(str(LIB_PATH))
        
        # Set up function signatures
        self.lib.create_engine.argtypes = [
            ctypes.c_int, ctypes.c_int, ctypes.c_double, 
            ctypes.c_int, ctypes.c_int
        ]
        self.lib.create_engine.restype = ctypes.c_void_p
        
        self.lib.destroy_engine.argtypes = [ctypes.c_void_p]
        self.lib.destroy_engine.restype = None
        
        self.lib.search.argtypes = [ctypes.c_void_p]
        self.lib.search.restype = ctypes.c_char_p
        
        self.lib.get_evaluation.argtypes = [ctypes.c_void_p]
        self.lib.get_evaluation.restype = ctypes.c_int
        
        self.lib.set_board_fen.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        self.lib.set_board_fen.restype = None
        
        self.lib.get_best_move_uci.argtypes = [ctypes.c_void_p]
        self.lib.get_best_move_uci.restype = ctypes.c_char_p
        
        self.lib.configure_engine.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.lib.configure_engine.restype = None
        
        # Optional newer exports (present in rebuilt library)
        if hasattr(self.lib, 'set_engine_depth'):
            self.lib.set_engine_depth.argtypes = [ctypes.c_void_p, ctypes.c_int]
            self.lib.set_engine_depth.restype = None
        
        # Create C++ engine instance
        self.engine_ptr = self.lib.create_engine(
            depth, int(use_backward_search), search_time, 
            int(realtime), int(quiet)
        )
        
        if not self.engine_ptr:
            raise RuntimeError("Failed to create C++ engine instance")
        
        # Cache for compatibility
        self.top_moves_cache = []
        self.current_search_depth = depth
    
    def __del__(self):
        """Clean up the C++ engine instance."""
        if hasattr(self, 'engine_ptr') and self.engine_ptr:
            self.lib.destroy_engine(self.engine_ptr)
    
    def _material_eval(self, chess_board):
        """Simple material evaluation used for top-move cache scores."""
        values = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
                  chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 0}
        score = 0
        for square in chess.SQUARES:
            piece = chess_board.piece_at(square)
            if piece:
                v = values.get(piece.piece_type, 0)
                score += v if piece.color == chess.WHITE else -v
        return score if chess_board.turn == chess.WHITE else -score
    
    def search(self, chess_board):
        """
        Search for the best move using the C++ engine.
        Falls back to the internal Python minimax if the C++ call fails.
        
        Args:
            chess_board: chess.Board object
            
        Returns:
            chess.Move object representing the best move
        """
        import chess
        
        legal_moves = list(chess_board.legal_moves)
        if not legal_moves:
            return None
        
        try:
            if hasattr(self.lib, 'set_engine_depth'):
                self.lib.set_engine_depth(self.engine_ptr, self.depth)
            self.lib.set_board_fen(self.engine_ptr, chess_board.fen().encode('utf-8'))
            raw = self.lib.search(self.engine_ptr)
            if raw:
                move = chess.Move.from_uci(raw.decode('utf-8'))
                if move in chess_board.legal_moves:
                    self.top_moves_cache = [(move, self._material_eval(chess_board))]
                    self.current_search_depth = self.depth
                    return move
        except Exception:
            pass
        
        return self._search_python(chess_board)
    
    def _search_python(self, chess_board):
        """Python minimax fallback (used only if the C++ engine call fails)."""
        import chess
        
        # Get legal moves from python-chess (reliable)
        legal_moves = list(chess_board.legal_moves)
        
        if not legal_moves:
            return None
        
        # Piece values for evaluation
        piece_values = {chess.PAWN: 100, chess.KNIGHT: 350, chess.BISHOP: 350,
                      chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000}
        
        # Center squares for position evaluation
        center_squares = [chess.D4, chess.D5, chess.E4, chess.E5]
        
        def evaluate(board):
            """Material + position evaluation with trade protection."""
            score = 0
            white_material = 0
            black_material = 0
            
            for square in chess.SQUARES:
                piece = board.piece_at(square)
                if piece:
                    value = piece_values.get(piece.piece_type, 0)
                    
                    # Center control bonus
                    if square in center_squares:
                        value += 10
                    
                    # Knight/Bishop center bonus
                    if piece.piece_type in [chess.KNIGHT, chess.BISHOP] and square in center_squares:
                        value += 15
                    
                    # Pawn advancement bonus
                    if piece.piece_type == chess.PAWN:
                        rank = chess.square_rank(square)
                        if piece.color == chess.WHITE and rank >= 4:
                            value += 5 * (rank - 3)
                        elif piece.color == chess.BLACK and rank <= 3:
                            value += 5 * (4 - rank)
                    
                    if piece.color == chess.WHITE:
                        score += value
                        white_material += value
                    else:
                        score -= value
                        black_material += value
            
            # Penalty for losing much more material than opponent
            material_diff = white_material - black_material
            if board.turn == chess.WHITE and material_diff < -200:
                score -= abs(material_diff) * 2  # Heavy penalty for being behind
            elif board.turn == chess.BLACK and material_diff > 200:
                score -= abs(material_diff) * 2  # Heavy penalty for being behind
            
            return score
        
        # Order moves using MVV-LVA with trade protection and piece development bonus
        def order_moves(moves, board):
            ordered = []
            for move in moves:
                score = 0
                
                # Piece development bonus: prefer moving less valuable pieces
                piece = board.piece_at(move.from_square)
                if piece:
                    piece_value = piece_values.get(piece.piece_type, 0)
                    # Higher bonus for lower-valued pieces (encourages development)
                    if piece_value < 500:  # Pawn, Knight, Bishop
                        score += (500 - piece_value) // 2  # Bonus inversely proportional to value
                    elif piece_value >= 900:  # Queen
                        score -= 50  # Penalty for moving queen early
                
                if board.is_capture(move):
                    victim = board.piece_at(move.to_square)
                    attacker = board.piece_at(move.from_square)
                    if victim and attacker:
                        victim_value = piece_values.get(victim.piece_type, 0)
                        attacker_value = piece_values.get(attacker.piece_type, 0)
                        
                        # MVV-LVA: prioritize capturing valuable pieces with less valuable pieces
                        score = victim_value * 10 - attacker_value
                        
                        # Penalty for bad trades (trading valuable piece for cheap one)
                        if attacker_value > victim_value + 100:
                            score -= (attacker_value - victim_value) * 2  # Heavy penalty for bad trade
                
                if move.promotion:
                    score += piece_values.get(move.promotion, 0) * 5
                
                ordered.append((move, score))
            
            ordered.sort(key=lambda x: x[1], reverse=True)
            return [move for move, score in ordered]
        
        def minimax(board, depth, alpha, beta, is_maximizing, ply_from_root=0):
            """Minimax with alpha-beta pruning and shortest checkmate preference."""
            if depth == 0 or board.is_game_over():
                if board.is_checkmate():
                    mate_depth = ply_from_root
                    if board.turn == chess.WHITE:
                        return -20000 + mate_depth
                    else:
                        return 20000 - mate_depth
                return evaluate(board)
            
            legal_moves = list(board.legal_moves)
            
            if is_maximizing:
                max_eval = float('-inf')
                for move in legal_moves:
                    board.push(move)
                    eval_score = minimax(board, depth - 1, alpha, beta, False, ply_from_root + 1)
                    board.pop()
                    max_eval = max(max_eval, eval_score)
                    alpha = max(alpha, eval_score)
                    if beta <= alpha:
                        break
                return max_eval
            else:
                min_eval = float('inf')
                for move in legal_moves:
                    board.push(move)
                    eval_score = minimax(board, depth - 1, alpha, beta, True, ply_from_root + 1)
                    board.pop()
                    min_eval = min(min_eval, eval_score)
                    beta = min(beta, eval_score)
                    if beta <= alpha:
                        break
                return min_eval
        
        # Order legal moves
        ordered_moves = order_moves(legal_moves, chess_board)
        
        # Find best move using minimax
        best_move = None
        best_score = float('-inf') if chess_board.turn == chess.WHITE else float('inf')
        
        # Track recent moves for repetition detection
        recent_moves = []
        for i in range(min(6, len(chess_board.move_stack))):
            recent_moves.append(chess_board.move_stack[-i-1].uci())
        
        for move in ordered_moves:
            board_copy = chess_board.copy()
            board_copy.push(move)
            
            # Repetition penalties
            repetition_penalty = 0
            move_uci = move.uci()
            
            if chess_board.move_stack:
                last_move = chess_board.peek()
                # Penalty: Move that undoes the immediate previous move
                if move.to_square == last_move.from_square and move.from_square == last_move.to_square:
                    repetition_penalty -= 150
                
                # Penalty: Moving the same piece again (starts where last move ended)
                if move.from_square == last_move.to_square:
                    repetition_penalty -= 120
            
            if move_uci in recent_moves:
                repetition_penalty -= 150
            
            if chess_board.turn == chess.WHITE:
                score = minimax(board_copy, self.depth - 1, float('-inf'), float('inf'), False, 1) + repetition_penalty
                if score > best_score:
                    best_score = score
                    best_move = move
            else:
                score = minimax(board_copy, self.depth - 1, float('-inf'), float('inf'), True, 1) + repetition_penalty
                if score < best_score:
                    best_score = score
                    best_move = move
        
        # Update cache for compatibility
        if best_move:
            board_copy = chess_board.copy()
            board_copy.push(best_move)
            eval_score = evaluate(board_copy)
            self.top_moves_cache = [(best_move, eval_score)]
            self.current_search_depth = self.depth
        else:
            self.top_moves_cache = []
        
        return best_move
    
    def get_best_move(self):
        """Get the best move as a custom tuple (for compatibility)"""
        move_uci = self.lib.get_best_move_uci(self.engine_ptr)
        if not move_uci:
            return None
        
        try:
            chess_move = chess.Move.from_uci(move_uci.decode('utf-8'))
            # Convert to custom tuple format for compatibility
            from_sq = (chess.square_rank(chess_move.from_square), 
                      chess.square_file(chess_move.from_square))
            to_sq = (chess.square_rank(chess_move.to_square), 
                    chess.square_file(chess_move.to_square))
            prom = None
            if chess_move.promotion:
                prom = chess_move.promotion
            return (from_sq, to_sq, prom)
        except ValueError:
            return None
    
    def chess_to_custom_board(self, chess_board):
        """Convert python-chess board to custom board format (for compatibility)"""
        # This is a compatibility function - not needed for C++ engine
        # since we use FEN for board state
        pass
    
    def custom_to_chess_move(self, custom_move):
        """Convert custom move tuple to chess.Move (for compatibility)"""
        if len(custom_move) >= 2:
            from_rank, from_file = custom_move[0]
            to_rank, to_file = custom_move[1]
            from_sq = chess.square(from_file, from_rank)
            to_sq = chess.square(to_file, to_rank)
            promotion = custom_move[2] if len(custom_move) > 2 else None
            return chess.Move(from_sq, to_sq, promotion)
        return None
    
    def set_realtime_callback(self, callback):
        """Set callback for real-time search updates (placeholder)"""
        # C++ engine doesn't support Python callbacks
        pass
    
    def get_current_analysis(self):
        """Get current analysis results (for compatibility)"""
        if self.top_moves_cache:
            best_move, score = self.top_moves_cache[0]
            return {
                'best_move': best_move,
                'score': score,
                'evaluation': score,
                'depth': self.current_search_depth,
                'top_moves': self.top_moves_cache,
                'principal_variations': []
            }
        return {
            'best_move': None,
            'score': 0,
            'evaluation': 0,
            'depth': self.current_search_depth,
            'top_moves': [],
            'principal_variations': []
        }
    
    def get_evaluation(self):
        """Get the current position evaluation (for compatibility)"""
        if self.top_moves_cache:
            return self.top_moves_cache[0][1]
        return 0
    
    def get_top_moves(self):
        """Get top moves (for compatibility)"""
        return self.top_moves_cache
    
    def get_principal_variations(self):
        """Get principal variations (for compatibility)"""
        return []
    
    def reset_board(self):
        """Reset the board to starting position"""
        starting_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        self.lib.set_board_fen(self.engine_ptr, starting_fen.encode('utf-8'))
    
    def clear_move_ordering_cache(self):
        """Clear the move ordering cache (placeholder)"""
        # C++ engine handles its own caching
        pass
    
    def configure_performance(self, tt_size=1000000, max_cache=100000, aggressive_caching=True):
        """Configure performance settings"""
        self.lib.configure_engine(self.engine_ptr, tt_size, max_cache, int(aggressive_caching))
