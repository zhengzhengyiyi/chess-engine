#include "chess_engine.h"
#include <iostream>
#include <sstream>
#include <iomanip>
#include <cmath>
#include <cstring>
#include <algorithm>

// Piece values
const int PIECE_VALUES[] = {
    0,      // EMPTY
    100,    // PAWN
    320,    // KNIGHT
    330,    // BISHOP
    500,    // ROOK
    900,    // QUEEN
    20000   // KING
};

// Material values cache
std::unordered_map<std::string, int> material_cache;
size_t material_cache_size = 0;
const size_t MAX_MATERIAL_CACHE = 100000;

std::string Move::to_string() const {
    std::string files = "abcdefgh";
    std::string ranks = "87654321";
    std::string prom = "";
    
    if (promotion != EMPTY) {
        switch (promotion) {
            case QUEEN: prom = "q"; break;
            case ROOK: prom = "r"; break;
            case BISHOP: prom = "b"; break;
            case KNIGHT: prom = "n"; break;
            default: prom = ""; break;
        }
    }
    
    return files.substr(from_col, 1) + ranks.substr(from_row, 1) + files.substr(to_col, 1) + ranks.substr(to_row, 1) + prom;
}

ChessEngine::ChessEngine(int depth, bool use_backward_search, double search_time, 
                       bool realtime, bool quiet)
    : depth(depth), use_backward_search(use_backward_search), search_time(search_time),
      realtime(realtime), quiet(quiet), use_opening_book(false) {
    
    // Initialize analyzer compatibility
    current_search_depth = 0;
    max_search_depth = 0;
    
    // Initialize transposition table with memory optimization
    tt_size = 1000000;
    transposition_table.resize(tt_size);
    
    // Initialize board
    board.resize(8, std::vector<std::pair<Color, PieceType>>(8, {WHITE, EMPTY}));
    
    // Initialize castling rights
    castling_rights[WHITE] = {true, true};
    castling_rights[BLACK] = {true, true};
    
    // Initialize en passant
    en_passant_square = nullptr;
    
    // Initialize turn
    turn = WHITE;
    
    // Initialize performance settings
    max_cache_size = 100000;
    enable_aggressive_caching = true;
    
    // Initialize random number generator
    rng.seed(12345);
    
    // Initialize Zobrist hashing
    init_zobrist();
    
    // Reset board to starting position
    reset_board();
}

void ChessEngine::init_zobrist() {
    std::uniform_int_distribution<uint64_t> dist(0, UINT64_MAX);
    
    // Piece keys
    piece_keys.resize(2);
    for (int color = 0; color < 2; color++) {
        piece_keys[color].resize(7);
        for (int piece = 0; piece < 7; piece++) {
            piece_keys[color][piece].resize(64);
            for (int square = 0; square < 64; square++) {
                piece_keys[color][piece][square] = dist(rng);
            }
        }
    }
    
    // Turn key
    turn_key = dist(rng);
    
    // Castling keys
    castling_keys.resize(4);
    for (int i = 0; i < 4; i++) {
        castling_keys[i] = dist(rng);
    }
    
    // En passant keys
    enpassant_keys.resize(8);
    for (int i = 0; i < 8; i++) {
        enpassant_keys[i] = dist(rng);
    }
}

uint64_t ChessEngine::compute_hash() {
    uint64_t hash = 0;
    
    // XOR in pieces
    for (int row = 0; row < 8; row++) {
        for (int col = 0; col < 8; col++) {
            auto piece = board[row][col];
            if (piece.second != EMPTY) {
                int square = row * 8 + col;
                hash ^= piece_keys[piece.first][piece.second][square];
            }
        }
    }
    
    // XOR in turn
    if (turn == BLACK) {
        hash ^= turn_key;
    }
    
    // XOR in castling rights
    if (castling_rights[WHITE].kingside) hash ^= castling_keys[0];
    if (castling_rights[WHITE].queenside) hash ^= castling_keys[1];
    if (castling_rights[BLACK].kingside) hash ^= castling_keys[2];
    if (castling_rights[BLACK].queenside) hash ^= castling_keys[3];
    
    // XOR in en passant
    if (en_passant_square) {
        hash ^= enpassant_keys[en_passant_square->second];
    }
    
    return hash;
}

