#include "search.h"
#include "evaluation.h"
#include "movegen.h"
#include <limits>
#include <algorithm>
#include <chrono>

SearchEngine::SearchEngine(int d, ChessBoard& b,
                         std::vector<TTEntry>& tt, size_t tts,
                         double search_time)
    : depth(d), time_limit(search_time > 0.0 ? search_time : 1.0),
      board(b), transposition_table(tt), tt_size(tts) {
    start_time = std::chrono::steady_clock::now();
    nodes = 0;
    stop = false;
    for (int p = 0; p < MAX_PLY; p++) {
        killers[p][0] = Move();
        killers[p][1] = Move();
    }
    for (int c = 0; c < 2; c++)
        for (int pc = 0; pc < 8; pc++)
            for (int s = 0; s < 64; s++)
                history[c][pc][s] = 0;
}

bool SearchEngine::time_up() const {
    double elapsed = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - start_time).count();
    return elapsed >= time_limit;
}

bool SearchEngine::in_check(Color color) const {
    MoveGenerator mg(board);
    return mg.is_in_check(color);
}

int SearchEngine::evaluate_side_to_move() const {
    int score = Evaluation::evaluate_board(board.get_board(), board.get_turn());
    return (board.get_turn() == WHITE) ? score : -score;
}

void SearchEngine::note_cutoff_move(const Move& move, int depth, int ply) {
    // Only quiet moves go to killer/history tables
    const auto& b = board.get_board();
    bool is_capture = (b[move.to_row][move.to_col].second != EMPTY);
    if (!is_capture) {
        int ep_r, ep_c;
        if (b[move.from_row][move.from_col].second == PAWN &&
            board.get_en_passant(ep_r, ep_c) &&
            move.to_row == ep_r && move.to_col == ep_c) {
            is_capture = true;
        }
    }
    if (is_capture) return;
    
    if (ply < MAX_PLY) {
        if (!(killers[ply][0] == move)) {
            killers[ply][1] = killers[ply][0];
            killers[ply][0] = move;
        }
    }
    PieceType pt = b[move.from_row][move.from_col].second;
    int& h = history[board.get_turn() == WHITE ? 0 : 1][pt][move.to_row * 8 + move.to_col];
    h += depth * depth;
    if (h > (1 << 20)) h = (1 << 20);
}

void SearchEngine::order_moves(std::vector<Move>& moves, int ply, const Move& tt_move) {
    const auto& b = board.get_board();
    
    auto move_score = [&](const Move& m) -> int {
        // Transposition table best move first
        if (m == tt_move) return 1 << 24;
        
        int score = 0;
        PieceType victim = b[m.to_row][m.to_col].second;
        PieceType attacker = b[m.from_row][m.from_col].second;
        
        bool is_capture = (victim != EMPTY);
        // En passant capture (target square empty)
        if (!is_capture && attacker == PAWN) {
            int ep_r, ep_c;
            if (board.get_en_passant(ep_r, ep_c) &&
                m.to_row == ep_r && m.to_col == ep_c) {
                is_capture = true;
                victim = PAWN;
            }
        }
        
        if (is_capture) {
            // MVV-LVA: most valuable victim, least valuable attacker
            score = Evaluation::get_piece_value(victim) * 10 -
                    Evaluation::get_piece_value(attacker);
        }
        
        if (m.promotion != EMPTY) {
            score += Evaluation::get_piece_value(m.promotion) * 5;
        }
        
        if (!is_capture) {
            if (ply < MAX_PLY && (killers[ply][0] == m || killers[ply][1] == m)) {
                score += 8000;
            }
            score += history[board.get_turn() == WHITE ? 0 : 1][attacker]
                               [m.to_row * 8 + m.to_col] / 4;
        }
        
        return score;
    };
    
    std::sort(moves.begin(), moves.end(),
              [&](const Move& a, const Move& c) { return move_score(a) > move_score(c); });
}

void SearchEngine::order_root_moves(std::vector<Move>& moves) {
    // Probe TT for this position's best move
    uint64_t h = board.get_hash();
    TTEntry& e = transposition_table[h % tt_size];
    Move tt_move;
    bool has_tt = (e.hash == h);
    if (has_tt) tt_move = e.best_move;
    order_moves(moves, 0, has_tt ? tt_move : Move());
}

