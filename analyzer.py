"""Chess position analyzer with real-time engine evaluation."""

import pygame
import chess
import threading
import time
import argparse
from board import Board
from engine.Engine import ChessEngine
import board_renderer

# ── Colours ───────────────────────────────────────────────────────────────
# Modern ChessKit-inspired color scheme
LIGHT        = (240, 217, 181)  # Classic light square
DARK         = (181, 136,  99)  # Classic dark square
MOVE_HL      = (186, 202, 68, 180)  # Subtle green highlight for last move
SELECTED_HL  = (100, 149, 237, 140)  # Cornflower blue for selected square
CHECK_HL     = (220,  20,  60, 160)  # Deep red for check
LEGAL_DOT    = (100, 100, 100, 100)  # Gray for legal move dots
PANEL_BG     = (18,  18,  18)  # Dark background (Material UI dark theme)
TEXT_FG      = (242, 242, 242)  # Light text (Material UI)
ACCENT       = (98,  0, 238)  # Deep blue accent (Material UI primary)
DIM          = (158, 158, 158)  # Dimmed text (Material UI secondary)

SQ = 80
BSIZ = SQ * 8
PW = 320
WINDOW_WIDTH = BSIZ + PW
WINDOW_HEIGHT = BSIZ
BUTTON_HEIGHT = 40
BUTTON_MARGIN = 20

PIECE_GLYPH = {
    (chess.PAWN, chess.WHITE): "P",
    (chess.KNIGHT, chess.WHITE): "N",
    (chess.BISHOP, chess.WHITE): "B",
    (chess.ROOK, chess.WHITE): "R",
    (chess.QUEEN, chess.WHITE): "Q",
    (chess.KING, chess.WHITE): "K",
    (chess.PAWN, chess.BLACK): "p",
    (chess.KNIGHT, chess.BLACK): "n",
    (chess.BISHOP, chess.BLACK): "b",
    (chess.ROOK, chess.BLACK): "r",
    (chess.QUEEN, chess.BLACK): "q",
    (chess.KING, chess.BLACK): "k",
}


def sq_to_px(sq: int, flipped: bool = False) -> tuple[int, int]:
    f = chess.square_file(sq)
    r = chess.square_rank(sq)
    if flipped:
        f, r = 7 - f, 7 - r
    return f * SQ, (7 - r) * SQ