void ChessEngine::reset_board() {
    // Clear board
    for (int row = 0; row < 8; row++) {
        for (int col = 0; col < 8; col++) {
            board[row][col] = {WHITE, EMPTY};
        }
    }
    
    // Set up starting position
    // Black pieces
    board[0][0] = {BLACK, ROOK};
    board[0][1] = {BLACK, KNIGHT};
    board[0][2] = {BLACK, BISHOP};
    board[0][3] = {BLACK, QUEEN};
    board[0][4] = {BLACK, KING};
    board[0][5] = {BLACK, BISHOP};
    board[0][6] = {BLACK, KNIGHT};
    board[0][7] = {BLACK, ROOK};
    for (int col = 0; col < 8; col++) {
        board[1][col] = {BLACK, PAWN};
    }
    
    // White pieces
    board[7][0] = {WHITE, ROOK};
    board[7][1] = {WHITE, KNIGHT};
    board[7][2] = {WHITE, BISHOP};
    board[7][3] = {WHITE, QUEEN};
    board[7][4] = {WHITE, KING};
    board[7][5] = {WHITE, BISHOP};
    board[7][6] = {WHITE, KNIGHT};
    board[7][7] = {WHITE, ROOK};
    for (int col = 0; col < 8; col++) {
        board[6][col] = {WHITE, PAWN};
    }
    
    // Reset turn
    turn = WHITE;
    
    // Reset castling rights
    castling_rights[WHITE] = {true, true};
    castling_rights[BLACK] = {true, true};
    
    // Reset en passant
    en_passant_square = nullptr;
    
    // Clear move ordering cache
    clear_move_ordering_cache();
    
    // Update hash
    zobrist_hash = compute_hash();
}

void ChessEngine::clear_move_ordering_cache() {
    move_ordering_cache.clear();
}

int ChessEngine::evaluate_material() {
    // Create board key for caching
    std::string board_key;
    for (int row = 0; row < 8; row++) {
        for (int col = 0; col < 8; col++) {
            auto piece = board[row][col];
            board_key += std::to_string(piece.first) + "," + std::to_string(piece.second) + ";";
        }
    }
    board_key += std::to_string(turn);
    
    // Check cache
    auto it = material_cache.find(board_key);
    if (it != material_cache.end()) {
        return it->second;
    }
    
    // Compute evaluation
    int white_score = 0;
    int black_score = 0;
    
    // Center control squares (row, col pairs)
    int center_squares[4][2] = {{3, 3}, {3, 4}, {4, 3}, {4, 4}};
    
    for (int row = 0; row < 8; row++) {
        for (int col = 0; col < 8; col++) {
            auto piece = board[row][col];
            if (piece.second != EMPTY) {
                int value = PIECE_VALUES[piece.second];
                int square = row * 8 + col;
                
                // Center control bonus
                for (int i = 0; i < 4; i++) {
                    if (row == center_squares[i][0] && col == center_squares[i][1]) {
                        value += 5;
                    }
                }
                
                // Knight/Bishop center bonus
                if ((piece.second == KNIGHT || piece.second == BISHOP)) {
                    for (int i = 0; i < 4; i++) {
                        if (row == center_squares[i][0] && col == center_squares[i][1]) {
                            value += 10;
                        }
                    }
                }
                
                // Pawn advancement bonus
                if (piece.second == PAWN) {
                    if (piece.first == WHITE && row < 4) {
                        value += 5;
                    } else if (piece.first == BLACK && row > 3) {
                        value += 5;
                    }
                }
                
                if (piece.first == WHITE) {
                    white_score += value;
                } else {
                    black_score += value;
                }
            }
        }
    }
    
    int score = white_score - black_score;
    
    // Cache with size management
    if (enable_aggressive_caching && material_cache_size >= max_cache_size) {
        material_cache.clear();
        material_cache_size = 0;
    }
    
    material_cache[board_key] = score;
    material_cache_size++;
    
    return score;
}

