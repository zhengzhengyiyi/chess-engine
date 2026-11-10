#ifndef SEARCH_H
#define SEARCH_H

#include <vector>
#include <chrono>
#include "types.h"
#include "board.h"

class SearchEngine {
private:
    static constexpr int MAX_PLY = 128;
    static constexpr int MATE_SCORE = 30000;
    static constexpr int INF = 1000000;
    static constexpr int TT_EXACT = 0;
    static constexpr int TT_LOWER = 1;
    static constexpr int TT_UPPER = 2;
    
    int depth;               // maximum plies (<=0 means unlimited, time-bound only)
    double time_limit;       // seconds
    ChessBoard& board;
    std::vector<TTEntry>& transposition_table;
    size_t tt_size;
    
    std::chrono::steady_clock::time_point start_time;
    uint64_t nodes;
    bool stop;
    
    // Move ordering state (persists across iterative deepening)
    Move killers[MAX_PLY][2];
    int history[2][8][64];   // [color][piece_type][to_square]
    
    int negamax(int depth, int alpha, int beta, int ply);
    int quiescence(int alpha, int beta, int ply);
    int evaluate_side_to_move() const;
    bool in_check(Color color) const;
    void order_moves(std::vector<Move>& moves, int ply, const Move& tt_move);
    void order_root_moves(std::vector<Move>& moves);
    bool time_up() const;
    void note_cutoff_move(const Move& move, int depth, int ply);
    
public:
    SearchEngine(int d, ChessBoard& b,
                std::vector<TTEntry>& tt, size_t tts,
                double search_time = 1.0);
    
    Move search();
};

#endif // SEARCH_H
