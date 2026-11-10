#ifndef NNUE_EVAL_H
#define NNUE_EVAL_H

#include "types.h"
#include "board.h"
#include <vector>
#include <fstream>
#include <cmath>

class NNUEEvaluator {
private:
    // Simple neural network weights (these would normally be loaded from a trained file)
    // For demonstration, we'll use a simplified approach
    
    // Input layer weights (64 squares × 12 piece types × 2 colors for PSQT-like features)
    std::vector<std::vector<float>> psqt_weights;
    
    // Hidden layer weights
    std::vector<std::vector<float>> hidden_weights;
    std::vector<float> hidden_bias;
    
    // Output layer weights
    std::vector<float> output_weights;
    float output_bias;
    
    // Feature extraction
    int get_piece_index(Color color, PieceType piece, int row, int col);
    std::vector<float> extract_features(const ChessBoard& board, Color perspective);
    
    // Neural network forward pass
    float forward_pass(const std::vector<float>& features);
    float get_hidden_activation(const std::vector<float>& features, int hidden_index);
    
public:
    NNUEEvaluator();
    
    // Initialize with random weights (in production, load from trained file)
    void initialize();
    
    // Load weights from file (simplified format)
    bool load_weights(const std::string& filename);
    
    // Save weights to file
    bool save_weights(const std::string& filename);
    
    // Evaluate position using NNUE
    int evaluate(ChessBoard& board, Color perspective);
    
    // Training interface (simplified)
    void train_from_example(ChessBoard& board, int target_score, Color perspective, float learning_rate = 0.01);
};

#endif // NNUE_EVAL_H