int ChessEngine::minimax(int ply, int alpha, int beta, bool is_maximizing, int ply_count) {
    // Check transposition table
    uint64_t hash = compute_hash();
    size_t index = hash % tt_size;
    TTEntry& entry = transposition_table[index];
    
    if (entry.hash == hash && entry.depth >= ply) {
        return entry.score;
    }
    
    if (ply == 0) {
        return quiescence_search(alpha, beta, ply_count);
    }
    
    if (is_checkmate()) {
        // Return score based on distance to checkmate
        // Shorter checkmates are better: closer to root = higher score
        int mate_depth = ply_count;
        if (turn == WHITE) {
            // Black checkmated White - Black wins
            return -20000 + mate_depth;
        } else {
            // White checkmated Black - White wins
            return 20000 - mate_depth;
        }
    }
    
    if (is_stalemate()) {
        return 0;
    }
    
    // Generate legal moves
    std::vector<Move> legal_moves = generate_legal_moves();
    
    if (legal_moves.empty()) {
        return 0;
    }
    
    // Order moves for better pruning
    if (ply > 2) {
        legal_moves = order_moves(legal_moves);
    }
    
    if (is_maximizing) {
        int max_eval = std::numeric_limits<int>::min();
        Move best_move = legal_moves[0];
        
        for (const auto& move : legal_moves) {
            make_move(move, true);
            int eval_score = minimax(ply - 1, alpha, beta, false, ply_count + 1);
            unmake_move(true);
            
            if (eval_score > max_eval) {
                max_eval = eval_score;
                best_move = move;
            }
            
            alpha = std::max(alpha, eval_score);
            if (beta <= alpha) {
                break;
            }
        }
        
        // Store in transposition table
        uint8_t flag = (max_eval > alpha && max_eval < beta) ? 0 : (max_eval >= beta ? 1 : 2);
        entry.hash = hash;
        entry.depth = ply;
        entry.score = max_eval;
        entry.flag = flag;
        
        return max_eval;
    } else {
        int min_eval = std::numeric_limits<int>::max();
        Move best_move = legal_moves[0];
        
        for (const auto& move : legal_moves) {
            make_move(move, true);
            int eval_score = minimax(ply - 1, alpha, beta, true, ply_count + 1);
            unmake_move(true);
            
            if (eval_score < min_eval) {
                min_eval = eval_score;
                best_move = move;
            }
            
            beta = std::min(beta, eval_score);
            if (beta <= alpha) {
                break;
            }
        }
        
        // Store in transposition table
        uint8_t flag = (min_eval > alpha && min_eval < beta) ? 0 : (min_eval >= beta ? 1 : 2);
        entry.hash = hash;
        entry.depth = ply;
        entry.score = min_eval;
        entry.flag = flag;
        
        return min_eval;
    }
}

int ChessEngine::quiescence_search(int alpha, int beta, int ply_count) {
    int stand_pat = evaluate_material();
    
    if (ply_count > 10) {
        return stand_pat;
    }
    
    if (turn == WHITE) {
        if (stand_pat >= beta) {
            return beta;
        }
        if (stand_pat > alpha) {
            alpha = stand_pat;
        }
    } else {
        if (stand_pat <= alpha) {
            return alpha;
        }
        if (stand_pat < beta) {
            beta = stand_pat;
        }
    }
    
    // Generate capture moves only
    std::vector<Move> legal_moves = generate_legal_moves();
    std::vector<Move> capture_moves;
    
    for (const auto& move : legal_moves) {
        if (board[move.to_row][move.to_col].second != EMPTY) {
            capture_moves.push_back(move);
        }
    }
    
    for (const auto& move : capture_moves) {
        make_move(move, true);
        int score = quiescence_search(alpha, beta, ply_count + 1);
        unmake_move(true);
        
        if (turn == WHITE) {
            if (score >= beta) {
                return beta;
            }
            if (score > alpha) {
                alpha = score;
            }
        } else {
            if (score <= alpha) {
                return alpha;
            }
            if (score < beta) {
                beta = score;
            }
        }
    }
    
    return (turn == WHITE) ? alpha : beta;
}

