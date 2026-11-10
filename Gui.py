"""Pygame GUI for chess engine with 2 AI players."""

import sys
sys.path.append('.')
import pygame
import chess
import time
import threading
import argparse
from datetime import datetime
import pyperclip
from engine.engine_selector import get_engine
from board import Board
import board_renderer

# Parse command line arguments
parser = argparse.ArgumentParser(description='Chess AI vs AI GUI')
parser.add_argument('--python', type=str, default='true',
                   help='Use Python engine (true) or C++ engine (false)')
parser.add_argument('--compile-cpp', action='store_true',
                   help='Compile C++ engine')
parser.add_argument('--play', type=str, default='both',
                   help='Which side the engine plays: white, black, or both')
parser.add_argument('--fen', type=str, default=None,
                   help='Start from a FEN string (optional)')
try:
    args = parser.parse_args()
except:
    args = argparse.Namespace(python='true', compile_cpp=False, play='both', fen=None)

# Convert string to bool
use_python = args.python.lower() in ['true', '1', 'yes', 'y']

# Handle C++ compilation if requested
if args.compile_cpp:
    from source.cpp_engine_wrapper import compile_cpp_engine
    compile_cpp_engine()
    sys.exit(0)

# Colors
LIGHT = (240, 217, 181)
DARK = (181, 136, 99)
MOVE_HL = (186, 202, 68, 180)
CHECK_HL = (220, 20, 60, 160)

# Board settings
SQ = 80
BSIZ = SQ * 8
WINDOW_WIDTH = BSIZ
WINDOW_HEIGHT = BSIZ + 60  # Extra space for button

# Button settings
BUTTON_WIDTH = 120
BUTTON_HEIGHT = 40
BUTTON_X = (WINDOW_WIDTH - BUTTON_WIDTH) // 2
BUTTON_Y = BSIZ + 10

