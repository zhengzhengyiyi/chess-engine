#include "movegen.h"
#include <algorithm>

namespace {
    inline Color other(Color c) { return c == WHITE ? BLACK : WHITE; }
}

MoveGenerator::MoveGenerator(ChessBoard& b)
    : cb(b), board(b.get_board()), turn(b.get_turn()) {}

bool MoveGenerator::is_on_board(int row, int col) const {
    return row >= 0 && row < 8 && col >= 0 && col < 8;
}

bool MoveGenerator::is_square_attacked(int row, int col, Color by_color) const {
    // Pawn attacks
    int pawn_dir = (by_color == WHITE) ? 1 : -1;
    for (int dc : {-1, 1}) {
        int pr = row + pawn_dir;
        int pc = col + dc;
        if (is_on_board(pr, pc)) {
            auto piece = board[pr][pc];
            if (piece.first == by_color && piece.second == PAWN) {
                return true;
            }
        }
    }
    
    // Knight attacks
    int knight_offsets[8][2] = {{-2,-1}, {-2,1}, {-1,-2}, {-1,2}, {1,-2}, {1,2}, {2,-1}, {2,1}};
    for (auto& offset : knight_offsets) {
        int nr = row + offset[0];
        int nc = col + offset[1];
        if (is_on_board(nr, nc)) {
            auto piece = board[nr][nc];
            if (piece.first == by_color && piece.second == KNIGHT) {
                return true;
            }
        }
    }
    
    // King attacks
    for (int dr = -1; dr <= 1; dr++) {
        for (int dc = -1; dc <= 1; dc++) {
            if (dr == 0 && dc == 0) continue;
            int kr = row + dr;
            int kc = col + dc;
            if (is_on_board(kr, kc)) {
                auto piece = board[kr][kc];
                if (piece.first == by_color && piece.second == KING) {
                    return true;
                }
            }
        }
    }
    
    // Sliding attacks (bishop/rook/queen)
    int bishop_dirs[4][2] = {{-1,-1}, {-1,1}, {1,-1}, {1,1}};
    int rook_dirs[4][2] = {{-1,0}, {1,0}, {0,-1}, {0,1}};
    
    for (auto& dir : bishop_dirs) {
        int check_r = row + dir[0];
        int check_c = col + dir[1];
        while (is_on_board(check_r, check_c)) {
            auto piece = board[check_r][check_c];
            if (piece.second != EMPTY) {
                if (piece.first == by_color && (piece.second == BISHOP || piece.second == QUEEN)) {
                    return true;
                }
                break;
            }
            check_r += dir[0];
            check_c += dir[1];
        }
    }
    
    for (auto& dir : rook_dirs) {
        int check_r = row + dir[0];
        int check_c = col + dir[1];
        while (is_on_board(check_r, check_c)) {
            auto piece = board[check_r][check_c];
            if (piece.second != EMPTY) {
                if (piece.first == by_color && (piece.second == ROOK || piece.second == QUEEN)) {
                    return true;
                }
                break;
            }
            check_r += dir[0];
            check_c += dir[1];
        }
    }
    
    return false;
}

void MoveGenerator::add_pawn_moves(std::vector<Move>& moves, int row, int col) {
    int direction = (turn == WHITE) ? -1 : 1;
    int start_row = (turn == WHITE) ? 6 : 1;
    int promotion_row = (turn == WHITE) ? 0 : 7;
    
    // Forward move
    if (is_on_board(row + direction, col) && board[row + direction][col].second == EMPTY) {
        if (row + direction == promotion_row) {
            moves.push_back(Move(row, col, row + direction, col, QUEEN));
            moves.push_back(Move(row, col, row + direction, col, ROOK));
            moves.push_back(Move(row, col, row + direction, col, BISHOP));
            moves.push_back(Move(row, col, row + direction, col, KNIGHT));
        } else {
            moves.push_back(Move(row, col, row + direction, col));
        }
        
        // Double move from start
        if (row == start_row && board[row + 2 * direction][col].second == EMPTY) {
            moves.push_back(Move(row, col, row + 2 * direction, col));
        }
    }
    
    // Captures
    for (int dc : {-1, 1}) {
        int new_col = col + dc;
        if (is_on_board(row + direction, new_col)) {
            auto target = board[row + direction][new_col];
            if (target.first != turn && target.second != EMPTY && target.second != KING) {
                if (row + direction == promotion_row) {
                    moves.push_back(Move(row, col, row + direction, new_col, QUEEN));
                    moves.push_back(Move(row, col, row + direction, new_col, ROOK));
                    moves.push_back(Move(row, col, row + direction, new_col, BISHOP));
                    moves.push_back(Move(row, col, row + direction, new_col, KNIGHT));
                } else {
                    moves.push_back(Move(row, col, row + direction, new_col));
                }
            }
        }
    }
    
    // En passant capture
    int ep_r, ep_c;
    if (cb.get_en_passant(ep_r, ep_c) && row + direction == ep_r) {
        if (col - 1 == ep_c || col + 1 == ep_c) {
            moves.push_back(Move(row, col, ep_r, ep_c));
        }
    }
}

void MoveGenerator::add_knight_moves(std::vector<Move>& moves, int row, int col) {
    int offsets[8][2] = {{-2,-1}, {-2,1}, {-1,-2}, {-1,2}, {1,-2}, {1,2}, {2,-1}, {2,1}};
    
    for (auto& offset : offsets) {
        int new_row = row + offset[0];
        int new_col = col + offset[1];
        if (is_on_board(new_row, new_col)) {
            auto target = board[new_row][new_col];
            if ((target.second == EMPTY || target.first != turn) && target.second != KING) {
                moves.push_back(Move(row, col, new_row, new_col));
            }
        }
    }
}

