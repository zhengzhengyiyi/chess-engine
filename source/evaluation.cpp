#include "evaluation.h"
#include "nnue_eval.h"
#include <memory>

// Piece values
const int Evaluation::PIECE_VALUES[] = {
    0,      // EMPTY
    100,    // PAWN
    320,    // KNIGHT
    330,    // BISHOP
    500,    // ROOK
    900,    // QUEEN
    20000   // KING
};

// Material values cache
std::unordered_map<std::string, int> Evaluation::material_cache;
size_t Evaluation::material_cache_size = 0;
const size_t Evaluation::MAX_MATERIAL_CACHE = 100000;

// Piece-square tables (index = row * 8 + col, row 0 = rank 8).
// Values are from White's perspective; Black mirrors vertically.
static const int PST_PAWN[64] = {
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0
};

static const int PST_KNIGHT[64] = {
   -50,-40,-30,-30,-30,-30,-40,-50,
   -40,-20,  0,  0,  0,  0,-20,-40,
   -30,  0, 10, 15, 15, 10,  0,-30,
   -30,  5, 15, 20, 20, 15,  5,-30,
   -30,  0, 15, 20, 20, 15,  0,-30,
   -30,  5, 10, 15, 15, 10,  5,-30,
   -40,-20,  0,  5,  5,  0,-20,-40,
   -50,-40,-30,-30,-30,-30,-40,-50
};

static const int PST_BISHOP[64] = {
   -20,-10,-10,-10,-10,-10,-10,-20,
   -10,  0,  0,  0,  0,  0,  0,-10,
   -10,  0,  5, 10, 10,  5,  0,-10,
   -10,  5,  5, 10, 10,  5,  5,-10,
   -10,  0, 10, 10, 10, 10,  0,-10,
   -10, 10, 10, 10, 10, 10, 10,-10,
   -10,  5,  0,  0,  0,  0,  5,-10,
   -20,-10,-10,-10,-10,-10,-10,-20
};

static const int PST_ROOK[64] = {
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0
};

static const int PST_QUEEN[64] = {
   -20,-10,-10, -5, -5,-10,-10,-20,
   -10,  0,  0,  0,  0,  0,  0,-10,
   -10,  0,  5,  5,  5,  5,  0,-10,
    -5,  0,  5,  5,  5,  5,  0, -5,
     0,  0,  5,  5,  5,  5,  0, -5,
   -10,  5,  5,  5,  5,  5,  0,-10,
   -10,  0,  5,  0,  0,  0,  0,-10,
   -20,-10,-10, -5, -5,-10,-10,-20
};

static const int PST_KING[64] = {
   -30,-40,-40,-50,-50,-40,-40,-30,
   -30,-40,-40,-50,-50,-40,-40,-30,
   -30,-40,-40,-50,-50,-40,-40,-30,
   -30,-40,-40,-50,-50,-40,-40,-30,
   -20,-30,-30,-40,-40,-30,-30,-20,
   -10,-20,-20,-20,-20,-20,-20,-10,
    20, 20,  0,  0,  0,  0, 20, 20,
    20, 30, 10,  0,  0, 10, 30, 20
};

static const int* pst_for(PieceType piece) {
    switch (piece) {
        case PAWN:   return PST_PAWN;
        case KNIGHT: return PST_KNIGHT;
        case BISHOP: return PST_BISHOP;
        case ROOK:   return PST_ROOK;
        case QUEEN:  return PST_QUEEN;
        case KING:   return PST_KING;
        default:     return nullptr;
    }
}

int Evaluation::get_piece_value(PieceType piece) {
    return PIECE_VALUES[piece];
}

int Evaluation::evaluate_board(const std::vector<std::vector<std::pair<Color, PieceType>>>& board, Color turn) {
    (void)turn; // Evaluation is side-agnostic; search negates for Black.
    int score = 0;
    
    for (int row = 0; row < 8; row++) {
        for (int col = 0; col < 8; col++) {
            Color color = board[row][col].first;
            PieceType piece = board[row][col].second;
            
            if (piece == EMPTY) continue;
            
            int value = PIECE_VALUES[piece];
            const int* pst = pst_for(piece);
            if (pst) {
                // Mirror the table vertically for Black
                int idx = (color == WHITE) ? (row * 8 + col)
                                           : ((7 - row) * 8 + col);
                value += pst[idx];
            }
            
            score += (color == WHITE) ? value : -value;
        }
    }
    
    return score;
}

int Evaluation::evaluate_cached(const std::vector<std::vector<std::pair<Color, PieceType>>>& board, 
                                const std::string& board_key, Color turn) {
    // Check cache first
    auto it = material_cache.find(board_key);
    if (it != material_cache.end()) {
        return it->second;
    }
    
    // Compute and cache
    int score = evaluate_board(board, turn);
    
    // LRU cache management
    if (material_cache_size >= MAX_MATERIAL_CACHE) {
        material_cache.clear();
        material_cache_size = 0;
    }
    
    material_cache[board_key] = score;
    material_cache_size++;
    
    return score;
}

void Evaluation::clear_cache() {
    material_cache.clear();
    material_cache_size = 0;
}
