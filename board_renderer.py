"""Board renderer for chess analyzer with letter-based pieces."""

import chess
import pygame

# Colors
LIGHT = (240, 217, 181)
DARK = (181, 136, 99)
MOVE_HL = (186, 202, 68, 180)
SELECTED_HL = (100, 149, 237, 140)
CHECK_HL = (220, 20, 60, 160)
LEGAL_DOT = (100, 100, 100, 100)

# Arrow colors for top moves (best, second best, third best)
ARROW_COLORS = [
    (76, 175, 80),    # Green for best move
    (255, 193, 7),    # Amber for second best
    (255, 152, 0)     # Orange for third best
]

# Arrow thicknesses (thickest to thinnest)
ARROW_THICKNESSES = [8, 5, 3]

# Piece letters for display
PIECE_LETTERS = {
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
    """Convert chess square to pixel coordinates."""
    f = chess.square_file(sq)
    r = chess.square_rank(sq)
    if flipped:
        f, r = 7 - f, 7 - r
    return f * 80, (7 - r) * 80

def draw_arrow(screen, from_sq, to_sq, color, thickness, flipped=False):
    """Draw an arrow from one square to another."""
    SQ = 80
    from_px = sq_to_px(from_sq, flipped)
    to_px = sq_to_px(to_sq, flipped)
    
    # Calculate center points
    from_center = (from_px[0] + SQ // 2, from_px[1] + SQ // 2)
    to_center = (to_px[0] + SQ // 2, to_px[1] + SQ // 2)
    
    # Draw line
    pygame.draw.line(screen, color, from_center, to_center, thickness)
    
    # Draw arrowhead
    arrow_size = thickness + 4
    dx = to_center[0] - from_center[0]
    dy = to_center[1] - from_center[1]
    length = (dx ** 2 + dy ** 2) ** 0.5
    
    if length > 0:
        # Normalize direction
        dx /= length
        dy /= length
        
        # Calculate arrowhead points
        arrow_point = to_center
        left_wing = (to_center[0] - dx * arrow_size + dy * arrow_size * 0.5,
                     to_center[1] - dy * arrow_size - dx * arrow_size * 0.5)
        right_wing = (to_center[0] - dx * arrow_size - dy * arrow_size * 0.5,
                      to_center[1] - dy * arrow_size + dx * arrow_size * 0.5)
        
        # Draw arrowhead
        pygame.draw.polygon(screen, color, [arrow_point, left_wing, right_wing])

def draw_board(screen, board, last_move, selected_sq, legal_targets, flipped, piece_font, label_font, top_moves=None, worst_moves=None, piece_images=None):
    """Draw the chess board with letter-based pieces or PNG images."""
    SQ = 80
    BSIZ = SQ * 8
    
    # Draw squares
    for row in range(8):
        for col in range(8):
            color = LIGHT if (row + col) % 2 == 0 else DARK
            pygame.draw.rect(screen, color, (col * SQ, row * SQ, SQ, SQ))
    
    # Draw last move highlight
    if last_move:
        from_px = sq_to_px(last_move.from_square, flipped)
        to_px = sq_to_px(last_move.to_square, flipped)
        s = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
        s.fill(MOVE_HL)
        screen.blit(s, from_px)
        screen.blit(s, to_px)
    
    # Draw arrows for top moves (best, second best, third best)
    if top_moves:
        for i, (move, score) in enumerate(top_moves[:3]):  # Only draw top 3 moves
            if i < len(ARROW_COLORS) and i < len(ARROW_THICKNESSES):
                color = ARROW_COLORS[i]
                thickness = ARROW_THICKNESSES[i]
                draw_arrow(screen, move.from_square, move.to_square, color, thickness, flipped)
    
    # Draw selected square highlight
    if selected_sq is not None:
        px = sq_to_px(selected_sq, flipped)
        s = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
        s.fill(SELECTED_HL)
        screen.blit(s, px)
    
    # Draw legal move dots
    for target in legal_targets:
        px = sq_to_px(target, flipped)
        center = (px[0] + SQ // 2, px[1] + SQ // 2)
        pygame.draw.circle(screen, LEGAL_DOT[:3], center, 8)
    
    # Draw check highlight
    if board.is_check():
        king_sq = board.king(board.turn)
        if king_sq is not None:
            px = sq_to_px(king_sq, flipped)
            s = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
            s.fill(CHECK_HL)
            screen.blit(s, px)
    
    # Draw pieces as images or letters
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            px = sq_to_px(square, flipped)
            piece_key = (piece.color, piece.piece_type)
            
            # Try to use PNG image if available
            if piece_images and piece_key in piece_images and piece_images[piece_key]:
                image = piece_images[piece_key]
                image_rect = image.get_rect(center=(px[0] + SQ // 2, px[1] + SQ // 2))
                screen.blit(image, image_rect)
            else:
                # Fallback to letter
                letter_key = (piece.piece_type, piece.color)
                letter = PIECE_LETTERS.get(letter_key, "?")
                
                # Choose color for letter
                text_color = (255, 255, 255) if piece.color == chess.WHITE else (0, 0, 0)
                
                text = piece_font.render(letter, True, text_color)
                text_rect = text.get_rect(center=(px[0] + SQ // 2, px[1] + SQ // 2))
                screen.blit(text, text_rect)
    
    # Draw coordinate labels
    for i in range(8):
        # Files (a-h)
        file_label = label_font.render(chr(ord('a') + i), True, (100, 100, 100))
        if flipped:
            screen.blit(file_label, (i * SQ + SQ - 10, BSIZ - 15))
        else:
            screen.blit(file_label, (i * SQ + 2, BSIZ - 15))
        
        # Ranks (1-8)
        rank_label = label_font.render(str(8 - i), True, (100, 100, 100))
        if flipped:
            screen.blit(rank_label, (2, i * SQ + 2))
        else:
            screen.blit(rank_label, (BSIZ - 12, i * SQ + SQ - 15))