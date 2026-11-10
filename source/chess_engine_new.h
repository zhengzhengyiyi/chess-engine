#ifndef CHESS_ENGINE_H
#define CHESS_ENGINE_H

#include "types.h"
#include "board.h"
#include "search.h"
#include "evaluation.h"
#include "zobrist.h"
// #include "nnue_eval.h"  // NNUE integration disabled for now
#include <vector>
#include <string>
#include <unordered_map>
#include <memory>

class ChessEngine {
private:
    int depth;
    bool use_backward_search;
    double search_time;
    bool realtime;
    bool quiet;
    bool use_opening_book;
    
    ChessBoard board;
    ZobristHash zobrist;
    
    // Transposition table
    std::vector<TTEntry> transposition_table;
    size_t tt_size;
    
    // Move ordering cache
    std::unordered_map<std::string, int> move_ordering_cache;
    
    // Performance optimization
    size_t max_cache_size;
    bool enable_aggressive_caching;
    
    // NNUE evaluator (currently disabled)
    // std::unique_ptr<NNUEEvaluator> nnue_evaluator;
    bool use_nnue;
    
    // Analyzer compatibility
    int current_search_depth;
    int max_search_depth;
    std::vector<std::pair<Move, int>> top_moves_cache;
    std::vector<std::vector<std::string>> principal_variations_cache;
    
    void clear_move_ordering_cache();
    
public:
    ChessEngine(int depth, bool use_backward_search = false, double search_time = 1.0, 
               bool realtime = false, bool quiet = false);
    
    // Board operations
    void reset_board();
    void make_move(const Move& move, bool temporary = false);
    void unmake_move(bool temporary = false);
    std::vector<Move> generate_legal_moves();
    std::vector<Move> generate_pseudo_legal_moves();
    
    // Search functions
    Move search();
    std::vector<Move> rank_moves();
    Move get_best_move();
    void set_depth(int d);
    int perft(int d);
    
    // Evaluation
    int evaluate_material();
    int evaluate_material_cached(const std::string& board_key, Color turn);
    
    // NNUE integration
    void set_use_nnue(bool use);
    bool get_use_nnue() const;
    
    // Position checks
    bool is_checkmate();
    bool is_stalemate();
    bool is_in_check(Color color);
    
    // Analyzer interface
    void set_realtime_callback(void (*callback)(Move, int));
    std::vector<std::pair<Move, int>> get_top_moves();
    std::vector<std::vector<std::string>> get_principal_variations();
    std::unordered_map<std::string, int> get_current_analysis();
    
    // Configuration
    void configure_performance(size_t tt_size = 1000000, size_t max_cache = 100000, 
                              bool aggressive_caching = true);
    std::unordered_map<std::string, int> get_performance_config();
    
    // Utility functions
    void display_board();
    std::string get_board_fen();
    void set_board_from_fen(const std::string& fen);
};

// C interface for Python integration
extern "C" {
    ChessEngine* create_engine(int depth, int use_backward_search, double search_time, 
                              int realtime, int quiet);
    void destroy_engine(ChessEngine* engine);
    const char* search(ChessEngine* engine);
    int get_evaluation(ChessEngine* engine);
    void set_board_fen(ChessEngine* engine, const char* fen);
    const char* get_best_move_uci(ChessEngine* engine);
    void configure_engine(ChessEngine* engine, int tt_size, int max_cache, int aggressive_caching);
    void set_engine_depth(ChessEngine* engine, int depth);
    int perft(ChessEngine* engine, int depth);
    const char* get_fen(ChessEngine* engine);
}

#endif // CHESS_ENGINE_H
