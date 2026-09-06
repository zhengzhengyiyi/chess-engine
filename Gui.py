"""Pygame GUI for chess engine with 2 AI players."""

import sys
sys.path.append('.')
import pygame
import chess
import time
import threading
from engine.Engine import ChessEngine, WHITE, BLACK
from board import Board
import board_renderer

# Colors
LIGHT = (240, 217, 181)
DARK = (181, 136, 99)
MOVE_HL = (186, 202, 68, 180)
CHECK_HL = (220, 20, 60, 160)

# Board settings
SQ = 80
BSIZ = SQ * 8
WINDOW_WIDTH = BSIZ
WINDOW_HEIGHT = BSIZ

class ChessGUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Chess AI vs AI")
        
        # Fonts
        self.piece_font = pygame.font.SysFont('Arial', 48, bold=True)
        self.label_font = pygame.font.SysFont('Arial', 14)
        self.info_font = pygame.font.SysFont('Arial', 16)
        
        # Load piece images
        self.piece_images = {}
        pieces = {
            (chess.WHITE, chess.PAWN): 'assets/pieces-png/white-pawn.png',
            (chess.WHITE, chess.KNIGHT): 'assets/pieces-png/white-knight.png',
            (chess.WHITE, chess.BISHOP): 'assets/pieces-png/white-bishop.png',
            (chess.WHITE, chess.ROOK): 'assets/pieces-png/white-rook.png',
            (chess.WHITE, chess.QUEEN): 'assets/pieces-png/white-queen.png',
            (chess.WHITE, chess.KING): 'assets/pieces-png/white-king.png',
            (chess.BLACK, chess.PAWN): 'assets/pieces-png/black-pawn.png',
            (chess.BLACK, chess.KNIGHT): 'assets/pieces-png/black-knight.png',
            (chess.BLACK, chess.BISHOP): 'assets/pieces-png/black-bishop.png',
            (chess.BLACK, chess.ROOK): 'assets/pieces-png/black-rook.png',
            (chess.BLACK, chess.QUEEN): 'assets/pieces-png/black-queen.png',
            (chess.BLACK, chess.KING): 'assets/pieces-png/black-king.png',
        }
        
        for piece_key, path in pieces.items():
            try:
                image = pygame.image.load(path)
                self.piece_images[piece_key] = pygame.transform.scale(image, (SQ - 10, SQ - 10))
            except:
                print(f"Failed to load {path}")
                self.piece_images[piece_key] = None
        
        # Board state
        self.board = Board()
        self.last_move = None
        
        # Load depth from Settings.py
        try:
            from Settings import depth
            self.search_depth = depth
        except:
            self.search_depth = 3
        
        # Create two engines (one for each color)
        self.white_engine = ChessEngine(depth=self.search_depth, use_backward_search=False, 
                                       search_time=1.0, realtime=False, quiet=True)
        self.black_engine = ChessEngine(depth=self.search_depth, use_backward_search=False, 
                                       search_time=1.0, realtime=False, quiet=True)
        
        self.white_engine.use_opening_book = False
        self.black_engine.use_opening_book = False
        
        self.game_over = False
        self.winner = None
        self.move_delay = 0.5  # Seconds between moves
        self.last_move_time = 0
        
        # Threading for AI moves
        self.ai_thread = None
        self.ai_lock = threading.Lock()
        self.current_search_depth = 0
        self.searching = False
        
    def draw_board(self):
        """Draw the chess board with letter-based pieces."""
        # Draw squares
        for row in range(8):
            for col in range(8):
                color = LIGHT if (row + col) % 2 == 0 else DARK
                pygame.draw.rect(self.screen, color, (col * SQ, row * SQ, SQ, SQ))
        
        # Draw last move highlight
        if self.last_move:
            from_px = board_renderer.sq_to_px(self.last_move.from_square)
            to_px = board_renderer.sq_to_px(self.last_move.to_square)
            s = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
            s.fill(MOVE_HL)
            self.screen.blit(s, from_px)
            self.screen.blit(s, to_px)
        
        # Draw check highlight
        if self.board.board.is_check():
            king_sq = self.board.board.king(self.board.board.turn)
            if king_sq is not None:
                px = board_renderer.sq_to_px(king_sq)
                s = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
                s.fill(CHECK_HL)
                self.screen.blit(s, px)
        
        # Draw pieces as images
        for square in chess.SQUARES:
            piece = self.board.board.piece_at(square)
            if piece:
                px = board_renderer.sq_to_px(square)
                piece_key = (piece.color, piece.piece_type)
                
                # Try to use PNG image, fallback to letter if image not available
                if piece_key in self.piece_images and self.piece_images[piece_key]:
                    image = self.piece_images[piece_key]
                    image_rect = image.get_rect(center=(px[0] + SQ // 2, px[1] + SQ // 2))
                    self.screen.blit(image, image_rect)
                else:
                    # Fallback to letter
                    letter = board_renderer.PIECE_LETTERS.get((piece.piece_type, piece.color), "?")
                    text_color = (255, 255, 255) if piece.color == chess.WHITE else (0, 0, 0)
                    text = self.piece_font.render(letter, True, text_color)
                    text_rect = text.get_rect(center=(px[0] + SQ // 2, px[1] + SQ // 2))
                    self.screen.blit(text, text_rect)
        
        # Draw coordinate labels
        for i in range(8):
            # Files (a-h)
            file_label = self.label_font.render(chr(ord('a') + i), True, (100, 100, 100))
            self.screen.blit(file_label, (i * SQ + 2, BSIZ - 15))
            
            # Ranks (1-8)
            rank_label = self.label_font.render(str(8 - i), True, (100, 100, 100))
            self.screen.blit(rank_label, (BSIZ - 12, i * SQ + SQ - 15))
    
    def draw_game_info(self):
        """Draw game information overlay."""
        if self.searching:
            # Draw search depth info
            depth_text = f"Searching depth: {self.current_search_depth}"
            depth_surf = self.info_font.render(depth_text, True, (255, 255, 255))
            depth_rect = depth_surf.get_rect(center=(WINDOW_WIDTH // 2, 20))
            self.screen.blit(depth_surf, depth_rect)
        
        if self.game_over:
            # Draw game over message
            overlay = pygame.Surface((WINDOW_WIDTH, 100), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            self.screen.blit(overlay, (0, WINDOW_HEIGHT // 2 - 50))
            
            if self.winner:
                text = f"{self.winner} wins!"
            else:
                text = "Draw!"
            
            text_surf = self.info_font.render(text, True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
            self.screen.blit(text_surf, text_rect)
            
            hint_surf = self.info_font.render("Press SPACE to restart", True, (200, 200, 200))
            hint_rect = hint_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 30))
            self.screen.blit(hint_surf, hint_rect)
    
    def depth_callback(self, depth):
        """Callback for depth updates during search."""
        with self.ai_lock:
            self.current_search_depth = depth
            print(f"Depth: {depth}")
    
    def make_ai_move(self, color):
        """Make an AI move for the given color (runs in thread)."""
        engine = self.white_engine if color == WHITE else self.black_engine
        
        # Set depth callback
        engine.set_realtime_callback(self.depth_callback)
        
        # Sync engine to current board
        engine.chess_to_custom_board(self.board.board)
        
        # Get best move
        best_move = engine.get_best_move()
        
        with self.ai_lock:
            self.searching = False
            self.current_search_depth = 0
        
        if best_move is None:
            return False  # No legal moves
        
        # Convert custom move to chess move
        chess_move = engine.custom_to_chess_move(best_move)
        
        # Make the move on the board
        with self.ai_lock:
            self.board.apply_move(chess_move)
            self.last_move = chess_move
        
        return True
    
    def start_ai_move(self, color):
        """Start AI move in a separate thread."""
        with self.ai_lock:
            if self.searching:
                return  # Already searching
            self.searching = True
            self.current_search_depth = 0
        
        # Create and start thread
        self.ai_thread = threading.Thread(target=self.make_ai_move, args=(color,))
        self.ai_thread.daemon = True
        self.ai_thread.start()
    
    def check_game_over(self):
        """Check if the game is over."""
        if self.board.board.is_checkmate():
            winner = "Black" if self.board.board.turn == chess.WHITE else "White"
            self.game_over = True
            self.winner = winner
            return True
        elif self.board.board.is_stalemate():
            self.game_over = True
            self.winner = None
            return True
        return False
    
    def reset_game(self):
        """Reset the game to starting position."""
        self.board = Board()
        self.last_move = None
        self.game_over = False
        self.winner = None
        self.last_move_time = time.time()
    
    def run(self):
        """Main game loop."""
        clock = pygame.time.Clock()
        running = True
        
        self.last_move_time = time.time()
        self.ai_move_started = False
        
        while running:
            current_time = time.time()
            
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE and self.game_over:
                        self.reset_game()
                    elif event.key == pygame.K_ESCAPE:
                        running = False
            
            # AI moves (non-blocking with threading)
            if not self.game_over:
                with self.ai_lock:
                    is_searching = self.searching
                
                if not is_searching and not self.ai_move_started:
                    # Start new AI move after delay
                    if current_time - self.last_move_time >= self.move_delay:
                        current_color = WHITE if self.board.board.turn == chess.WHITE else BLACK
                        self.start_ai_move(current_color)
                        self.ai_move_started = True
                elif not is_searching and self.ai_move_started:
                    # AI move completed
                    self.ai_move_started = False
                    self.last_move_time = current_time
                    # Check for game over
                    self.check_game_over()
            
            # Draw
            self.screen.fill((0, 0, 0))
            self.draw_board()
            self.draw_game_info()
            
            pygame.display.flip()
            clock.tick(60)
        
        pygame.quit()

if __name__ == "__main__":
    gui = ChessGUI()
    gui.run()