"""Test arrow drawing in board renderer."""

import pygame
import chess
from board import Board
from board_renderer import draw_board, draw_arrow, sq_to_px, ARROW_COLORS, ARROW_THICKNESSES

# Initialize pygame
pygame.init()
screen = pygame.display.set_mode((640, 640))
pygame.display.set_caption("Test Arrow Drawing")

# Create fonts
piece_font = pygame.font.SysFont('Arial', 48, bold=True)
label_font = pygame.font.SysFont('Arial', 14)

# Create test board
board = Board()

# Create test moves
test_moves = [
    (chess.Move.from_uci('e2e4'), 100),   # Best move (green, thickest)
    (chess.Move.from_uci('d2d4'), 50),    # Second best (amber, medium)
    (chess.Move.from_uci('g1f3'), 25)     # Third best (orange, thinnest)
]

# Draw board with arrows
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    # Draw board
    draw_board(
        screen,
        board.board,
        None,  # last_move
        None,  # selected_sq
        [],    # legal_targets
        False, # flipped
        piece_font,
        label_font,
        top_moves=test_moves,
        worst_moves=None
    )
    
    pygame.display.flip()
    pygame.time.Clock().tick(60)

pygame.quit()
print("Arrow drawing test completed!")