#include "chess_engine_new.h"
#include "movegen.h"
#include <iostream>
#include <sstream>
#include <iomanip>
#include <cmath>
#include <cstring>
#include <algorithm>
#include <limits>

ChessEngine::ChessEngine(int depth, bool use_backward_search, double search_time, 
                       bool realtime, bool quiet)
    : depth(depth), use_backward_search(use_backward_search), search_time(search_time),
      realtime(realtime), quiet(quiet), use_opening_book(false), use_nnue(false) {
    
    // Initialize analyzer compatibility
    current_search_depth = 0;
    max_search_depth = 0;
    
    // Initialize transposition table with memory optimization
    tt_size = 1000000;
    transposition_table.resize(tt_size);
    
    // Initialize performance settings
    max_cache_size = 100000;
    enable_aggressive_caching = true;
    
    // Initialize NNUE evaluator (disabled by default)
    // nnue_evaluator = std::make_unique<NNUEEvaluator>();
    
    // Reset board to starting position
    reset_board();
}

void ChessEngine::clear_move_ordering_cache() {
    move_ordering_cache.clear();
}

void ChessEngine::reset_board() {
    board.reset_board();
    clear_move_ordering_cache();
}

void ChessEngine::make_move(const Move& move, bool temporary) {
    board.make_move(move, temporary);
}

void ChessEngine::unmake_move(bool temporary) {
    board.unmake_move(temporary);
}

std::vector<Move> ChessEngine::generate_legal_moves() {
    MoveGenerator mg(board);
    return mg.generate_legal_moves();
}

std::vector<Move> ChessEngine::generate_pseudo_legal_moves() {
    MoveGenerator mg(board);
    return mg.generate_pseudo_legal_moves();
}

void ChessEngine::set_depth(int d) {
    depth = d;
}

int ChessEngine::perft(int d) {
    if (d <= 0) return 1;
    MoveGenerator mg(board);
    std::vector<Move> moves = mg.generate_legal_moves();
    if (d == 1) return static_cast<int>(moves.size());
    int nodes = 0;
    for (const auto& move : moves) {
        board.make_move(move, true);
        nodes += perft(d - 1);
        board.unmake_move(true);
    }
    return nodes;
}

Move ChessEngine::search() {
    SearchEngine se(depth, board, transposition_table, tt_size, search_time);
    return se.search();
}

std::vector<Move> ChessEngine::rank_moves() {
    std::vector<Move> moves = generate_legal_moves();
    
    if (moves.empty()) {
        return moves;
    }
    
    std::vector<std::pair<Move, int>> move_scores;
    
    for (const auto& move : moves) {
        int score = 0;
        
        // Make move temporarily
        make_move(move, true);
        score = evaluate_material();
        unmake_move(true);
        
        move_scores.push_back({move, score});
    }
    
    // Sort by score
    std::sort(move_scores.begin(), move_scores.end(), 
              [](const auto& a, const auto& b) { return a.second > b.second; });
    
    std::vector<Move> result;
    for (const auto& item : move_scores) {
        result.push_back(item.first);
    }
    
    return result;
}

Move ChessEngine::get_best_move() {
    return search();
}

int ChessEngine::evaluate_material() {
    // Create board key for caching
    std::string board_key = board.get_fen();
    
    if (enable_aggressive_caching) {
        return Evaluation::evaluate_cached(board.get_board(), board_key, board.get_turn());
    }
    
    return Evaluation::evaluate_board(board.get_board(), board.get_turn());
}

int ChessEngine::evaluate_material_cached(const std::string& board_key, Color turn) {
    return Evaluation::evaluate_cached(board.get_board(), board_key, turn);
}

bool ChessEngine::is_checkmate() {
    return generate_legal_moves().empty() && is_in_check(board.get_turn());
}

bool ChessEngine::is_stalemate() {
    return generate_legal_moves().empty() && !is_in_check(board.get_turn());
}

bool ChessEngine::is_in_check(Color color) {
    // Find king
    int king_row = -1, king_col = -1;
    auto& b = board.get_board();
    
    for (int row = 0; row < 8; row++) {
        for (int col = 0; col < 8; col++) {
            if (b[row][col].first == color && b[row][col].second == KING) {
                king_row = row;
                king_col = col;
                break;
            }
        }
        if (king_row != -1) break;
    }
    
    if (king_row == -1) return false;
    
    // Check if square is attacked
    Color attacker = (color == WHITE) ? BLACK : WHITE;
    MoveGenerator mg(board);
    return mg.is_square_attacked(king_row, king_col, attacker);
}

void ChessEngine::set_realtime_callback(void (*callback)(Move, int)) {
    // Placeholder for callback functionality
}

std::vector<std::pair<Move, int>> ChessEngine::get_top_moves() {
    std::vector<Move> moves = rank_moves();
    std::vector<std::pair<Move, int>> result;
    
    for (const auto& move : moves) {
        make_move(move, true);
        int score = evaluate_material();
        unmake_move(true);
        result.push_back({move, score});
    }
    
    return result;
}

std::vector<std::vector<std::string>> ChessEngine::get_principal_variations() {
    return principal_variations_cache;
}

std::unordered_map<std::string, int> ChessEngine::get_current_analysis() {
    std::unordered_map<std::string, int> analysis;
    analysis["depth"] = current_search_depth;
    analysis["max_depth"] = max_search_depth;
    return analysis;
}

void ChessEngine::configure_performance(size_t tt_size_arg, size_t max_cache_arg, bool aggressive_caching) {
    tt_size = tt_size_arg;
    transposition_table.resize(tt_size);
    max_cache_size = max_cache_arg;
    enable_aggressive_caching = aggressive_caching;
}

std::unordered_map<std::string, int> ChessEngine::get_performance_config() {
    std::unordered_map<std::string, int> config;
    config["tt_size"] = tt_size;
    config["max_cache"] = max_cache_size;
    config["aggressive_caching"] = enable_aggressive_caching;
    return config;
}

void ChessEngine::display_board() {
    board.display_board();
}

std::string ChessEngine::get_board_fen() {
    return board.get_fen();
}

void ChessEngine::set_board_from_fen(const std::string& fen) {
    board.set_from_fen(fen);
    clear_move_ordering_cache();
}

void ChessEngine::set_use_nnue(bool use) {
    use_nnue = use;
    // NNUE integration disabled for now - would require more complex setup
    // if (use && nnue_evaluator) {
    //     nnue_evaluator->initialize();
    //     nnue_evaluator->load_weights("nnue_weights.bin");
    // }
}

bool ChessEngine::get_use_nnue() const {
    return use_nnue;
}

// C interface for Python integration
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
        if (best_move.from_row == best_move.to_row &&
            best_move.from_col == best_move.to_col) {
            result.clear();
        } else {
            result = best_move.to_string();
        }
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
        if (best_move.from_row == best_move.to_row &&
            best_move.from_col == best_move.to_col) {
            result.clear();
        } else {
            result = best_move.to_string();
        }
        return result.c_str();
    }
    
    void configure_engine(ChessEngine* engine, int tt_size, int max_cache, int aggressive_caching) {
        engine->configure_performance(tt_size, max_cache, aggressive_caching != 0);
    }
    
    void set_engine_depth(ChessEngine* engine, int depth) {
        engine->set_depth(depth);
    }
    
    int perft(ChessEngine* engine, int depth) {
        return engine->perft(depth);
    }
    
    const char* get_fen(ChessEngine* engine) {
        static std::string fen;
        fen = engine->get_board_fen();
        return fen.c_str();
    }
}
