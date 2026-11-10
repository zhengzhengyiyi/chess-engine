#ifndef TYPES_H
#define TYPES_H

#include <string>
#include <cstdint>

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
    
    Move() : from_row(0), from_col(0), to_row(0), to_col(0), promotion(EMPTY) {}
    Move(int fr, int fc, int tr, int tc, PieceType prom = EMPTY)
        : from_row(fr), from_col(fc), to_row(tr), to_col(tc), promotion(prom) {}
    
    bool operator==(const Move& other) const {
        return from_row == other.from_row && from_col == other.from_col &&
               to_row == other.to_row && to_col == other.to_col &&
               promotion == other.promotion;
    }
    bool operator!=(const Move& other) const { return !(*this == other); }
    
    std::string to_string() const;
};

// Transposition table entry
// flag: 0 = exact, 1 = lower bound, 2 = upper bound
struct TTEntry {
    uint64_t hash = 0;
    int32_t score = 0;
    int16_t depth = -1;
    int16_t ply = 0;
    uint8_t flag = 0;
    Move best_move;
    
    TTEntry() = default;
};

#endif // TYPES_H
