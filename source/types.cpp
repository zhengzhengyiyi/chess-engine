#include "types.h"

std::string Move::to_string() const {
    std::string files = "abcdefgh";
    std::string ranks = "87654321";
    std::string prom = "";
    
    if (promotion != EMPTY) {
        switch (promotion) {
            case QUEEN: prom = "q"; break;
            case ROOK: prom = "r"; break;
            case BISHOP: prom = "b"; break;
            case KNIGHT: prom = "n"; break;
            default: prom = ""; break;
        }
    }
    
    return files.substr(from_col, 1) + ranks.substr(from_row, 1) + files.substr(to_col, 1) + ranks.substr(to_row, 1) + prom;
}