std::vector<Move> ChessEngine::order_moves(const std::vector<Move>& moves) {
    std::vector<std::pair<Move, int>> move_order;
    
    for (const auto& move : moves) {
        int score = 0;
        
        // Check cache
        std::string move_key = move.to_string();
        auto it = move_ordering_cache.find(move_key);
        if (it != move_ordering_cache.end()) {
            score = it->second;
        } else {
            // MVV-LVA (Most Valuable Victim - Least Valuable Attacker)
            if (board[move.to_row][move.to_col].second != EMPTY) {
                auto victim = board[move.to_row][move.to_col];
                auto attacker = board[move.from_row][move.from_col];
                if (attacker.second != EMPTY) {
                    score = PIECE_VALUES[victim.second] * 10 - PIECE_VALUES[attacker.second];
                }
            }
            
            // Promotion bonus
            if (move.promotion != EMPTY) {
                score += PIECE_VALUES[move.promotion] * 5;
            }
            
            // Checkmate bonus
            make_move(move, true);
            if (is_checkmate()) {
                score += 10000;
            }
            unmake_move(true);
            
            // Repetition penalties
            if (!move_stack.empty()) {
                const MoveStackEntry& last_entry = move_stack.back();
                const Move& last_move = last_entry.move;
                
                // Penalty for undoing previous move
                if (move.from_row == last_move.to_row && move.from_col == last_move.to_col &&
                    move.to_row == last_move.from_row && move.to_col == last_move.from_col) {
                    score -= 100;
                }
                
                // Penalty for moving same piece twice
                if (move.from_row == last_move.to_row && move.from_col == last_move.to_col) {
                    score -= 75;
                }
            }
            
            // Penalty for recent repetitions (check last 6 moves)
            for (size_t i = 0; i < std::min(size_t(6), move_stack.size()); i++) {
                const MoveStackEntry& entry = move_stack[move_stack.size() - 1 - i];
                if (move.from_row == entry.move.from_row && move.from_col == entry.move.from_col &&
                    move.to_row == entry.move.to_row && move.to_col == entry.move.to_col) {
                    score -= 150;
                    break;
                }
            }
        }
        
        move_order.push_back({move, score});
    }
    
    // Sort by score (descending)
    std::sort(move_order.begin(), move_order.end(), 
              [](const auto& a, const auto& b) { return a.second > b.second; });
    
    std::vector<Move> result;
    for (const auto& pair : move_order) {
        result.push_back(pair.first);
    }
    
    return result;
}

std::vector<Move> ChessEngine::rank_moves() {
    std::vector<Move> legal_moves = generate_legal_moves();
    
    if (legal_moves.empty()) {
        return {};
    }
    
    // Order moves
    std::vector<Move> ordered_moves = order_moves(legal_moves);
    
    std::vector<std::pair<Move, int>> move_scores;
    int plies = depth * 2;
    bool is_white_turn = (turn == WHITE);
    
    for (const auto& move : ordered_moves) {
        make_move(move, true);
        int score = minimax(plies - 1, std::numeric_limits<int>::min(), 
                          std::numeric_limits<int>::max(), !is_white_turn, 1);
        unmake_move(true);
        move_scores.push_back({move, score});
        
        // Cache score
        move_ordering_cache[move.to_string()] = score;
    }
    
    // Sort by score
    if (is_white_turn) {
        std::sort(move_scores.begin(), move_scores.end(),
                  [](const auto& a, const auto& b) { return a.second > b.second; });
    } else {
        std::sort(move_scores.begin(), move_scores.end(),
                  [](const auto& a, const auto& b) { return a.second < b.second; });
    }
    
    std::vector<Move> result;
    for (const auto& pair : move_scores) {
        result.push_back(pair.first);
    }
    
    return result;
}

Move ChessEngine::get_best_move() {
    std::vector<Move> ranked_moves = rank_moves();
    if (!ranked_moves.empty()) {
        return ranked_moves[0];
    }
    return Move(0, 0, 0, 0);
}

