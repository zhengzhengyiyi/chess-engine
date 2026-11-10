#ifndef EVALUATION_H
#define EVALUATION_H

#include <vector>
#include <string>
#include <unordered_map>
#include "types.h"
#include "board.h"

class Evaluation {
private:
    static const int PIECE_VALUES[];
    static std::unordered_map<std::string, int> material_cache;
    static size_t material_cache_size;
    static const size_t MAX_MATERIAL_CACHE;
    
public:
    static int get_piece_value(PieceType piece);
    static int evaluate_board(const std::vector<std::vector<std::pair<Color, PieceType>>>& board, Color turn);
    static int evaluate_cached(const std::vector<std::vector<std::pair<Color, PieceType>>>& board, 
                              const std::string& board_key, Color turn);
    static void clear_cache();
};

#endif // EVALUATION_H