int SearchEngine::negamax(int depth, int alpha, int beta, int ply) {
    if (stop) return alpha;
    
    if ((++nodes & 2047) == 0 && time_up()) {
        stop = true;
        return alpha;
    }
    
    uint64_t h = board.get_hash();
    size_t idx = h % tt_size;
    TTEntry& entry = transposition_table[idx];
    
    Move tt_move;
    bool has_tt_move = false;
    if (entry.hash == h) {
        tt_move = entry.best_move;
        has_tt_move = true;
        if (entry.depth >= depth) {
            int s = entry.score;
            // Convert mate scores stored at a different ply
            if (s > MATE_SCORE - 256 || s < -MATE_SCORE + 256) {
                s += (entry.ply - ply) * (s > 0 ? 1 : -1);
            }
            if (entry.flag == TT_EXACT) return s;
            if (entry.flag == TT_LOWER) alpha = std::max(alpha, s);
            else beta = std::min(beta, s);
            if (alpha >= beta) return s;
        }
    }
    
    if (depth <= 0) {
        return quiescence(alpha, beta, ply);
    }
    
    if (ply >= MAX_PLY) {
        return evaluate_side_to_move();
    }
    
    MoveGenerator mg(board);
    std::vector<Move> moves = mg.generate_legal_moves();
    
    if (moves.empty()) {
        if (in_check(board.get_turn())) {
            return -MATE_SCORE + ply;
        }
        return 0; // stalemate
    }
    
    order_moves(moves, ply, has_tt_move ? tt_move : Move());
    
    int best_score = std::numeric_limits<int>::min();
    Move best_move = moves[0];
    int original_alpha = alpha;
    
    for (const auto& move : moves) {
        board.make_move(move, true);
        int score = -negamax(depth - 1, -beta, -alpha, ply + 1);
        board.unmake_move(true);
        
        if (stop) return alpha;
        
        if (score > best_score) {
            best_score = score;
            best_move = move;
        }
        alpha = std::max(alpha, score);
        if (alpha >= beta) {
            note_cutoff_move(move, depth, ply);
            break;
        }
    }
    
    // Store in TT
    uint8_t flag;
    if (best_score <= original_alpha) flag = TT_UPPER;
    else if (best_score >= beta) flag = TT_LOWER;
    else flag = TT_EXACT;
    
    entry.hash = h;
    entry.score = best_score;
    entry.depth = static_cast<int16_t>(depth);
    entry.ply = static_cast<int16_t>(ply);
    entry.flag = flag;
    entry.best_move = best_move;
    
    return best_score;
}

int SearchEngine::quiescence(int alpha, int beta, int ply) {
    if (stop) return alpha;
    if ((++nodes & 2047) == 0 && time_up()) {
        stop = true;
        return alpha;
    }
    if (ply >= MAX_PLY) {
        return evaluate_side_to_move();
    }
    
    bool check = in_check(board.get_turn());
    
    int stand_pat = evaluate_side_to_move();
    if (!check) {
        if (stand_pat >= beta) return beta;
        alpha = std::max(alpha, stand_pat);
    }
    
    MoveGenerator mg(board);
    std::vector<Move> moves = mg.generate_legal_moves();
    
    std::vector<Move> tactical;
    tactical.reserve(moves.size());
    const auto& b = board.get_board();
    
    for (const auto& m : moves) {
        if (check) {
            tactical.push_back(m); // in check: search all evasions
        } else {
            PieceType victim = b[m.to_row][m.to_col].second;
            bool is_capture = (victim != EMPTY);
            if (!is_capture && b[m.from_row][m.from_col].second == PAWN) {
                int ep_r, ep_c;
                if (board.get_en_passant(ep_r, ep_c) &&
                    m.to_row == ep_r && m.to_col == ep_c) {
                    is_capture = true;
                }
            }
            if (is_capture || m.promotion != EMPTY) {
                tactical.push_back(m);
            }
        }
    }
    
    if (tactical.empty()) {
        return check ? (-MATE_SCORE + ply) : alpha;
    }
    
    // Order captures by MVV-LVA
    auto capture_score = [&](const Move& m) {
        PieceType victim = b[m.to_row][m.to_col].second;
        PieceType attacker = b[m.from_row][m.from_col].second;
        if (victim == EMPTY && attacker == PAWN) {
            int ep_r, ep_c;
            if (board.get_en_passant(ep_r, ep_c) &&
                m.to_row == ep_r && m.to_col == ep_c) {
                victim = PAWN;
            }
        }
        return Evaluation::get_piece_value(victim) * 10 -
               Evaluation::get_piece_value(attacker) +
               (m.promotion != EMPTY ? Evaluation::get_piece_value(m.promotion) * 5 : 0);
    };
    std::sort(tactical.begin(), tactical.end(),
              [&](const Move& a, const Move& c) { return capture_score(a) > capture_score(c); });
    
    for (const auto& move : tactical) {
        board.make_move(move, true);
        int score = -quiescence(-beta, -alpha, ply + 1);
        board.unmake_move(true);
        
        if (stop) return alpha;
        
        if (score >= beta) return beta;
        alpha = std::max(alpha, score);
    }
    
    return alpha;
}

Move SearchEngine::search() {
    start_time = std::chrono::steady_clock::now();
    nodes = 0;
    stop = false;
    
    MoveGenerator mg(board);
    std::vector<Move> root_moves = mg.generate_legal_moves();
    
    if (root_moves.empty()) {
        return Move();
    }
    
    int max_ply = (depth > 0) ? depth : MAX_PLY;
    if (max_ply > MAX_PLY) max_ply = MAX_PLY;
    
    Move best_move = root_moves[0];
    
    // Iterative deepening
    for (int d = 1; d <= max_ply && !stop; d++) {
        order_root_moves(root_moves);
        
        int alpha = -INF;
        int iter_best_score = -INF;
        Move iter_best = root_moves[0];
        bool completed = true;
        
        for (const auto& move : root_moves) {
            board.make_move(move, true);
            int score = -negamax(d - 1, -INF, -alpha, 1);
            board.unmake_move(true);
            
            if (stop) {
                completed = false;
                break;
            }
            
            if (score > iter_best_score) {
                iter_best_score = score;
                iter_best = move;
            }
            alpha = std::max(alpha, score);
        }
        
        if (!completed) break;
        best_move = iter_best;
        
        if (iter_best_score > MATE_SCORE - MAX_PLY ||
            iter_best_score < -MATE_SCORE + MAX_PLY) {
            break; // found mate, no need to search deeper
        }
    }
    
    return best_move;
}