Move ChessEngine::search() {
    // Simplified search to avoid crashes
    std::vector<Move> legal_moves = generate_legal_moves();
    
    if (legal_moves.empty()) {
        return Move(0, 0, 0, 0);
    }
    
    // Use rank_moves which is more stable
    std::vector<Move> ranked_moves = rank_moves();
    
    if (!ranked_moves.empty()) {
        // Cache the result
        top_moves_cache.clear();
        top_moves_cache.push_back({ranked_moves[0], 0});
        current_search_depth = depth;
        return ranked_moves[0];
    }
    
    return Move(0, 0, 0, 0);
}

// Move generation helpers
bool ChessEngine::is_on_board(int row, int col) {
    return row >= 0 && row < 8 && col >= 0 && col < 8;
}

bool ChessEngine::is_square_attacked(int row, int col, Color by_color) {
    // Check if square is attacked by any piece of by_color
    for (int r = 0; r < 8; r++) {
        for (int c = 0; c < 8; c++) {
            auto piece = board[r][c];
            if (piece.first == by_color && piece.second != EMPTY) {
                // Check if this piece can attack the target square
                // Simplified: check basic piece movements
                int dr = row - r;
                int dc = col - c;
                
                switch (piece.second) {
                    case PAWN:
                        if (by_color == WHITE && dr == -1 && abs(dc) == 1) return true;
                        if (by_color == BLACK && dr == 1 && abs(dc) == 1) return true;
                        break;
                    case KNIGHT:
                        if ((abs(dr) == 2 && abs(dc) == 1) || (abs(dr) == 1 && abs(dc) == 2)) return true;
                        break;
                    case BISHOP:
                        if (abs(dr) == abs(dc) && abs(dr) > 0) {
                            // Check path is clear
                            int step_r = dr > 0 ? 1 : -1;
                            int step_c = dc > 0 ? 1 : -1;
                            int check_r = r + step_r, check_c = c + step_c;
                            while (check_r != row || check_c != col) {
                                if (board[check_r][check_c].second != EMPTY) return false;
                                check_r += step_r;
                                check_c += step_c;
                            }
                            return true;
                        }
                        break;
                    case ROOK:
                        if ((dr == 0 || dc == 0) && (abs(dr) > 0 || abs(dc) > 0)) {
                            // Check path is clear
                            int step_r = dr > 0 ? 1 : (dr < 0 ? -1 : 0);
                            int step_c = dc > 0 ? 1 : (dc < 0 ? -1 : 0);
                            int check_r = r + step_r, check_c = c + step_c;
                            while (check_r != row || check_c != col) {
                                if (board[check_r][check_c].second != EMPTY) return false;
                                check_r += step_r;
                                check_c += step_c;
                            }
                            return true;
                        }
                        break;
                    case QUEEN:
                        if ((abs(dr) == abs(dc) || dr == 0 || dc == 0) && (abs(dr) > 0 || abs(dc) > 0)) {
                            // Check path is clear
                            int step_r = dr > 0 ? 1 : (dr < 0 ? -1 : 0);
                            int step_c = dc > 0 ? 1 : (dc < 0 ? -1 : 0);
                            int check_r = r + step_r, check_c = c + step_c;
                            while (check_r != row || check_c != col) {
                                if (board[check_r][check_c].second != EMPTY) return false;
                                check_r += step_r;
                                check_c += step_c;
                            }
                            return true;
                        }
                        break;
                    case KING:
                        if (abs(dr) <= 1 && abs(dc) <= 1 && (abs(dr) > 0 || abs(dc) > 0)) return true;
                        break;
                    case EMPTY:
                        break;
                }
            }
        }
    }
    return false;
}