def px_to_sq(x: int, y: int, flipped: bool = False) -> int:
    f = x // SQ
    r = 7 - (y // SQ)
    if flipped:
        f, r = 7 - f, 7 - r
    f = max(0, min(7, f))
    r = max(0, min(7, r))
    return chess.square(f, r)


class ChessAnalyzer:
    def __init__(self, quiet=False):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Chess Position Analyzer")
        self.quiet = quiet  # Quiet mode flag
        
        # Analyzer-specific depth setting (independent of Settings.py)
        # Use higher depth for iterative deepening - will search until stopped
        self.analyzer_depth = 20  # Will search iteratively to this depth
        
        # Fonts
        self.piece_font = pygame.font.SysFont('Arial', 48, bold=True)
        self.label_font = pygame.font.SysFont('Arial', 14)
        self.ui_font = pygame.font.SysFont('Arial', 16)
        self.title_font = pygame.font.SysFont('Arial', 20, bold=True)
        
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
        self.flipped = False
        self.selected_sq = None
        self.legal_targets = []
        self.last_move = None
        
        # Engine for analysis - use custom chess engine directly
        # Use analyzer's own depth setting, independent of Settings.py
        self.engine = ChessEngine(depth=self.analyzer_depth, use_backward_search=False, search_time=1.0, realtime=True, quiet=self.quiet)
        self.engine.use_opening_book = False  # Disable opening book for analyzer
        
        # Set real-time callback
        self.engine.set_realtime_callback(self.on_better_move_found)
        
        # Analysis results
        self.best_move = None
        self.second_best_move = None
        self.third_best_move = None
        self.evaluation = 0.0
        self.win_rate = 50.0
        self.analyzing = False
        self.analysis_depth = 0
        self.last_print_time = time.time()  # Track last time we printed status in quiet mode
        self.search_start_time = 0  # Track when current search started
        self.principal_variations = []  # Store principal variations for top 3 moves
        self.pv_rects = []  # Store clickable rectangles for PV lines
        self.mouse_pos = (0, 0)  # Track mouse position for hover effects
        self.mate_in = None  # Store mate distance (e.g., "Mate in 3")
        
        # Threading for continuous analysis
        self.analysis_thread = None
        self.stop_analysis = threading.Event()
        self.board_changed = True  # Flag to trigger new analysis when board changes
        
        # Start continuous analysis
        self.start_analysis()
        
    def start_analysis(self):
        """Start continuous background analysis."""
        self.stop_analysis.clear()
        self.analyzing = True
        self.analysis_thread = threading.Thread(target=self.continuous_analysis, daemon=True)
        self.analysis_thread.start()
        
    def on_better_move_found(self, move, score):
        """Callback when engine finds a better move."""
        self.best_move = move
        self.evaluation = score
        
        # Detect mate
        self.mate_in = None
        if abs(score) > 50000:  # Mate detected
            # Extract mate distance from score
            # Score format: 100000 - ply_count for white mate, -100000 + ply_count for black mate
            if score > 0:
                # White is mating
                self.mate_in = (100000 - score + 1) // 2  # Convert plies to moves
            else:
                # Black is mating
                self.mate_in = -(100000 + score + 1) // 2  # Convert plies to moves
        
        # Get second and third best moves from top_moves
        top_moves = self.engine.get_top_moves()
        if len(top_moves) >= 2:
            self.second_best_move = top_moves[1][0]
        if len(top_moves) >= 3:
            self.third_best_move = top_moves[2][0]
        
        # Get principal variations from engine
        self.principal_variations = self.engine.get_principal_variations()
        
        # Calculate win rate from evaluation (only if not mate)
        if self.mate_in is None:
            self.win_rate = 100 / (1 + 2.71828 ** (-self.evaluation / 200))
            self.win_rate = max(0, min(100, self.win_rate))
        else:
            # Set win rate to 100% or 0% based on who is mating
            if self.mate_in > 0:
                self.win_rate = 100  # White mates
            else:
                self.win_rate = 0  # Black mates
        
        # In quiet mode, don't print anything here (handled in continuous_analysis)
    
    def continuous_analysis(self):
        """Run continuous analysis in background with iterative deepening."""
        while not self.stop_analysis.is_set():
            try:
                # Only start new analysis if board has changed
                if self.board_changed:
                    self.board_changed = False
                    self.analyze_position_iterative()
                
                # In quiet mode, print status every 5 seconds
                if self.quiet:
                    current_time = time.time()
                    if current_time - self.last_print_time >= 5.0:
                        depth = self.analysis_depth if hasattr(self, 'analysis_depth') else 0
                        elapsed = current_time - self.last_print_time
                        print(f"depth: {depth}, best_move: {self.best_move}, eval: {self.evaluation}")
                        self.last_print_time = current_time
                
                # Small delay to prevent CPU overload
                time.sleep(0.1)
            except Exception as e:
                # Always print errors in quiet mode for debugging
                print(f"Analysis error: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(1)
    
    def analyze_position_iterative(self):
        """Analyze current position with iterative deepening using move ordering cache."""
        try:
            # Clear move ordering cache when starting new analysis
            self.engine.clear_move_ordering_cache()
            
            # Sync engine to current board
            self.engine.chess_to_custom_board(self.board.board)
            
            # Search iteratively from depth 1 to max_depth
            for current_depth in range(1, self.analyzer_depth + 1):
                # Check if board changed during search
                if self.board_changed:
                    break
                
                # Update engine depth for this iteration
                self.engine.depth = current_depth
                
                # Get best move at current depth
                best_move = self.engine.search(self.board.board)
                
                # Get current analysis data
                analysis_data = self.engine.get_current_analysis()
                
                # Update analyzer state
                self.best_move = analysis_data['best_move']
                self.evaluation = analysis_data['evaluation']
                top_moves = analysis_data['top_moves']
                self.principal_variations = analysis_data['principal_variations']
                self.analysis_depth = analysis_data['depth']
                
                # Detect mate
                self.mate_in = None
                if abs(self.evaluation) > 50000:
                    if self.evaluation > 0:
                        self.mate_in = (100000 - self.evaluation + 1) // 2
                    else:
                        self.mate_in = -(100000 + self.evaluation + 1) // 2
                
                # Set second and third best moves
                if len(top_moves) >= 2:
                    self.second_best_move = top_moves[1][0]
                else:
                    self.second_best_move = None
                if len(top_moves) >= 3:
                    self.third_best_move = top_moves[2][0]
                else:
                    self.third_best_move = None
                
                # Calculate win rate
                if self.mate_in is None:
                    self.win_rate = 100 / (1 + 2.71828 ** (-self.evaluation / 200))
                    self.win_rate = max(0, min(100, self.win_rate))
                else:
                    if self.mate_in > 0:
                        self.win_rate = 100
                    else:
                        self.win_rate = 0
                
                if not self.quiet:
                    print(f"Depth {current_depth}: {self.best_move}, eval: {self.evaluation}")
                
                # Small delay between depths to allow UI updates
                time.sleep(0.05)
                
        except Exception as e:
            if not self.quiet:
                print(f"Iterative analysis error: {e}")
                import traceback
                traceback.print_exc()
    
    def analyze_position(self):
        """Analyze current position and update best moves."""
        try:
            # Track search start time for accurate elapsed time reporting
            self.search_start_time = time.time()
            
            # Create a copy of the board for analysis to prevent modifying the actual board
            board_copy = self.board.clone()
            
            # Get top moves from engine using the underlying chess.Board
            best_move = self.engine.search(board_copy.board)
            
            # Get current analysis data from engine
            analysis_data = self.engine.get_current_analysis()
            
            # Update analyzer state with engine data
            self.best_move = analysis_data['best_move']
            self.evaluation = analysis_data['evaluation']
            top_moves = analysis_data['top_moves']
            self.principal_variations = analysis_data['principal_variations']
            self.analysis_depth = analysis_data['depth']
            
            # Detect mate
            self.mate_in = None
            if abs(self.evaluation) > 50000:  # Mate detected
                # Extract mate distance from score
                # Score format: 100000 - ply_count for white mate, -100000 + ply_count for black mate
                if self.evaluation > 0:
                    # White is mating
                    self.mate_in = (100000 - self.evaluation + 1) // 2  # Convert plies to moves
                else:
                    # Black is mating
                    self.mate_in = -(100000 + self.evaluation + 1) // 2  # Convert plies to moves
            
            # If depth is still 0, use the engine's configured depth
            if self.analysis_depth == 0:
                self.analysis_depth = self.engine.depth
            
            if not self.quiet:
                print(f"Top moves: {top_moves}")
                print(f"Best move: {self.best_move}")
                print(f"Evaluation: {self.evaluation}")
                print(f"Depth: {self.analysis_depth}")
                if self.mate_in is not None:
                    print(f"Mate in: {self.mate_in}")
            
            # Set second and third best moves directly from top_moves
            if len(top_moves) >= 1:
                self.best_move = top_moves[0][0]
            if len(top_moves) >= 2:
                self.second_best_move = top_moves[1][0]
            else:
                self.second_best_move = None
            if len(top_moves) >= 3:
                self.third_best_move = top_moves[2][0]
            else:
                self.third_best_move = None
            
            # Calculate win rate from evaluation (only if not mate)
            if self.mate_in is None:
                # Simple sigmoid function: 100 / (1 + exp(-eval/100))
                self.win_rate = 100 / (1 + 2.71828 ** (-self.evaluation / 200))
                self.win_rate = max(0, min(100, self.win_rate))
            else:
                # Set win rate to 100% or 0% based on who is mating
                if self.mate_in > 0:
                    self.win_rate = 100  # White mates
                else:
                    self.win_rate = 0  # Black mates
            
            if not self.quiet:
                print(f"Win rate: {self.win_rate}")
                print(f"Second best: {self.second_best_move}")
                print(f"Third best: {self.third_best_move}")
            
        except Exception as e:
            if not self.quiet:
                print(f"Position analysis error: {e}")
                import traceback
                traceback.print_exc()
    
    def handle_click(self, pos):
        """Handle board click for piece movement and PV line clicks."""
        x, y = pos
        
        # Check if click is on PV lines in side panel
        if x >= BSIZ:
            for rect, pv_idx in self.pv_rects:
                if rect.collidepoint(pos):
                    self.play_principal_variation(pv_idx)
                    return
            return
        
        # Handle board clicks for piece movement
        sq = px_to_sq(x, y, self.flipped)
        piece = self.board.board.piece_at(sq)
        
        if self.selected_sq is None:
            # Select piece
            if piece:
                self.selected_sq = sq
                self.legal_targets = []
                for move in self.board.board.legal_moves:
                    if move.from_square == sq:
                        self.legal_targets.append(move.to_square)
        else:
            # Try to make move
            if sq in self.legal_targets:
                # Find the move
                for move in self.board.board.legal_moves:
                    if move.from_square == self.selected_sq and move.to_square == sq:
                        self.board.apply_move(move)
                        self.last_move = move
                        self.selected_sq = None
                        self.legal_targets = []
                        # Clear analysis results immediately when move is made
                        self.best_move = None
                        self.second_best_move = None
                        self.third_best_move = None
                        self.evaluation = 0.0
                        self.win_rate = 50.0
                        self.mate_in = None
                        self.principal_variations = []
                        # Trigger new analysis after move
                        self.board_changed = True
                        break
            else:
                # Select different piece
                if piece:
                    self.selected_sq = sq
                    self.legal_targets = []
                    for move in self.board.board.legal_moves:
                        if move.from_square == sq:
                            self.legal_targets.append(move.to_square)
                else:
                    self.selected_sq = None
                    self.legal_targets = []
    
    def play_principal_variation(self, pv_idx):
        """Play the principal variation line on the board."""
        if pv_idx >= len(self.principal_variations):
            return
        
        pv = self.principal_variations[pv_idx]
        if not pv:
            return
        
        # Create a temporary board to parse the UCI moves (engine returns UCI format)
        temp_board = self.board.board.copy()
        
        # Parse and play each move in the PV (UCCI format)
        for uci_move in pv:
            try:
                move = chess.Move.from_uci(uci_move)
                if move in temp_board.legal_moves:
                    temp_board.push(move)
                else:
                    break  # Stop if move is not legal
            except:
                break  # Stop if parsing fails
        
        # Update the actual board with the PV line
        # We need to clear the current board and set it to the PV position
        self.board.board = temp_board
        self.selected_sq = None
        self.legal_targets = []
        self.last_move = None
        
        # Clear analysis results immediately when PV line is played
        self.best_move = None
        self.second_best_move = None
        self.third_best_move = None
        self.evaluation = 0.0
        self.win_rate = 50.0
        self.mate_in = None
        self.principal_variations = []
        
        # Trigger new analysis after playing PV line
        self.board_changed = True
    
    def draw_win_rate_bar(self):
        """Draw win rate bar in side panel with modern styling."""
        panel_x = BSIZ + 20
        bar_y = 100
        bar_width = PW - 40
        bar_height = 24
        
        # If mate detected, show mate clock instead of win rate bar
        if self.mate_in is not None:
            # Draw mate indicator
            mate_color = (76, 175, 80) if self.mate_in > 0 else (244, 67, 54)  # Green for white mate, red for black mate
            mate_text = f"Mate in {abs(self.mate_in)}"
            if self.mate_in < 0:
                mate_text = f"Mate in {abs(self.mate_in)} for Black"
            else:
                mate_text = f"Mate in {self.mate_in} for White"
            
            mate_label = self.title_font.render(mate_text, True, mate_color)
            self.screen.blit(mate_label, (panel_x + bar_width // 2 - mate_label.get_width() // 2, bar_y))
            
            # Draw simplified bar (full for winning side)
            pygame.draw.rect(self.screen, (33, 33, 33), (panel_x, bar_y + 35, bar_width, bar_height), border_radius=4)
            if self.mate_in > 0:
                pygame.draw.rect(self.screen, (236, 239, 241), (panel_x, bar_y + 35, bar_width, bar_height), border_radius=4)
            else:
                pygame.draw.rect(self.screen, (66, 66, 66), (panel_x, bar_y + 35, bar_width, bar_height), border_radius=4)
            
            return
        
        # Background (darker for Material UI look)
        pygame.draw.rect(self.screen, (33, 33, 33), (panel_x, bar_y, bar_width, bar_height), border_radius=4)
        
        # White portion (left) - Material UI light color
        white_width = int(bar_width * (self.win_rate / 100))
        pygame.draw.rect(self.screen, (236, 239, 241), (panel_x, bar_y, white_width, bar_height), border_radius=4)
        
        # Black portion (right) - Material UI dark color
        black_width = bar_width - white_width
        if black_width > 0:
            pygame.draw.rect(self.screen, (66, 66, 66), (panel_x + white_width, bar_y, black_width, bar_height), border_radius=4)
        
        # Labels with better spacing
        white_label = self.ui_font.render(f"White: {self.win_rate:.1f}%", True, TEXT_FG)
        black_label = self.ui_font.render(f"Black: {100-self.win_rate:.1f}%", True, TEXT_FG)
        
        self.screen.blit(white_label, (panel_x, bar_y - 22))
        self.screen.blit(black_label, (panel_x + bar_width - black_label.get_width(), bar_y - 22))
        
        # Evaluation text with accent color
        eval_text = f"Eval: {self.evaluation:+.2f}"
        eval_label = self.ui_font.render(eval_text, True, ACCENT)
        self.screen.blit(eval_label, (panel_x + bar_width // 2 - eval_label.get_width() // 2, bar_y + bar_height + 12))
    
    def draw_analysis_info(self):
        """Draw analysis information in side panel with modern styling."""
        panel_x = BSIZ + 20
        y = 180
        
        # Title with better spacing
        title = self.title_font.render("Analysis", True, ACCENT)
        self.screen.blit(title, (panel_x, y))
        y += 35
        
        # Best move with Material UI green
        if self.best_move:
            try:
                best_san = self.board.board.san(self.best_move)
                best_text = self.ui_font.render(f"Best: {best_san}", True, (76, 175, 80))
                self.screen.blit(best_text, (panel_x, y))
            except:
                # Move not legal in current position, show UCI instead
                best_text = self.ui_font.render(f"Best: {self.best_move.uci()}", True, (76, 175, 80))
                self.screen.blit(best_text, (panel_x, y))
            y += 28
        
        # Second best move with Material UI amber
        if self.second_best_move:
            try:
                second_san = self.board.board.san(self.second_best_move)
                second_text = self.ui_font.render(f"2nd: {second_san}", True, (255, 193, 7))
                self.screen.blit(second_text, (panel_x, y))
            except:
                # Move not legal in current position, show UCI instead
                second_text = self.ui_font.render(f"2nd: {self.second_best_move.uci()}", True, (255, 193, 7))
                self.screen.blit(second_text, (panel_x, y))
            y += 28
        
        # Third best move with Material UI orange
        if self.third_best_move:
            try:
                third_san = self.board.board.san(self.third_best_move)
                third_text = self.ui_font.render(f"3rd: {third_san}", True, (255, 152, 0))
                self.screen.blit(third_text, (panel_x, y))
            except:
                # Move not legal in current position, show UCI instead
                third_text = self.ui_font.render(f"3rd: {self.third_best_move.uci()}", True, (255, 152, 0))
                self.screen.blit(third_text, (panel_x, y))
            y += 28
        
        # Depth with dimmed text
        depth_text = self.ui_font.render(f"Depth: {self.analysis_depth}", True, DIM)
        self.screen.blit(depth_text, (panel_x, y))
        y += 35
        
        # Status with accent color
        status = "Analyzing..." if self.analyzing else "Stopped"
        status_text = self.ui_font.render(status, True, ACCENT)
        self.screen.blit(status_text, (panel_x, y))
        
        # Instructions with better spacing (moved down further to avoid overlay)
        y += 120
        instructions = [
            "Controls:",
            "• Click to select piece",
            "• Click target to move",
            "• Press 'F' to flip board",
            "• Press 'R' to reset position",
            "• Analysis updates in real-time"
        ]
        
        for instruction in instructions:
            inst_text = self.ui_font.render(instruction, True, DIM)
            self.screen.blit(inst_text, (panel_x, y))
            y += 22
    
    def draw_principal_variations(self):
        """Draw principal variations as clickable text in side panel with hover effects."""
        panel_x = BSIZ + 20
        y = 360  # Start higher (moved up from 400)
        
        self.pv_rects = []  # Clear previous click rectangles
        
        if not self.principal_variations or len(self.principal_variations) == 0:
            return
        
        # Title
        title = self.title_font.render("Engine Lines", True, ACCENT)
        self.screen.blit(title, (panel_x, y))
        y += 35
        
        # Colors for each line
        pv_colors = [(76, 175, 80), (255, 193, 7), (255, 152, 0)]  # Green, Amber, Orange
        hover_colors = [(97, 195, 101), (255, 213, 37), (255, 167, 38)]  # Lighter hover versions
        
        # Display up to 3 principal variations
        for idx, pv in enumerate(self.principal_variations[:3]):
            if not pv:
                continue
            
            # Format the PV line as a string
            pv_str = " ".join(pv[:12]) if len(pv) > 12 else " ".join(pv)  # Limit to first 12 moves for display
            
            # Check if mouse is hovering over this line
            is_hovered = False
            if hasattr(self, 'mouse_pos'):
                temp_text = self.label_font.render(f"{idx + 1}. {pv_str}", True, pv_colors[idx])
                temp_rect = temp_text.get_rect(topleft=(panel_x, y))
                if temp_rect.collidepoint(self.mouse_pos):
                    is_hovered = True
            
            # Use hover color if mouse is over this line
            color = hover_colors[idx] if is_hovered else pv_colors[idx]
            
            # Create clickable text
            pv_text = self.label_font.render(f"{idx + 1}. {pv_str}", True, color)
            text_rect = pv_text.get_rect(topleft=(panel_x, y))
            
            # Draw background highlight on hover
            if is_hovered:
                bg_rect = text_rect.inflate(10, 4)
                pygame.draw.rect(self.screen, (50, 50, 50), bg_rect, border_radius=4)
            
            # Store rectangle for click detection
            self.pv_rects.append((text_rect, idx))
            
            # Draw text
            self.screen.blit(pv_text, (panel_x, y))
            y += 25
    
    def draw(self):
        """Main draw function."""
        self.screen.fill(PANEL_BG)
        
        # Draw board
        # Pass top 3 moves with their evaluations for arrows of different thickness
        top_moves_list = []
        if self.best_move:
            top_moves_list.append((self.best_move, self.evaluation))
        if self.second_best_move:
            top_moves_list.append((self.second_best_move, self.evaluation))
        if self.third_best_move:
            top_moves_list.append((self.third_best_move, self.evaluation))
        
        board_renderer.draw_board(
            self.screen,
            self.board.board,
            self.last_move,
            self.selected_sq,
            self.legal_targets,
            self.flipped,
            self.piece_font,
            self.label_font,
            top_moves=top_moves_list if top_moves_list else None,
            worst_moves=None,
            piece_images=self.piece_images
        )
        
        # Draw side panel
        self.draw_win_rate_bar()
        self.draw_analysis_info()
        self.draw_principal_variations()
        
        pygame.display.flip()
    
    def run(self):
        """Main game loop."""
        clock = pygame.time.Clock()
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        self.handle_click(event.pos)
                elif event.type == pygame.MOUSEMOTION:
                    self.mouse_pos = event.pos  # Track mouse position for hover effects
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_f:
                        self.flipped = not self.flipped
                    elif event.key == pygame.K_r:
                        # Reset position
                        self.board = Board()
                        self.selected_sq = None
                        self.legal_targets = []
                        self.last_move = None
                        self.board_changed = True  # Trigger analysis on reset
            
            self.draw()
            clock.tick(60)
        
        # Cleanup
        self.stop_analysis.set()
        if self.analysis_thread:
            self.analysis_thread.join(timeout=1)
        pygame.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Chess Position Analyzer')
    parser.add_argument('--quiet', action='store_true', help='Reduce console output')
    args = parser.parse_args()
    
    analyzer = ChessAnalyzer(quiet=args.quiet)
    analyzer.run()