void MoveGenerator::add_sliding_moves(std::vector<Move>& moves, int row, int col, const int directions[8][2], int num_dirs) {
    for (int d = 0; d < num_dirs; d++) {
        int dr = directions[d][0];
        int dc = directions[d][1];
        int new_row = row + dr;
        int new_col = col + dc;
        
        while (is_on_board(new_row, new_col)) {
            auto target = board[new_row][new_col];
            if (target.second == EMPTY) {
                moves.push_back(Move(row, col, new_row, new_col));
            } else {
                if (target.first != turn && target.second != KING) {
                    moves.push_back(Move(row, col, new_row, new_col));
                }
                break;
            }
            new_row += dr;
            new_col += dc;
        }
    }
}

void MoveGenerator::add_king_moves(std::vector<Move>& moves, int row, int col) {
    for (int dr = -1; dr <= 1; dr++) {
        for (int dc = -1; dc <= 1; dc++) {
            if (dr == 0 && dc == 0) continue;
            int new_row = row + dr;
            int new_col = col + dc;
            if (is_on_board(new_row, new_col)) {
                auto target = board[new_row][new_col];
                if ((target.second == EMPTY || target.first != turn) && target.second != KING) {
                    moves.push_back(Move(row, col, new_row, new_col));
                }
            }
        }
    }
}

void MoveGenerator::add_castling_moves(std::vector<Move>& moves, int row, int col) {
    // King must be on its home square (e-file of its back rank)
    int home_row = (turn == WHITE) ? 7 : 0;
    if (row != home_row || col != 4) return;
    if (board[row][col].second != KING || board[row][col].first != turn) return;
    
    Color enemy = other(turn);
    
    // Cannot castle out of, through, or into check
    if (is_square_attacked(row, col, enemy)) return;
    
    // Kingside: f and g empty; f and g not attacked; rook on h-file
    if (cb.has_castling_right(turn, true) &&
        board[row][5].second == EMPTY && board[row][6].second == EMPTY &&
        board[row][7].second == ROOK && board[row][7].first == turn &&
        !is_square_attacked(row, 5, enemy) && !is_square_attacked(row, 6, enemy)) {
        moves.push_back(Move(row, 4, row, 6));
    }
    
    // Queenside: b, c, d empty; d and c not attacked; rook on a-file
    if (cb.has_castling_right(turn, false) &&
        board[row][1].second == EMPTY && board[row][2].second == EMPTY &&
        board[row][3].second == EMPTY &&
        board[row][0].second == ROOK && board[row][0].first == turn &&
        !is_square_attacked(row, 3, enemy) && !is_square_attacked(row, 2, enemy)) {
        moves.push_back(Move(row, 4, row, 2));
    }
}

std::vector<Move> MoveGenerator::generate_pseudo_legal_moves() {
    std::vector<Move> moves;
    
    for (int row = 0; row < 8; row++) {
        for (int col = 0; col < 8; col++) {
            auto piece = board[row][col];
            if (piece.second != EMPTY && piece.first == turn) {
                switch (piece.second) {
                    case PAWN:
                        add_pawn_moves(moves, row, col);
                        break;
                    case KNIGHT:
                        add_knight_moves(moves, row, col);
                        break;
                    case BISHOP: {
                        int directions[4][2] = {{-1,-1}, {-1,1}, {1,-1}, {1,1}};
                        add_sliding_moves(moves, row, col, directions, 4);
                        break;
                    }
                    case ROOK: {
                        int directions[4][2] = {{-1,0}, {1,0}, {0,-1}, {0,1}};
                        add_sliding_moves(moves, row, col, directions, 4);
                        break;
                    }
                    case QUEEN: {
                        int directions[8][2] = {{-1,-1}, {-1,1}, {1,-1}, {1,1}, {-1,0}, {1,0}, {0,-1}, {0,1}};
                        add_sliding_moves(moves, row, col, directions, 8);
                        break;
                    }
                    case KING:
                        add_king_moves(moves, row, col);
                        add_castling_moves(moves, row, col);
                        break;
                    case EMPTY:
                        break;
                }
            }
        }
    }
    
    return moves;
}

std::vector<Move> MoveGenerator::generate_legal_moves() {
    std::vector<Move> pseudo_moves = generate_pseudo_legal_moves();
    std::vector<Move> legal_moves;
    legal_moves.reserve(pseudo_moves.size());
    
    Color mover = turn;
    Color enemy = other(turn);
    
    for (const auto& move : pseudo_moves) {
        cb.make_move(move, true);
        
        // Locate the mover's king after the move
        int king_row = -1, king_col = -1;
        for (int r = 0; r < 8 && king_row == -1; r++) {
            for (int c = 0; c < 8; c++) {
                if (board[r][c].first == mover && board[r][c].second == KING) {
                    king_row = r;
                    king_col = c;
                    break;
                }
            }
        }
        
        bool king_safe = (king_row != -1) &&
                         !is_square_attacked(king_row, king_col, enemy);
        
        cb.unmake_move(true);
        
        if (king_safe) {
            legal_moves.push_back(move);
        }
    }
    
    return legal_moves;
}

bool MoveGenerator::is_in_check(Color color) const {
    int king_row = -1, king_col = -1;
    for (int r = 0; r < 8; r++) {
        for (int c = 0; c < 8; c++) {
            if (board[r][c].first == color && board[r][c].second == KING) {
                king_row = r;
                king_col = c;
                break;
            }
        }
        if (king_row != -1) break;
    }
    if (king_row == -1) return false;
    return is_square_attacked(king_row, king_col, other(color));
}