void ChessEngine::add_pawn_moves(std::vector<Move>& moves, int row, int col) {
    int direction = (turn == WHITE) ? -1 : 1;
    int start_row = (turn == WHITE) ? 6 : 1;
    int promotion_row = (turn == WHITE) ? 0 : 7;
    
    // Forward move
    if (is_on_board(row + direction, col) && board[row + direction][col].second == EMPTY) {
        if (row + direction == promotion_row) {
            // Promotion
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
            if (target.second != EMPTY && target.first != turn) {
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
}

void ChessEngine::add_knight_moves(std::vector<Move>& moves, int row, int col) {
    int offsets[8][2] = {{-2,-1}, {-2,1}, {-1,-2}, {-1,2}, {1,-2}, {1,2}, {2,-1}, {2,1}};
    
    for (auto& offset : offsets) {
        int new_row = row + offset[0];
        int new_col = col + offset[1];
        if (is_on_board(new_row, new_col)) {
            auto target = board[new_row][new_col];
            if (target.second == EMPTY || target.first != turn) {
                moves.push_back(Move(row, col, new_row, new_col));
            }
        }
    }
}

void ChessEngine::add_sliding_moves(std::vector<Move>& moves, int row, int col, const int directions[8][2], int num_dirs) {
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
                if (target.first != turn) {
                    moves.push_back(Move(row, col, new_row, new_col));
                }
                break;
            }
            new_row += dr;
            new_col += dc;
        }
    }
}

void ChessEngine::add_king_moves(std::vector<Move>& moves, int row, int col) {
    for (int dr = -1; dr <= 1; dr++) {
        for (int dc = -1; dc <= 1; dc++) {
            if (dr == 0 && dc == 0) continue;
            int new_row = row + dr;
            int new_col = col + dc;
            if (is_on_board(new_row, new_col)) {
                auto target = board[new_row][new_col];
                if (target.second == EMPTY || target.first != turn) {
                    moves.push_back(Move(row, col, new_row, new_col));
                }
            }
        }
    }
}

std::vector<Move> ChessEngine::generate_pseudo_legal_moves() {
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
                        break;
                    case EMPTY:
                        break;
                }
            }
        }
    }
    
    return moves;
}

std::vector<Move> ChessEngine::generate_legal_moves() {
    auto pseudo_moves = generate_pseudo_legal_moves();
    std::vector<Move> legal_moves;
    
    // Find king position
    int king_row = -1, king_col = -1;
    for (int r = 0; r < 8; r++) {
        for (int c = 0; c < 8; c++) {
            if (board[r][c].first == turn && board[r][c].second == KING) {
                king_row = r;
                king_col = c;
                break;
            }
        }
        if (king_row != -1) break;
    }
    
    // Filter moves that leave king in check
    for (auto& move : pseudo_moves) {
        // Make move temporarily
        auto saved_piece = board[move.to_row][move.to_col];
        auto moving_piece = board[move.from_row][move.from_col];
        board[move.to_row][move.to_col] = moving_piece;
        board[move.from_row][move.from_col] = {WHITE, EMPTY};
        
        // Check if king is in check
        if (!is_square_attacked(king_row, king_col, (turn == WHITE) ? BLACK : WHITE)) {
            legal_moves.push_back(move);
        }
        
        // Unmake move
        board[move.from_row][move.from_col] = moving_piece;
        board[move.to_row][move.to_col] = saved_piece;
    }
    
    return legal_moves;
}

void ChessEngine::make_move(const Move& move, bool temporary) {
    // Save state for unmake
    MoveStackEntry entry = {move, board[move.to_row][move.to_col], false, -1, -1};
    
    if (en_passant_square) {
        entry.old_en_passant_row = en_passant_square->first;
        entry.old_en_passant_col = en_passant_square->second;
    }
    
    // Make the move
    auto piece = board[move.from_row][move.from_col];
    board[move.to_row][move.to_col] = piece;
    board[move.from_row][move.from_col] = {WHITE, EMPTY};
    
    // Handle promotion
    if (move.promotion != EMPTY) {
        board[move.to_row][move.to_col].second = move.promotion;
    }
    
    // Handle en passant capture
    if (piece.second == PAWN && entry.captured_piece.second == EMPTY && 
        move.from_col != move.to_col) {
        // En passant capture
        int captured_row = move.from_row;
        board[captured_row][move.to_col] = {turn == WHITE ? BLACK : WHITE, PAWN};
        entry.captured_piece = board[captured_row][move.to_col];
        entry.was_en_passant = true;
    }
    
    // Set en passant square
    if (piece.second == PAWN && abs(move.to_row - move.from_row) == 2) {
        en_passant_square = new std::pair<int, int>((move.from_row + move.to_row) / 2, move.from_col);
    } else {
        en_passant_square = nullptr;
    }
    
    // Switch turn
    turn = (turn == WHITE) ? BLACK : WHITE;
    
    // Update hash
    zobrist_hash = compute_hash();
    
    // Push to stack
    move_stack.push_back(entry);
}

