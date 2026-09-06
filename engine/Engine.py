import sys
sys.path.append('..')
import chess
from functools import lru_cache
from numba import njit

# Bitboard helper functions with Numba JIT
@njit
def square_to_bit(square):
    """Convert chess square (0-63) to bitboard bit position"""
    return 1 << square

@njit
def bit_to_square(bit):
    """Convert bitboard bit to chess square (0-63) using Numba-compatible operations"""
    # Find position of set bit using loop
    for i in range(64):
        if bit & (1 << i):
            return i
    return 0

@njit
def pop_lsb(bb):
    """Get least significant bit and remove it"""
    lsb = bb & -bb
    bb ^= lsb
    return lsb, bb

@njit
def count_bits(bb):
    """Count number of set bits in bitboard using Numba-compatible operations"""
    count = 0
    while bb:
        bb &= bb - 1
        count += 1
    return count

# Piece types
EMPTY = 0
PAWN = 1
KNIGHT = 2
BISHOP = 3
ROOK = 4
QUEEN = 5
KING = 6

# Colors
WHITE = 0
BLACK = 1

# Piece letters for display
PIECE_LETTERS = {
    (WHITE, PAWN): 'P',
    (WHITE, KNIGHT): 'N',
    (WHITE, BISHOP): 'B',
    (WHITE, ROOK): 'R',
    (WHITE, QUEEN): 'Q',
    (WHITE, KING): 'K',
    (BLACK, PAWN): 'p',
    (BLACK, KNIGHT): 'n',
    (BLACK, BISHOP): 'b',
    (BLACK, ROOK): 'r',
    (BLACK, QUEEN): 'q',
    (BLACK, KING): 'k',
    (WHITE, EMPTY): '.',
    (BLACK, EMPTY): '.'
}

# Material values
PIECE_VALUES = {
    PAWN: 100,
    KNIGHT: 320,
    BISHOP: 330,
    ROOK: 500,
    QUEEN: 900,
    KING: 20000
}