class ChessGUI:
    def __init__(self, play_side='both'):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Chess AI vs AI")
        
        # Which side the engine plays
        self.play_side = play_side.lower()  # 'white', 'black', or 'both'
        
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
        if args.fen:
            self.board = Board(fen=args.fen)
        else:
            self.board = Board()
        self.last_move = None
        self.selected_square = None  # For human move selection
        self.selected_piece = None  # For piece selection highlight
        
        # Load depth from Settings.py
        try:
            from Settings import depth
            self.search_depth = depth
        except:
            self.search_depth = 3
        
        # Create two engines (one for each color) using engine selector
        self.white_engine = get_engine(depth=self.search_depth, use_backward_search=False, 
                                       search_time=1.0, realtime=False, quiet=True, use_python=use_python)
        self.black_engine = get_engine(depth=self.search_depth, use_backward_search=False, 
                                       search_time=1.0, realtime=False, quiet=True, use_python=use_python)
        
        # C++ engine doesn't have use_opening_book, so handle gracefully
        if hasattr(self.white_engine, 'use_opening_book'):
            self.white_engine.use_opening_book = False
        if hasattr(self.black_engine, 'use_opening_book'):
            self.black_engine.use_opening_book = False
        
        self.game_over = False
        self.winner = None
        self.move_delay = 0.5  # Seconds between moves
        self.last_move_time = 0
        self.paused = False  # Pause state
        
        # If engine plays one side and it's that side's turn, set last_move_time so it starts immediately
        current_color = chess.WHITE if self.board.board.turn == chess.WHITE else chess.BLACK
        if self.play_side != 'both':
            engine_color = self.play_side
            if (engine_color == 'white' and current_color == chess.WHITE) or \
               (engine_color == 'black' and current_color == chess.BLACK):
                self.last_move_time = 0  # Start AI move immediately
        
        # Threading for AI moves
        self.ai_thread = None
        self.ai_lock = threading.Lock()
        self.current_search_depth = 0
        self.searching = False
        
        # Button state
        self.copy_pgn_button = pygame.Rect(BUTTON_X, BUTTON_Y, BUTTON_WIDTH, BUTTON_HEIGHT)
        self.button_hovered = False
    
    def generate_pgn(self):
        """Generate PGN format for the current game."""
        try:
            from Settings import depth as settings_depth
        except:
            settings_depth = self.search_depth
        
        engine_type = "Python" if use_python else "C++"
        
        # PGN header
        date_str = datetime.now().strftime("%Y.%m.%d")
        pgn = f'[Event "Chess AI vs AI"]\n'
        pgn += f'[Site "Desktop"]\n'
        pgn += f'[Date "{date_str}"]\n'
        pgn += f'[White "AI1 ({engine_type}, depth {settings_depth})"]\n'
        pgn += f'[Black "AI2 ({engine_type}, depth {settings_depth})"]\n'
        pgn += f'[Result "*"]\n\n'
        
        # Move list - use the board's internal move history to get proper SAN notation
        move_list = []
        
        # Create a temporary board and replay the game to get proper SAN
        temp_board = chess.Board()
        
        for i, move in enumerate(self.board.board.move_stack):
            try:
                # Try to get SAN from the current board state
                temp_board.push(move)
                move_san = temp_board.san(move)
            except:
                # If move is illegal, try UCI as fallback
                try:
                    move_san = move.uci()
                except:
                    move_san = "???"
            
            if i % 2 == 0:
                move_list.append(f"{i//2 + 1}. {move_san}")
            else:
                move_list.append(move_san)
        
        # Format moves (80 characters per line)
        line = ""
        for move in move_list:
            if line:
                if len(line) + len(move) + 1 <= 80:
                    line += " " + move
                else:
                    pgn += line + "\n"
                    line = move
            else:
                line = move
        
        if line:
            pgn += line + "\n"
        
        pgn += "*\n"
        return pgn
    
    def handle_mouse_click(self, mouse_pos):
        """Handle mouse clicks for human moves when engine plays only one side."""
        # Convert mouse position to board square
        if mouse_pos[1] < BSIZ:  # Click is on the board
            col = mouse_pos[0] // SQ
            row = mouse_pos[1] // SQ
            square = chess.square(col, 7 - row)
            
            # Check if it's the human's turn
            current_color = chess.WHITE if self.board.board.turn == chess.WHITE else chess.BLACK
            human_color = chess.WHITE if self.play_side == 'black' else chess.BLACK
            
            if current_color == human_color:
                piece = self.board.board.piece_at(square)
                
                if self.selected_square is None:
                    # Select a piece
                    if piece and piece.color == human_color:
                        self.selected_square = square
                        self.selected_piece = piece
                else:
                    # Try to make a move
                    legal_moves = list(self.board.board.legal_moves)
                    
                    # Check if this is a valid move from selected square
                    for move in legal_moves:
                        if move.from_square == self.selected_square and move.to_square == square:
                            try:
                                self.board.apply_move(move)
                                self.last_move = move
                                self.last_move_time = time.time()
                                self.check_game_over()
                                self.selected_square = None
                                self.selected_piece = None
                                break
                            except:
                                pass  # Invalid move, try next
                    
                    # If clicked on own piece, change selection
                    if piece and piece.color == human_color:
                        self.selected_square = square
                        self.selected_piece = piece
                    else:
                        # Deselect
                        self.selected_square = None
                        self.selected_piece = None
    
    def copy_pgn_to_clipboard(self):
        """Copy PGN to clipboard."""
        try:
            pgn = self.generate_pgn()
            pyperclip.copy(pgn)
            print("PGN copied to clipboard!")
        except Exception as e:
            print(f"Failed to copy PGN: {e}")
            print("PGN content:")
            print(self.generate_pgn())
        
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
        
        # Draw selected piece highlight
        if self.selected_square is not None:
            px = board_renderer.sq_to_px(self.selected_square)
            s = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
            s.fill((255, 255, 0, 150))  # Yellow highlight for selected piece
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
        
        if self.paused:
            # Draw pause indicator
            pause_text = "PAUSED (Press SPACE to resume)"
            pause_surf = self.info_font.render(pause_text, True, (255, 100, 100))
            pause_rect = pause_surf.get_rect(center=(WINDOW_WIDTH // 2, 20))
            self.screen.blit(pause_surf, pause_rect)
        
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
    
    def draw_button(self):
        """Draw the Copy PGN button."""
        button_color = (100, 100, 200) if self.button_hovered else (70, 70, 150)
        pygame.draw.rect(self.screen, button_color, self.copy_pgn_button, border_radius=5)
        pygame.draw.rect(self.screen, (150, 150, 250), self.copy_pgn_button, 2, border_radius=5)
        
        button_text = self.info_font.render("Copy PGN", True, (255, 255, 255))
        text_rect = button_text.get_rect(center=self.copy_pgn_button.center)
        self.screen.blit(button_text, text_rect)
    
    def depth_callback(self, move, score):
        """Callback for depth updates during search."""
        with self.ai_lock:
            # Python engine passes (move, score), we ignore for now
            self.current_search_depth = self.white_engine.depth if hasattr(self.white_engine, 'depth') else 3
            print(f"Search update: move={move}, score={score}")
    
    def make_ai_move(self, color):
        """Make an AI move for the given color (runs in thread)."""
        engine = self.white_engine if color == chess.WHITE else self.black_engine
        
        # Set depth callback if engine supports it
        if hasattr(engine, 'set_realtime_callback'):
            engine.set_realtime_callback(self.depth_callback)
        
        # Sync engine to current board
        engine.chess_to_custom_board(self.board.board)
        
        # Search for best move
        best_move = engine.search(self.board.board)
        
        with self.ai_lock:
            self.searching = False
            self.current_search_depth = 0
        
        if best_move is None:
            print(f"No best move found for {color}")
            return False  # No legal moves
        
        # search() now returns chess.Move directly for both engines
        chess_move = best_move
        
        print(f"AI move for {color}: {chess_move}")
        
        # Double-check that it's still the correct turn before applying move
        current_color = chess.WHITE if self.board.board.turn == chess.WHITE else chess.BLACK
        if color != current_color:
            print(f"Skipping move - turn changed from {color} to {current_color}")
            return False
        
        # Make the move on the board
        with self.ai_lock:
            self.board.apply_move(chess_move)
            self.last_move = chess_move
            print(f"Move applied. New turn: {'White' if self.board.board.turn == chess.WHITE else 'Black'}")
        
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
        """Reset the game to starting position or original FEN."""
        if args.fen:
            self.board = Board(fen=args.fen)
        else:
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
                    if event.key == pygame.K_SPACE:
                        if self.game_over:
                            self.reset_game()
                        else:
                            # Toggle pause
                            self.paused = not self.paused
                    elif event.key == pygame.K_ESCAPE:
                        running = False
                elif event.type == pygame.MOUSEMOTION:
                    mouse_pos = pygame.mouse.get_pos()
                    self.button_hovered = self.copy_pgn_button.collidepoint(mouse_pos)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        mouse_pos = pygame.mouse.get_pos()
                        if self.copy_pgn_button.collidepoint(mouse_pos):
                            self.copy_pgn_to_clipboard()
                        elif self.play_side != 'both':
                            # Handle human move if engine only plays one side
                            self.handle_mouse_click(mouse_pos)
            
            # AI moves (non-blocking with threading)
            if not self.game_over and not self.paused:
                with self.ai_lock:
                    is_searching = self.searching
                
                if not is_searching and not self.ai_move_started:
                    # Start new AI move after delay
                    if current_time - self.last_move_time >= self.move_delay:
                        current_color = chess.WHITE if self.board.board.turn == chess.WHITE else chess.BLACK
                        
                        # Only make AI move if this side should be played by engine
                        should_play = (
                            (self.play_side == 'both') or
                            (self.play_side == 'white' and current_color == chess.WHITE) or
                            (self.play_side == 'black' and current_color == chess.BLACK)
                        )
                        
                        if should_play:
                            print(f"Starting AI move for {current_color}")
                            self.start_ai_move(current_color)
                            self.ai_move_started = True
                elif not is_searching and self.ai_move_started:
                    # AI move completed
                    self.ai_move_started = False
                    self.last_move_time = current_time
                    # Check for game over
                    self.check_game_over()
            elif self.paused:
                # When paused, allow current move to finish but don't start new ones
                with self.ai_lock:
                    is_searching = self.searching
                
                if not is_searching and self.ai_move_started:
                    # Current move finished, stop starting new ones
                    self.ai_move_started = False
            
            # Draw
            self.screen.fill((0, 0, 0))
            self.draw_board()
            self.draw_game_info()
            self.draw_button()
            
            pygame.display.flip()
            clock.tick(60)
        
        pygame.quit()

if __name__ == "__main__":
    gui = ChessGUI(play_side=args.play)
    gui.run()