#ifndef CHESS_ENGINE_H
#define CHESS_ENGINE_H

#include <vector>
#include <string>
#include <memory>
#include <random>
#include <unordered_map>
#include <algorithm>
#include <limits>

// Piece types
enum PieceType {
    EMPTY = 0,
    PAWN = 1,
    KNIGHT = 2,
    BISHOP = 3,
    ROOK = 4,
    QUEEN = 5,
    KING = 6
};

// Colors
enum Color {
    WHITE = 0,
    BLACK = 1
};

// Move structure
struct Move {
    int from_row;
    int from_col;
    int to_row;
    int to_col;
    PieceType promotion;
    
    Move(int fr, int fc, int tr, int tc, PieceType prom = EMPTY)
        : from_row(fr), from_col(fc), to_row(tr), to_col(tc), promotion(prom) {}
    
    std::string to_string() const;
};

// Transposition table entry
struct TTEntry {
    uint64_t hash;
    int8_t depth;
    int16_t score;
    uint8_t flag;  // 0 = exact, 1 = lower bound, 2 = upper bound
    uint32_t best_move;
};

// Chess Engine class
class ChessEngine {
private:
    int depth;
    bool use_backward_search;
    double search_time;
    bool realtime;
    bool quiet;
    bool use_opening_book;
    
    // Transposition table
    std::vector<TTEntry> transposition_table;
    size_t tt_size;
    
    // Board state
    std::vector<std::vector<std::pair<Color, PieceType>>> board;
    Color turn;
    
    // Castling rights
    struct CastlingRights {
        bool kingside;
        bool queenside;
    };
    std::unordered_map<Color, CastlingRights> castling_rights;
    
    // En passant
    std::pair<int, int>* en_passant_square;
    
    // Move ordering cache
    std::unordered_map<std::string, int> move_ordering_cache;
    
    // Move stack for make/unmake
    struct MoveStackEntry {
        Move move;
        std::pair<Color, PieceType> captured_piece;
        bool was_en_passant;
        int old_en_passant_row;
        int old_en_passant_col;
    };
    std::vector<MoveStackEntry> move_stack;
    
    // Zobrist hashing
    uint64_t zobrist_hash;
    std::vector<std::vector<std::vector<uint64_t>>> piece_keys;
    uint64_t turn_key;
    std::vector<uint64_t> castling_keys;
    std::vector<uint64_t> enpassant_keys;
    
    // Performance optimization
    size_t max_cache_size;
    bool enable_aggressive_caching;
    
    // Analyzer compatibility
    int current_search_depth;
    int max_search_depth;
    std::vector<std::pair<Move, int>> top_moves_cache;
    std::vector<std::vector<std::string>> principal_variations_cache;
    
    // Random number generator
    std::mt19937 rng;
    
    void init_zobrist();
    uint64_t compute_hash();
    void clear_move_ordering_cache();
    
    // Move generation helpers
    bool is_on_board(int row, int col);
    bool is_square_attacked(int row, int col, Color by_color);
    void add_pawn_moves(std::vector<Move>& moves, int row, int col);
    void add_knight_moves(std::vector<Move>& moves, int row, int col);
    void add_sliding_moves(std::vector<Move>& moves, int row, int col, const int directions[8][2], int num_dirs);
    void add_king_moves(std::vector<Move>& moves, int row, int col);
    
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
    int minimax(int ply, int alpha, int beta, bool is_maximizing, int ply_count = 0);
    int quiescence_search(int alpha, int beta, int ply_count);
    Move search();
    std::vector<Move> rank_moves();
    std::vector<Move> order_moves(const std::vector<Move>& moves);
    Move get_best_move();
    
    // Evaluation
    int evaluate_material();
    int evaluate_material_cached(const std::string& board_key, Color turn);
    
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
}

#endif // CHESS_ENGINE_H