class ChessEngine:
    def __init__(self, depth, use_backward_search=False, search_time=1.0, realtime=False, quiet=False):
        self.depth = depth
        self.use_backward_search = use_backward_search
        self.search_time = search_time
        self.realtime = realtime
        self.quiet = quiet
        self.use_opening_book = False
        
        # Analyzer compatibility
        self.current_search_depth = 0
        self.max_search_depth = 0  # Track maximum depth reached
        self.top_moves_cache = []
        self.principal_variations_cache = []
        self.realtime_callback = None
        
        # Transposition table for performance
        self.transposition_table = {}
        self.tt_size = 10000  # Maximum number of entries
        
        # Board state - bitboard representation
        # One bitboard per piece type per color
        self.bitboards = {
            WHITE: {PAWN: 0, KNIGHT: 0, BISHOP: 0, ROOK: 0, QUEEN: 0, KING: 0},
            BLACK: {PAWN: 0, KNIGHT: 0, BISHOP: 0, ROOK: 0, QUEEN: 0, KING: 0}
        }
        self.occupancy = {WHITE: 0, BLACK: 0}  # All pieces for each color
        self.total_occupancy = 0  # All pieces on board
        self.turn = WHITE
        self.castling_rights = {
            WHITE: {'kingside': True, 'queenside': True},
            BLACK: {'kingside': True, 'queenside': True}
        }
        self.en_passant_square = None
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.move_history = []
        
        # Move ordering cache for iterative deepening
        self.move_ordering_cache = {}  # Maps move tuple to score from previous depth
        
        # Keep 2D board for compatibility with existing code
        self.board = [[0 for _ in range(8)] for _ in range(8)]
        
        # Initialize board to starting position for move generation
        self.chess_board = chess.Board()
        self.reset_board()
    
    def clear_move_ordering_cache(self):
        """Clear the move ordering cache (call when board changes)"""
        self.move_ordering_cache.clear()
    
    def reset_board(self):
        """Initialize the board to starting position"""
        self.board = [[(WHITE, EMPTY) for _ in range(8)] for _ in range(8)]
        
        # Reset bitboards
        for color in [WHITE, BLACK]:
            for piece_type in [PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING]:
                self.bitboards[color][piece_type] = 0
        self.occupancy = {WHITE: 0, BLACK: 0}
        self.total_occupancy = 0
        
        # Black pieces
        self.board[0][0] = (BLACK, ROOK)
        self.board[0][1] = (BLACK, KNIGHT)
        self.board[0][2] = (BLACK, BISHOP)
        self.board[0][3] = (BLACK, QUEEN)
        self.board[0][4] = (BLACK, KING)
        self.board[0][5] = (BLACK, BISHOP)
        self.board[0][6] = (BLACK, KNIGHT)
        self.board[0][7] = (BLACK, ROOK)
        for col in range(8):
            self.board[1][col] = (BLACK, PAWN)
        
        # White pieces
        self.board[7][0] = (WHITE, ROOK)
        self.board[7][1] = (WHITE, KNIGHT)
        self.board[7][2] = (WHITE, BISHOP)
        self.board[7][3] = (WHITE, QUEEN)
        self.board[7][4] = (WHITE, KING)
        self.board[7][5] = (WHITE, BISHOP)
        self.board[7][6] = (WHITE, KNIGHT)
        self.board[7][7] = (WHITE, ROOK)
        for col in range(8):
            self.board[6][col] = (WHITE, PAWN)
        
        self.turn = WHITE
        
        # Sync bitboards from 2D board
        self.sync_bitboards_from_board()
    
    def sync_bitboards_from_board(self):
        """Sync bitboards from 2D board representation"""
        for color in [WHITE, BLACK]:
            for piece_type in [PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING]:
                self.bitboards[color][piece_type] = 0
        self.occupancy = {WHITE: 0, BLACK: 0}
        self.total_occupancy = 0
        
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece != (WHITE, EMPTY) and piece != (BLACK, EMPTY):
                    color, piece_type = piece
                    square = row * 8 + col
                    bit = square_to_bit(square)
                    self.bitboards[color][piece_type] |= bit
                    self.occupancy[color] |= bit
                    self.total_occupancy |= bit
    
    def sync_board_from_bitboards(self):
        """Sync 2D board from bitboards"""
        self.board = [[(WHITE, EMPTY) for _ in range(8)] for _ in range(8)]
        
        for color in [WHITE, BLACK]:
            for piece_type in [PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING]:
                bb = self.bitboards[color][piece_type]
                while bb:
                    lsb, bb = pop_lsb(bb)
                    square = bit_to_square(lsb)
                    row = square // 8
                    col = square % 8
                    self.board[row][col] = (color, piece_type)
        self.chess_board.reset()
    
    def get_piece_at(self, row, col):
        """Get piece at given square"""
        if 0 <= row < 8 and 0 <= col < 8:
            return self.board[row][col]
        return (WHITE, EMPTY)
    
    def is_empty_square(self, row, col):
        """Check if square is empty"""
        if 0 <= row < 8 and 0 <= col < 8:
            piece = self.board[row][col]
            return piece == (WHITE, EMPTY) or piece == (BLACK, EMPTY)
        return False
    
    def is_valid_square(self, row, col):
        """Check if square is within board"""
        return 0 <= row < 8 and 0 <= col < 8
    
    def get_piece_color(self, piece):
        """Get color of a piece"""
        if piece == 0 or piece == (WHITE, EMPTY):
            return WHITE
        if isinstance(piece, tuple):
            return piece[0]
        return WHITE
    
    def get_piece_type(self, piece):
        """Get type of a piece"""
        if piece == 0 or piece == (WHITE, EMPTY):
            return EMPTY
        if isinstance(piece, tuple):
            return piece[1]
        return EMPTY
    
    def sync_to_chess_board(self):
        """Sync custom board state to python-chess board"""
        # Create a new chess board
        self.chess_board = chess.Board()
        
        # Clear the board
        self.chess_board.clear()
        
        # Transfer pieces from custom board to chess board
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece != (WHITE, EMPTY) and piece != (BLACK, EMPTY):
                    color, piece_type = piece
                    
                    # Map custom engine piece types to chess piece types
                    piece_type_map = {
                        PAWN: chess.PAWN,
                        KNIGHT: chess.KNIGHT,
                        BISHOP: chess.BISHOP,
                        ROOK: chess.ROOK,
                        QUEEN: chess.QUEEN,
                        KING: chess.KING
                    }
                    
                    chess_color = chess.WHITE if color == WHITE else chess.BLACK
                    chess_piece_type = piece_type_map[piece_type]
                    
                    # Convert to chess square
                    square = chess.square(col, 7 - row)
                    self.chess_board.set_piece_at(square, chess.Piece(chess_piece_type, chess_color))
        
        # Set turn
        self.chess_board.turn = chess.WHITE if self.turn == WHITE else chess.BLACK
        
        # Set castling rights
        if self.castling_rights[WHITE]['kingside']:
            self.chess_board.castling_rights |= chess.BB_H1
        if self.castling_rights[WHITE]['queenside']:
            self.chess_board.castling_rights |= chess.BB_A1
        if self.castling_rights[BLACK]['kingside']:
            self.chess_board.castling_rights |= chess.BB_H8
        if self.castling_rights[BLACK]['queenside']:
            self.chess_board.castling_rights |= chess.BB_A8
        
        # Set en passant square
        if self.en_passant_square:
            ep_row, ep_col = self.en_passant_square
            ep_square = chess.square(ep_col, 7 - ep_row)
            self.chess_board.ep_square = ep_square
        
        # Set move counters
        self.chess_board.halfmove_clock = self.halfmove_clock
        self.chess_board.fullmove_number = self.fullmove_number
    
    def sync_from_chess_board(self):
        """Sync python-chess board state back to custom board"""
        # Clear custom board
        for row in range(8):
            for col in range(8):
                self.board[row][col] = (WHITE, EMPTY)
        
        # Transfer pieces from chess board to custom board
        for square in chess.SQUARES:
            piece = self.chess_board.piece_at(square)
            if piece:
                row = 7 - chess.square_rank(square)
                col = chess.square_file(square)
                
                color = WHITE if piece.color == chess.WHITE else BLACK
                
                # Map chess piece types to custom engine piece types
                piece_type_map = {
                    chess.PAWN: PAWN,
                    chess.KNIGHT: KNIGHT,
                    chess.BISHOP: BISHOP,
                    chess.ROOK: ROOK,
                    chess.QUEEN: QUEEN,
                    chess.KING: KING
                }
                piece_type = piece_type_map[piece.piece_type]
                
                self.board[row][col] = (color, piece_type)
        
        # Set turn
        self.turn = WHITE if self.chess_board.turn == chess.WHITE else BLACK
        
        # Set castling rights
        self.castling_rights[WHITE]['kingside'] = self.chess_board.has_kingside_castling_rights(chess.WHITE)
        self.castling_rights[WHITE]['queenside'] = self.chess_board.has_queenside_castling_rights(chess.WHITE)
        self.castling_rights[BLACK]['kingside'] = self.chess_board.has_kingside_castling_rights(chess.BLACK)
        self.castling_rights[BLACK]['queenside'] = self.chess_board.has_queenside_castling_rights(chess.BLACK)
        
        # Set en passant square
        if self.chess_board.ep_square is not None:
            ep_row = 7 - chess.square_rank(self.chess_board.ep_square)
            ep_col = chess.square_file(self.chess_board.ep_square)
            self.en_passant_square = (ep_row, ep_col)
        else:
            self.en_passant_square = None
        
        # Set move counters
        self.halfmove_clock = self.chess_board.halfmove_clock
        self.fullmove_number = self.chess_board.fullmove_number
    
    def generate_pseudo_legal_moves(self):
        """Generate all pseudo-legal moves for current position using python-chess"""
        # Sync custom board to chess board
        self.sync_to_chess_board()
        
        # Get pseudo-legal moves from python-chess
        chess_moves = list(self.chess_board.pseudo_legal_moves)
        
        # Convert to custom move format
        custom_moves = []
        for chess_move in chess_moves:
            custom_moves.append(self.chess_to_custom_move(chess_move))
        
        return custom_moves
    
    def generate_pawn_moves(self, row, col):
        """Generate pawn moves"""
        moves = []
        color = self.turn
        direction = -1 if color == WHITE else 1
        start_row = 6 if color == WHITE else 1
        
        # Forward move
        new_row = row + direction
        if self.is_valid_square(new_row, col):
            target = self.board[new_row][col]
            if target == (WHITE, EMPTY) or target == (BLACK, EMPTY):
                # Check for promotion
                if new_row == 0 or new_row == 7:
                    for promotion in [QUEEN, ROOK, BISHOP, KNIGHT]:
                        moves.append(((row, col), (new_row, col), promotion))
                else:
                    moves.append(((row, col), (new_row, col), None))
                
                # Double forward move from starting position
                if row == start_row:
                    new_row2 = row + 2 * direction
                    if self.is_valid_square(new_row2, col):
                        target2 = self.board[new_row2][col]
                        if target2 == (WHITE, EMPTY) or target2 == (BLACK, EMPTY):
                            moves.append(((row, col), (new_row2, col), None))
        
        # Captures
        for dc in [-1, 1]:
            new_col = col + dc
            new_row = row + direction
            if self.is_valid_square(new_row, new_col):
                target = self.board[new_row][new_col]
                if target != (WHITE, EMPTY) and target != (BLACK, EMPTY):
                    target_color = target[0]
                    if target_color != color:
                        if new_row == 0 or new_row == 7:
                            for promotion in [QUEEN, ROOK, BISHOP, KNIGHT]:
                                moves.append(((row, col), (new_row, new_col), promotion))
                        else:
                            moves.append(((row, col), (new_row, new_col), None))
        
        # En passant
        if self.en_passant_square:
            ep_row, ep_col = self.en_passant_square
            if new_row == ep_row and (col - 1 == ep_col or col + 1 == ep_col):
                moves.append(((row, col), (ep_row, ep_col), None))
        
        return moves
    
    def generate_knight_moves(self, row, col):
        """Generate knight moves"""
        moves = []
        offsets = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
        
        for dr, dc in offsets:
            new_row, new_col = row + dr, col + dc
            if self.is_valid_square(new_row, new_col):
                target = self.board[new_row][new_col]
                if target == (WHITE, EMPTY) or target == (BLACK, EMPTY):
                    moves.append(((row, col), (new_row, new_col), None))
                else:
                    target_color = target[0]
                    if target_color != self.turn:
                        moves.append(((row, col), (new_row, new_col), None))
        
        return moves
    
    def generate_bishop_moves(self, row, col):
        """Generate bishop moves"""
        moves = []
        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        
        for dr, dc in directions:
            for i in range(1, 8):
                new_row, new_col = row + dr * i, col + dc * i
                if not self.is_valid_square(new_row, new_col):
                    break
                
                target = self.board[new_row][new_col]
                if target == (WHITE, EMPTY) or target == (BLACK, EMPTY):
                    moves.append(((row, col), (new_row, new_col), None))
                else:
                    target_color = target[0]
                    if target_color != self.turn:
                        moves.append(((row, col), (new_row, new_col), None))
                    break
        
        return moves
    
    def generate_rook_moves(self, row, col):
        """Generate rook moves"""
        moves = []
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        
        for dr, dc in directions:
            for i in range(1, 8):
                new_row, new_col = row + dr * i, col + dc * i
                if not self.is_valid_square(new_row, new_col):
                    break
                
                target = self.board[new_row][new_col]
                if target == (WHITE, EMPTY) or target == (BLACK, EMPTY):
                    moves.append(((row, col), (new_row, new_col), None))
                else:
                    target_color = target[0]
                    if target_color != self.turn:
                        moves.append(((row, col), (new_row, new_col), None))
                    break
        
        return moves
    
    def generate_queen_moves(self, row, col):
        """Generate queen moves"""
        moves = []
        moves.extend(self.generate_bishop_moves(row, col))
        moves.extend(self.generate_rook_moves(row, col))
        return moves
    
    def generate_king_moves(self, row, col):
        """Generate king moves including castling"""
        moves = []
        offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
        
        for dr, dc in offsets:
            new_row, new_col = row + dr, col + dc
            if self.is_valid_square(new_row, new_col):
                target = self.board[new_row][new_col]
                if target == (WHITE, EMPTY) or target == (BLACK, EMPTY):
                    moves.append(((row, col), (new_row, new_col), None))
                else:
                    target_color = target[0]
                    if target_color != self.turn:
                        moves.append(((row, col), (new_row, new_col), None))
        
        # Castling
        color = self.turn
        if color == WHITE:
            king_row = 7
        else:
            king_row = 0
        
        if row == king_row and col == 4:
            # Kingside castling
            if self.castling_rights[color]['kingside']:
                if (self.board[king_row][5] == 0 or self.board[king_row][5] == (WHITE, EMPTY)) and \
                   (self.board[king_row][6] == 0 or self.board[king_row][6] == (WHITE, EMPTY)):
                    if not self.is_square_attacked(king_row, 4, 1 - color) and \
                       not self.is_square_attacked(king_row, 5, 1 - color) and \
                       not self.is_square_attacked(king_row, 6, 1 - color):
                        moves.append(((row, col), (king_row, 6), None))
            
            # Queenside castling
            if self.castling_rights[color]['queenside']:
                if (self.board[king_row][1] == 0 or self.board[king_row][1] == (WHITE, EMPTY)) and \
                   (self.board[king_row][2] == 0 or self.board[king_row][2] == (WHITE, EMPTY)) and \
                   (self.board[king_row][3] == 0 or self.board[king_row][3] == (WHITE, EMPTY)):
                    if not self.is_square_attacked(king_row, 4, 1 - color) and \
                       not self.is_square_attacked(king_row, 3, 1 - color) and \
                       not self.is_square_attacked(king_row, 2, 1 - color):
                        moves.append(((row, col), (king_row, 2), None))
        
        return moves
    
    def is_square_attacked(self, row, col, by_color):
        """Check if a square is attacked by given color"""
        # Check pawn attacks
        pawn_direction = 1 if by_color == WHITE else -1
        for dc in [-1, 1]:
            pawn_row = row + pawn_direction
            pawn_col = col + dc
            if self.is_valid_square(pawn_row, pawn_col):
                piece = self.board[pawn_row][pawn_col]
                if piece != 0 and piece != (WHITE, EMPTY):
                    if piece[0] == by_color and piece[1] == PAWN:
                        return True
        
        # Check knight attacks
        knight_offsets = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
        for dr, dc in knight_offsets:
            knight_row, knight_col = row + dr, col + dc
            if self.is_valid_square(knight_row, knight_col):
                piece = self.board[knight_row][knight_col]
                if piece != 0 and piece != (WHITE, EMPTY):
                    if piece[0] == by_color and piece[1] == KNIGHT:
                        return True
        
        # Check king attacks
        king_offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
        for dr, dc in king_offsets:
            king_row, king_col = row + dr, col + dc
            if self.is_valid_square(king_row, king_col):
                piece = self.board[king_row][king_col]
                if piece != 0 and piece != (WHITE, EMPTY):
                    if piece[0] == by_color and piece[1] == KING:
                        return True
        
        # Check sliding piece attacks (bishop, rook, queen)
        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        for dr, dc in directions:
            for i in range(1, 8):
                check_row, check_col = row + dr * i, col + dc * i
                if not self.is_valid_square(check_row, check_col):
                    break
                piece = self.board[check_row][check_col]
                if piece != 0 and piece != (WHITE, EMPTY):
                    if piece[0] == by_color and piece[1] in [BISHOP, QUEEN]:
                        return True
                    break
        
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for dr, dc in directions:
            for i in range(1, 8):
                check_row, check_col = row + dr * i, col + dc * i
                if not self.is_valid_square(check_row, check_col):
                    break
                piece = self.board[check_row][check_col]
                if piece != 0 and piece != (WHITE, EMPTY):
                    if piece[0] == by_color and piece[1] in [ROOK, QUEEN]:
                        return True
                    break
        
        return False
    
    def find_king(self, color):
        """Find king position for given color"""
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece != 0 and piece != (WHITE, EMPTY):
                    if piece[0] == color and piece[1] == KING:
                        return (row, col)
        return None
    
    def is_in_check(self, color):
        """Check if given color is in check using python-chess"""
        # Sync custom board to chess board
        self.sync_to_chess_board()
        
        # Check if the given color is in check
        chess_color = chess.WHITE if color == WHITE else chess.BLACK
        return self.chess_board.is_check()
    
    def generate_legal_moves(self):
        """Generate all legal moves using python-chess"""
        # Sync custom board to chess board
        self.sync_to_chess_board()
        
        # Get legal moves from python-chess
        chess_moves = list(self.chess_board.legal_moves)
        
        # Convert to custom move format
        custom_moves = []
        for chess_move in chess_moves:
            custom_moves.append(self.chess_to_custom_move(chess_move))
        
        return custom_moves
    
    def make_move(self, move, temporary=False):
        """Make a move on the board using python-chess"""
        # Sync custom board to chess board
        self.sync_to_chess_board()
        
        # Convert custom move to chess move
        chess_move = self.custom_to_chess_move(move)
        
        # Store state for unmaking
        state = {
            'chess_board': self.chess_board.copy(),
            'turn': self.turn,
            'halfmove_clock': self.halfmove_clock,
            'fullmove_number': self.fullmove_number,
            'castling_rights': {color: rights.copy() for color, rights in self.castling_rights.items()},
            'en_passant_square': self.en_passant_square
        }
        
        # Make the move on chess board
        if chess_move not in self.chess_board.legal_moves:
            return False
        
        self.chess_board.push(chess_move)
        
        # Sync back to custom board and bitboards
        self.sync_from_chess_board()
        self.sync_bitboards_from_board()
        
        if temporary:
            self.move_history.append(state)
            return True
        
        # Update turn
        self.turn = 1 - self.turn
        self.move_history.append(state)
        return True
    
    def unmake_move(self, temporary=False):
        """Unmake the last move"""
        if not self.move_history:
            return
        
        state = self.move_history.pop()
        
        # Restore chess board state
        self.chess_board = state['chess_board'].copy()
        
        # Sync chess board back to custom board
        self.sync_from_chess_board()
        
        # Restore other state
        self.turn = state['turn']
        self.halfmove_clock = state['halfmove_clock']
        self.fullmove_number = state['fullmove_number']
        self.castling_rights = state['castling_rights']
        self.en_passant_square = state['en_passant_square']
        
        if not temporary:
            if self.turn == BLACK:
                self.fullmove_number -= 1
    
    def is_checkmate(self):
        """Check if current position is checkmate using python-chess"""
        # Sync custom board to chess board
        self.sync_to_chess_board()
        return self.chess_board.is_checkmate()
    
    def is_stalemate(self):
        """Check if current position is stalemate using python-chess"""
        # Sync custom board to chess board
        self.sync_to_chess_board()
        return self.chess_board.is_stalemate()
    
    @lru_cache(maxsize=1024)
    def evaluate_material_cached(self, board_tuple, turn):
        """Cached material evaluation for performance using bitboards"""
        white_score = 0
        black_score = 0
        
        # Center control squares as bits
        center_bits = square_to_bit(27) | square_to_bit(28) | square_to_bit(35) | square_to_bit(36)
        
        for row in range(8):
            for col in range(8):
                piece = board_tuple[row][col]
                if piece != (WHITE, EMPTY) and piece != (BLACK, EMPTY):
                    color, piece_type = piece
                    value = PIECE_VALUES[piece_type]
                    square = row * 8 + col
                    bit = square_to_bit(square)
                    
                    # Heavily prioritize material value - this is the most important factor
                    # Add positional bonus for center control (secondary to material)
                    if bit & center_bits:
                        value += 5  # Reduced from 10 to make material more dominant
                    
                    # Add bonus for knights and bishops in center (secondary)
                    if piece_type in [KNIGHT, BISHOP] and bit & center_bits:
                        value += 10  # Reduced from 20
                    
                    # Add bonus for pawns advancing (secondary)
                    if piece_type == PAWN:
                        if color == WHITE and row < 4:
                            value += 5  # Reduced from 10
                        elif color == BLACK and row > 3:
                            value += 5  # Reduced from 10
                    
                    if color == WHITE:
                        white_score += value
                    else:
                        black_score += value
        
        return white_score - black_score
    
    def evaluate_material(self):
        """Material evaluation with strong tactical capture priority"""
        # Convert board to tuple for caching
        board_tuple = tuple(tuple(row) for row in self.board)
        return self.evaluate_material_cached(board_tuple, self.turn)
    
    def quiescence_search(self, alpha, beta, ply_count):
        """Quiescence search to extend tactical captures beyond depth 0"""
        stand_pat = self.evaluate_material()
        
        if ply_count > 10:  # Limit quiescence depth
            return stand_pat
        
        if self.turn == WHITE:
            if stand_pat >= beta:
                return beta
            if stand_pat > alpha:
                alpha = stand_pat
        else:
            if stand_pat <= alpha:
                return alpha
            if stand_pat < beta:
                beta = stand_pat
        
        # Generate only capture moves using custom move system
        legal_moves = self.generate_legal_moves()
        
        # Filter for captures only
        capture_moves = []
        for move in legal_moves:
            from_sq, to_sq, promotion = move
            # Check if this is a capture (destination square has a piece)
            if self.board[to_sq[0]][to_sq[1]] != (WHITE, EMPTY) and self.board[to_sq[0]][to_sq[1]] != (BLACK, EMPTY):
                capture_moves.append(move)
        
        for move in capture_moves:
            if self.make_move(move, temporary=True):
                score = self.quiescence_search(alpha, beta, ply_count + 1)
                self.unmake_move(temporary=True)
                
                if self.turn == WHITE:  # After unmake, turn is back to original
                    if score >= beta:
                        return beta
                    if score > alpha:
                        alpha = score
                else:
                    if score <= alpha:
                        return alpha
                    if score < beta:
                        beta = score
        
        return alpha if self.turn == WHITE else beta
    
    def get_board_hash(self):
        """Generate a simple hash of the board position for transposition table."""
        board_tuple = tuple(tuple(row) for row in self.board)
        return hash((board_tuple, self.turn))
    
    def minimax(self, ply, alpha, beta, is_maximizing, ply_count=0):
        """Minimax with alpha-beta pruning, move ordering, transposition table, and null-move pruning"""
        # Check transposition table
        board_hash = self.get_board_hash()
        if board_hash in self.transposition_table:
            cached_depth, cached_score = self.transposition_table[board_hash]
            if cached_depth >= ply:
                return cached_score
        
        if ply == 0:
            return self.quiescence_search(alpha, beta, ply_count)
        
        if self.is_checkmate():
            if is_maximizing:
                return -100000 + ply_count  # Black checkmated
            else:
                return 100000 - ply_count  # White checkmated
        
        if self.is_stalemate():
            return 0  # Draw
        
        # Null-move pruning
        # Don't use in check, at low depth, or in endgame (few pieces)
        if ply >= 3 and not self.is_in_check(self.turn) and self.total_occupancy.bit_count() > 10:
            # Make null move (skip turn)
            self.turn = 1 - self.turn
            # Search with reduced depth
            R = 2  # Reduction depth
            null_score = self.minimax(ply - 1 - R, alpha, beta, not is_maximizing, ply_count + 1)
            # Undo null move
            self.turn = 1 - self.turn
            
            # If null move fails high, the position is good enough to prune
            if is_maximizing:
                if null_score >= beta:
                    return beta
            else:
                if null_score <= alpha:
                    return alpha
        
        legal_moves = self.generate_legal_moves()
        
        # Order moves for better pruning (only at deeper depths to avoid overhead)
        if ply > 2:
            legal_moves = self.order_moves(legal_moves)
        
        if is_maximizing:
            max_eval = float('-inf')
            for move in legal_moves:
                if self.make_move(move, temporary=True):
                    eval_score = self.minimax(ply - 1, alpha, beta, False, ply_count + 1)
                    self.unmake_move(temporary=True)
                    max_eval = max(max_eval, eval_score)
                    alpha = max(alpha, eval_score)
                    if beta <= alpha:
                        break
            # Store in transposition table
            if len(self.transposition_table) < self.tt_size:
                self.transposition_table[board_hash] = (ply, max_eval)
            return max_eval
        else:
            min_eval = float('inf')
            for move in legal_moves:
                if self.make_move(move, temporary=True):
                    eval_score = self.minimax(ply - 1, alpha, beta, True, ply_count + 1)
                    self.unmake_move(temporary=True)
                    min_eval = min(min_eval, eval_score)
                    beta = min(beta, eval_score)
                    if beta <= alpha:
                        break
            # Store in transposition table
            if len(self.transposition_table) < self.tt_size:
                self.transposition_table[board_hash] = (ply, min_eval)
            return min_eval
    
    def order_moves(self, moves):
        """Order moves for better alpha-beta pruning using cache from previous depth"""
        move_order = []
        
        for move in moves:
            from_sq, to_sq, promotion = move
            score = 0
            
            # Use cached score from previous depth if available
            move_key = tuple(move)
            if move_key in self.move_ordering_cache:
                score = self.move_ordering_cache[move_key]
            else:
                # Prioritize captures (MVV-LVA: Most Valuable Victim - Least Valuable Attacker)
                if self.board[to_sq[0]][to_sq[1]] != (WHITE, EMPTY) and self.board[to_sq[0]][to_sq[1]] != (BLACK, EMPTY):
                    victim_color, victim_type = self.board[to_sq[0]][to_sq[1]]
                    attacker_color, attacker_type = self.board[from_sq[0]][from_sq[1]]
                    # Ensure attacker is not empty
                    if attacker_type != EMPTY:
                        score = PIECE_VALUES[victim_type] * 10 - PIECE_VALUES[attacker_type]
                
                # Prioritize promotions
                if promotion:
                    score += PIECE_VALUES[promotion] * 5
                
                # Prioritize checks
                if self.make_move(move, temporary=True):
                    if self.is_checkmate():
                        score += 10000  # Checkmate is best
                    elif self.is_in_check(self.turn):
                        score += 50  # Give check
                    self.unmake_move(temporary=True)
            
            move_order.append((move, score))
        
        # Sort by score (descending)
        move_order.sort(key=lambda x: x[1], reverse=True)
        
        return [move for move, score in move_order]
    
    def rank_moves(self):
        """Rank all legal moves from best to worst and cache scores for iterative deepening"""
        legal_moves = self.generate_legal_moves()
        
        if not legal_moves:
            return []
        
        # Order moves for better pruning
        ordered_moves = self.order_moves(legal_moves)
        
        move_scores = []
        plies = self.depth * 2  # Use engine's depth, not Settings
        is_white_turn = (self.turn == WHITE)
        
        for move in ordered_moves:
            if self.make_move(move, temporary=True):
                # After making move, turn flips, so we pass the opposite
                score = self.minimax(plies - 1, float('-inf'), float('inf'), not is_white_turn, 1)
                self.unmake_move(temporary=True)
                move_scores.append((move, score))
                
                # Cache the score for this move for use in deeper searches
                move_key = tuple(move)
                self.move_ordering_cache[move_key] = score
        
        # Sort by score (descending for White, ascending for Black)
        if is_white_turn:
            move_scores.sort(key=lambda x: x[1], reverse=True)
        else:
            move_scores.sort(key=lambda x: x[1])
        
        return [move for move, score in move_scores]
    
    def get_best_move(self):
        """Get the best move for current position"""
        ranked_moves = self.rank_moves()
        if ranked_moves:
            return ranked_moves[0]
        return None
    
    def get_piece_letter(self, piece):
        """Get letter representation of a piece"""
        if piece == 0 or piece == (WHITE, EMPTY):
            return '.'
        return PIECE_LETTERS[piece]
    
    # Analyzer compatibility methods
    def chess_to_custom_board(self, chess_board):
        """Convert chess.Board to custom engine board format."""
        # Handle both chess.Board and our Board wrapper
        if hasattr(chess_board, 'board'):
            # It's our Board wrapper, get the underlying chess.Board
            actual_board = chess_board.board
        else:
            # It's already a chess.Board
            actual_board = chess_board
        
        # Reset the custom engine
        self.reset_board()
        
        # Clear the board first using proper empty square format
        for row in range(8):
            for col in range(8):
                self.board[row][col] = (WHITE, EMPTY)
        
        # Transfer pieces from chess board to custom board
        for square in chess.SQUARES:
            piece = actual_board.piece_at(square)
            if piece:
                row = 7 - chess.square_rank(square)
                col = chess.square_file(square)
                
                color = WHITE if piece.color == chess.WHITE else BLACK
                
                # Map chess piece types to custom engine piece types
                piece_type_map = {
                    chess.PAWN: PAWN,
                    chess.KNIGHT: KNIGHT,
                    chess.BISHOP: BISHOP,
                    chess.ROOK: ROOK,
                    chess.QUEEN: QUEEN,
                    chess.KING: KING
                }
                piece_type = piece_type_map[piece.piece_type]
                
                self.board[row][col] = (color, piece_type)
        
        # Set turn
        self.turn = WHITE if actual_board.turn == chess.WHITE else BLACK
        
        # Set castling rights
        self.castling_rights[WHITE]['kingside'] = actual_board.has_kingside_castling_rights(chess.WHITE)
        self.castling_rights[WHITE]['queenside'] = actual_board.has_queenside_castling_rights(chess.WHITE)
        self.castling_rights[BLACK]['kingside'] = actual_board.has_kingside_castling_rights(chess.BLACK)
        self.castling_rights[BLACK]['queenside'] = actual_board.has_queenside_castling_rights(chess.BLACK)
        
        # Set en passant square
        if actual_board.ep_square is not None:
            ep_row = 7 - chess.square_rank(actual_board.ep_square)
            ep_col = chess.square_file(actual_board.ep_square)
            self.en_passant_square = (ep_row, ep_col)
        else:
            self.en_passant_square = None
    
    def custom_to_chess_move(self, custom_move):
        """Convert custom engine move format to chess.Move."""
        from_square, to_square, promotion = custom_move
        
        # Convert custom coordinates to chess square indices
        from_file = from_square[1]
        from_rank = 7 - from_square[0]
        to_file = to_square[1]
        to_rank = 7 - to_square[0]
        
        from_sq = chess.square(from_file, from_rank)
        to_sq = chess.square(to_file, to_rank)
        
        # Handle promotion
        promotion_piece = None
        if promotion:
            promotion_map = {
                QUEEN: chess.QUEEN,
                ROOK: chess.ROOK,
                BISHOP: chess.BISHOP,
                KNIGHT: chess.KNIGHT
            }
            promotion_piece = promotion_map[promotion]
        
        return chess.Move(from_sq, to_sq, promotion=promotion_piece)
    
    def chess_to_custom_move(self, chess_move):
        """Convert chess.Move to custom engine move format."""
        from_sq = chess_move.from_square
        to_sq = chess_move.to_square
        
        # Convert chess square indices to custom coordinates
        from_row = 7 - chess.square_rank(from_sq)
        from_col = chess.square_file(from_sq)
        to_row = 7 - chess.square_rank(to_sq)
        to_col = chess.square_file(to_sq)
        
        # Handle promotion
        promotion = None
        if chess_move.promotion:
            promotion_map = {
                chess.QUEEN: QUEEN,
                chess.ROOK: ROOK,
                chess.BISHOP: BISHOP,
                chess.KNIGHT: KNIGHT
            }
            promotion = promotion_map[chess_move.promotion]
        
        return ((from_row, from_col), (to_row, to_col), promotion)
    
    def search(self, chess_board):
        """Search function compatible with analyzer interface with iterative deepening."""
        # Convert chess board to custom engine format
        self.chess_to_custom_board(chess_board)
        
        # Implement iterative deepening for real-time updates
        max_depth = self.depth * 2  # Convert to plies
        best_chess_move = None
        best_score = 0
        
        # Initialize top moves cache
        self.top_moves_cache = []
        
        # Search iteratively from depth 1 to max_depth
        for current_depth in range(1, max_depth + 1):
            # Update current search depth for analyzer (don't reset to 0)
            self.current_search_depth = current_depth
            self.max_search_depth = max(self.max_search_depth, current_depth)
            
            # Temporarily adjust engine depth for this iteration
            original_depth = self.depth
            self.depth = current_depth // 2 if current_depth % 2 == 0 else (current_depth + 1) // 2
            
            # Get ranked moves at current depth
            ranked_custom_moves = self.rank_moves()
            
            # Reset depth for next iteration
            self.depth = original_depth
            
            # Evaluate each move and populate cache
            current_top_moves = []
            for custom_move in ranked_custom_moves:
                chess_move = self.custom_to_chess_move(custom_move)
                # Get evaluation for this move
                self.chess_to_custom_board(chess_board)
                if self.make_move(custom_move, temporary=True):
                    score = self.evaluate_material()
                    self.unmake_move(temporary=True)
                    current_top_moves.append((chess_move, score))
            
            # Update top moves cache with latest results
            self.top_moves_cache = current_top_moves
            
            # Get best move from current iteration
            if current_top_moves:
                best_chess_move = current_top_moves[0][0]
                best_score = current_top_moves[0][1]
                
                # Generate principal variations for current depth
                self.principal_variations_cache = []
                for i, (chess_move, score) in enumerate(current_top_moves[:3]):
                    # Generate a simple PV line by following best responses
                    pv_line = self.generate_pv_line(chess_move, depth=5)
                    self.principal_variations_cache.append(pv_line)
                
                # Call realtime callback if set
                if self.realtime_callback:
                    self.realtime_callback(best_chess_move, best_score)
        
        # Keep current_search_depth at max depth for analyzer to show
        # Don't reset to 0 so analyzer can show the final depth
        
        # Return final best move
        return best_chess_move
    
    def generate_pv_line(self, first_move, depth=5):
        """Generate a principal variation line starting with the given move."""
        pv_line = [first_move.uci()]
        
        # Sync to chess board for PV generation
        self.sync_to_chess_board()
        
        # Create a temporary board to simulate the line
        temp_board = self.chess_board.copy()
        
        try:
            # Make the first move
            if first_move in temp_board.legal_moves:
                temp_board.push(first_move)
                
                # Follow simple material-based best responses for the remaining depth
                for _ in range(depth - 1):
                    # Get all legal moves and pick the one with best material gain
                    legal_moves = list(temp_board.legal_moves)
                    if not legal_moves:
                        break
                    
                    # Simple evaluation: prefer captures
                    best_move = None
                    best_score = float('-inf')
                    
                    for move in legal_moves:
                        score = 0
                        # Prioritize captures
                        if temp_board.is_capture(move):
                            captured_piece = temp_board.piece_at(move.to_square)
                            if captured_piece:
                                # Simple piece values
                                piece_values = {
                                    chess.PAWN: 100,
                                    chess.KNIGHT: 320,
                                    chess.BISHOP: 330,
                                    chess.ROOK: 500,
                                    chess.QUEEN: 900,
                                    chess.KING: 0
                                }
                                score = piece_values.get(captured_piece.piece_type, 0)
                        
                        # Slight preference for checks
                        temp_board.push(move)
                        if temp_board.is_check():
                            score += 50
                        temp_board.pop()
                        
                        if score > best_score:
                            best_score = score
                            best_move = move
                    
                    if best_move:
                        pv_line.append(best_move.uci())
                        temp_board.push(best_move)
                    else:
                        # If no captures, just pick first legal move
                        pv_line.append(legal_moves[0].uci())
                        temp_board.push(legal_moves[0])
        except Exception:
            pass
        
        return pv_line
    
    def get_top_moves(self):
        """Return top moves with evaluations."""
        return self.top_moves_cache
    
    def get_principal_variations(self):
        """Return principal variations."""
        return self.principal_variations_cache
    
    def evaluate_material_chess(self, chess_board):
        """Evaluate material for a given chess board using chess library."""
        # Handle both chess.Board and our Board wrapper
        if hasattr(chess_board, 'board'):
            # It's our Board wrapper, get the underlying chess.Board
            actual_board = chess_board.board
        else:
            # It's already a chess.Board
            actual_board = chess_board
        
        # Use chess library to calculate material
        piece_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 20000
        }
        
        white_score = 0
        black_score = 0
        
        for square in chess.SQUARES:
            piece = actual_board.piece_at(square)
            if piece:
                value = piece_values[piece.piece_type]
                if piece.color == chess.WHITE:
                    white_score += value
                else:
                    black_score += value
        
        return white_score - black_score
    
    def set_realtime_callback(self, callback):
        """Set callback for real-time updates."""
        self.realtime_callback = callback
    
    def get_current_analysis(self):
        """Get current analysis data for analyzer."""
        # Use max_search_depth if available, otherwise current_search_depth, otherwise engine depth
        depth_to_report = self.max_search_depth if self.max_search_depth > 0 else (self.current_search_depth if self.current_search_depth > 0 else self.depth)
        return {
            'best_move': self.top_moves_cache[0][0] if self.top_moves_cache else None,
            'evaluation': self.top_moves_cache[0][1] if self.top_moves_cache else 0,
            'top_moves': self.top_moves_cache,
            'principal_variations': self.principal_variations_cache,
            'depth': depth_to_report
        }
    
    def display_board(self):
        """Display the board with letter-based pieces"""
        print("  a b c d e f g h")
        for row in range(8):
            row_str = f"{8 - row} "
            for col in range(8):
                piece = self.board[row][col]
                if piece == 0 or piece == (WHITE, EMPTY):
                    row_str += ". "
                else:
                    row_str += PIECE_LETTERS[piece] + " "
            print(row_str + f"{8 - row}")
        print("  a b c d e f g h")