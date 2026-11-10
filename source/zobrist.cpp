#include "zobrist.h"
#include <limits>

ZobristHash::ZobristHash() {
    rng.seed(12345);
    init();
}

void ZobristHash::init() {
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
    
    // Castling keys (4: white kingside, white queenside, black kingside, black queenside)
    castling_keys.resize(4);
    for (int i = 0; i < 4; i++) {
        castling_keys[i] = dist(rng);
    }
    
    // En passant keys (8 files)
    enpassant_keys.resize(8);
    for (int i = 0; i < 8; i++) {
        enpassant_keys[i] = dist(rng);
    }
}

uint64_t ZobristHash::get_piece_key(Color color, PieceType piece, int square) const {
    return piece_keys[color][piece][square];
}

uint64_t ZobristHash::get_turn_key() const {
    return turn_key;
}

uint64_t ZobristHash::get_castling_key(int index) const {
    return castling_keys[index];
}

uint64_t ZobristHash::get_enpassant_key(int file) const {
    return enpassant_keys[file];
}