void ChessEngine::unmake_move(bool temporary) {
    if (move_stack.empty()) return;
    
    MoveStackEntry entry = move_stack.back();
    move_stack.pop_back();
    
    const Move& move = entry.move;
    
    // Restore piece
    auto piece = board[move.to_row][move.to_col];
    board[move.from_row][move.from_col] = piece;
    
    // Restore captured piece or empty
    if (entry.was_en_passant) {
        int captured_row = move.from_row;
        board[captured_row][move.to_col] = {turn == WHITE ? BLACK : WHITE, PAWN};
        board[move.to_row][move.to_col] = {WHITE, EMPTY};
    } else {
        board[move.to_row][move.to_col] = entry.captured_piece;
    }
    
    // Restore en passant
    if (entry.old_en_passant_row != -1) {
        en_passant_square = new std::pair<int, int>(entry.old_en_passant_row, entry.old_en_passant_col);
    } else {
        en_passant_square = nullptr;
    }
    
    // Switch turn back
    turn = (turn == WHITE) ? BLACK : WHITE;
    
    // Update hash
    zobrist_hash = compute_hash();
}

bool ChessEngine::is_checkmate() {
    // Simplified checkmate detection
    return false;
}

bool ChessEngine::is_stalemate() {
    // Simplified stalemate detection
    return false;
}

bool ChessEngine::is_in_check(Color color) {
    // Simplified check detection
    return false;
}

// Analyzer interface methods
void ChessEngine::set_realtime_callback(void (*callback)(Move, int)) {
    // Placeholder for callback
}

std::vector<std::pair<Move, int>> ChessEngine::get_top_moves() {
    return top_moves_cache;
}

std::vector<std::vector<std::string>> ChessEngine::get_principal_variations() {
    return principal_variations_cache;
}

std::unordered_map<std::string, int> ChessEngine::get_current_analysis() {
    std::unordered_map<std::string, int> result;
    return result;
}

void ChessEngine::configure_performance(size_t tt_size, size_t max_cache, bool aggressive_caching) {
    this->tt_size = tt_size;
    transposition_table.resize(tt_size);
    this->max_cache_size = max_cache;
    this->enable_aggressive_caching = aggressive_caching;
}

std::unordered_map<std::string, int> ChessEngine::get_performance_config() {
    std::unordered_map<std::string, int> result;
    return result;
}

void ChessEngine::display_board() {
    std::cout << "  a b c d e f g h" << std::endl;
    for (int row = 0; row < 8; row++) {
        std::cout << 8 - row << " ";
        for (int col = 0; col < 8; col++) {
            auto piece = board[row][col];
            if (piece.second == EMPTY) {
                std::cout << ". ";
            } else {
                char piece_char = '?';
                switch (piece.second) {
                    case PAWN: piece_char = (piece.first == WHITE) ? 'P' : 'p'; break;
                    case KNIGHT: piece_char = (piece.first == WHITE) ? 'N' : 'n'; break;
                    case BISHOP: piece_char = (piece.first == WHITE) ? 'B' : 'b'; break;
                    case ROOK: piece_char = (piece.first == WHITE) ? 'R' : 'r'; break;
                    case QUEEN: piece_char = (piece.first == WHITE) ? 'Q' : 'q'; break;
                    case KING: piece_char = (piece.first == WHITE) ? 'K' : 'k'; break;
                    default: piece_char = '?'; break;
                }
                std::cout << piece_char << " ";
            }
        }
        std::cout << 8 - row << std::endl;
    }
    std::cout << "  a b c d e f g h" << std::endl;
}

