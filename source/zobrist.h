#ifndef ZOBRIST_H
#define ZOBRIST_H

#include <vector>
#include <cstdint>
#include <random>
#include "types.h"

class ZobristHash {
private:
    std::vector<std::vector<std::vector<uint64_t>>> piece_keys;
    uint64_t turn_key;
    std::vector<uint64_t> castling_keys;
    std::vector<uint64_t> enpassant_keys;
    std::mt19937 rng;
    
public:
    ZobristHash();
    void init();
    uint64_t get_piece_key(Color color, PieceType piece, int square) const;
    uint64_t get_turn_key() const;
    uint64_t get_castling_key(int index) const;
    uint64_t get_enpassant_key(int file) const;
};

#endif // ZOBRIST_H
