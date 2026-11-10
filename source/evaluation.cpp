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

int Evaluation::get_piece_value(PieceType piece) {
    return PIECE_VALUES[piece];
}

int Evaluation::evaluate_board(const std::vector<std::vector<std::pair<Color, PieceType>>>& board, Color turn) {
    // Traditional evaluation
    int score = 0;
    int white_material = 0;
    int black_material = 0;
    
    // Center squares for position evaluation
    int center_squares[4][2] = {{3, 3}, {3, 4}, {4, 3}, {4, 4}};
    
    for (int row = 0; row < 8; row++) {
        for (int col = 0; col < 8; col++) {
            Color color = board[row][col].first;
            PieceType piece = board[row][col].second;
            
            if (piece != EMPTY) {
                int value = PIECE_VALUES[piece];
                
                // Center control bonus
                for (int i = 0; i < 4; i++) {
                    if (row == center_squares[i][0] && col == center_squares[i][1]) {
                        value += 10;
                    }
                }
                
                // Knight/Bishop center bonus
                if ((piece == KNIGHT || piece == BISHOP)) {
                    for (int i = 0; i < 4; i++) {
                        if (row == center_squares[i][0] && col == center_squares[i][1]) {
                            value += 15;
                        }
                    }
                }
                
                // Pawn advancement bonus
                if (piece == PAWN) {
                    if (color == WHITE && row >= 4) {
                        value += 5 * (row - 3);
                    } else if (color == BLACK && row <= 3) {
                        value += 5 * (4 - row);
                    }
                }
                
                if (color == WHITE) {
                    score += value;
                    white_material += value;
                } else {
                    score -= value;
                    black_material += value;
                }
            }
        }
    }
    
    // Penalty for losing much more material than opponent
    int material_diff = white_material - black_material;
    if (turn == WHITE && material_diff < -200) {
        score -= abs(material_diff) * 2;
    } else if (turn == BLACK && material_diff > 200) {
        score -= abs(material_diff) * 2;
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