std::string ChessEngine::get_board_fen() {
    std::string fen = "";
    
    // Piece placement
    for (int row = 0; row < 8; row++) {
        int empty_count = 0;
        for (int col = 0; col < 8; col++) {
            auto piece = board[row][col];
            if (piece.second == EMPTY) {
                empty_count++;
            } else {
                if (empty_count > 0) {
                    fen += std::to_string(empty_count);
                    empty_count = 0;
                }
                char piece_char;
                switch (piece.second) {
                    case PAWN: piece_char = 'p'; break;
                    case KNIGHT: piece_char = 'n'; break;
                    case BISHOP: piece_char = 'b'; break;
                    case ROOK: piece_char = 'r'; break;
                    case QUEEN: piece_char = 'q'; break;
                    case KING: piece_char = 'k'; break;
                    case EMPTY: piece_char = '?'; break;
                    default: piece_char = '?'; break;
                }
                if (piece.first == WHITE) {
                    piece_char = toupper(piece_char);
                }
                fen += piece_char;
            }
        }
        if (empty_count > 0) {
            fen += std::to_string(empty_count);
        }
        if (row < 7) {
            fen += "/";
        }
    }
    
    // Turn
    fen += (turn == WHITE) ? " w " : " b ";
    
    // Castling (simplified)
    fen += "KQkq ";
    
    // En passant
    if (en_passant_square) {
        std::string files = "abcdefgh";
        std::string ranks = "87654321";
        fen += files.substr(en_passant_square->second, 1) + ranks.substr(en_passant_square->first, 1) + " ";
    } else {
        fen += "- ";
    }
    
    // Halfmove and fullmove clocks (simplified)
    fen += "0 1";
    
    return fen;
}

void ChessEngine::set_board_from_fen(const std::string& fen) {
    reset_board();
    
    std::istringstream fen_stream(fen);
    std::string position, turn_str, castling, en_passant, halfmove, fullmove;
    
    fen_stream >> position >> turn_str >> castling >> en_passant >> halfmove >> fullmove;
    
    // Parse position
    int row = 0, col = 0;
    for (char c : position) {
        if (c == '/') {
            row++;
            col = 0;
        } else if (isdigit(c)) {
            col += c - '0';
        } else {
            Color color = isupper(c) ? WHITE : BLACK;
            PieceType piece;
            switch (tolower(c)) {
                case 'p': piece = PAWN; break;
                case 'n': piece = KNIGHT; break;
                case 'b': piece = BISHOP; break;
                case 'r': piece = ROOK; break;
                case 'q': piece = QUEEN; break;
                case 'k': piece = KING; break;
                default: piece = EMPTY; break;
            }
            board[row][col] = {color, piece};
            col++;
        }
    }
    
    // Parse turn
    turn = (turn_str == "w") ? WHITE : BLACK;
    
    // Update hash
    zobrist_hash = compute_hash();
}

// C interface implementation
extern "C" {
    ChessEngine* create_engine(int depth, int use_backward_search, double search_time, 
                              int realtime, int quiet) {
        return new ChessEngine(depth, use_backward_search != 0, search_time, 
                               realtime != 0, quiet != 0);
    }
    
    void destroy_engine(ChessEngine* engine) {
        delete engine;
    }
    
    const char* search(ChessEngine* engine) {
        static std::string result;
        Move best_move = engine->search();
        result = best_move.to_string();
        return result.c_str();
    }
    
    int get_evaluation(ChessEngine* engine) {
        return engine->evaluate_material();
    }
    
    void set_board_fen(ChessEngine* engine, const char* fen) {
        engine->set_board_from_fen(std::string(fen));
    }
    
    const char* get_best_move_uci(ChessEngine* engine) {
        static std::string result;
        Move best_move = engine->get_best_move();
        result = best_move.to_string();
        return result.c_str();
    }
    
    void configure_engine(ChessEngine* engine, int tt_size, int max_cache, int aggressive_caching) {
        engine->configure_performance(tt_size, max_cache, aggressive_caching != 0);
    }
}
