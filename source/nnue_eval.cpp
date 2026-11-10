#include "nnue_eval.h"
#include <iostream>
#include <random>
#include <algorithm>

NNUEEvaluator::NNUEEvaluator() {
    // Initialize with default sizes
    psqt_weights.resize(64 * 12 * 2, std::vector<float>(1, 0.0f));  // Simple PSQT-like features
    hidden_weights.resize(128, std::vector<float>(64 * 12 * 2, 0.0f));  // Hidden layer
    hidden_bias.resize(128, 0.0f);
    output_weights.resize(128, 0.0f);
    output_bias = 0.0f;
}

void NNUEEvaluator::initialize() {
    // Initialize with small random weights
    std::random_device rd;
    std::mt19937 gen(rd());
    std::normal_distribution<float> dist(0.0f, 0.1f);
    
    // Initialize PSQT weights
    for (auto& weight_vec : psqt_weights) {
        weight_vec[0] = dist(gen) * 0.1f;
    }
    
    // Initialize hidden layer
    for (auto& weight_vec : hidden_weights) {
        for (auto& weight : weight_vec) {
            weight = dist(gen) * 0.05f;
        }
    }
    
    // Initialize hidden bias
    for (auto& bias : hidden_bias) {
        bias = dist(gen) * 0.05f;
    }
    
    // Initialize output weights
    for (auto& weight : output_weights) {
        weight = dist(gen) * 0.05f;
    }
    
    output_bias = dist(gen) * 0.05f;
    
    std::cout << "NNUE initialized with random weights" << std::endl;
}

int NNUEEvaluator::get_piece_index(Color color, PieceType piece, int row, int col) {
    // Convert piece to index (0-11: 6 piece types × 2 colors)
    int piece_index = piece * 2 + color;
    
    // Convert square to index (0-63)
    int square_index = row * 8 + col;
    
    // Combined index
    return piece_index * 64 + square_index;
}

std::vector<float> NNUEEvaluator::extract_features(const ChessBoard& board, Color perspective) {
    std::vector<float> features(64 * 12 * 2, 0.0f);
    
    const auto& b = board.get_board();  // Use const to match interface
    
    // Extract features for each piece on the board
    for (int row = 0; row < 8; row++) {
        for (int col = 0; col < 8; col++) {
            auto piece = b[row][col];
            if (piece.second != EMPTY) {
                // Determine perspective (if we're black, flip the board)
                int actual_row = (perspective == BLACK) ? (7 - row) : row;
                int actual_col = (perspective == BLACK) ? (7 - col) : col;
                
                // Determine actual color from perspective
                Color actual_color = (piece.first == perspective) ? WHITE : BLACK;
                
                int index = get_piece_index(actual_color, piece.second, actual_row, actual_col);
                features[index] = 1.0f;
            }
        }
    }
    
    return features;
}

float NNUEEvaluator::forward_pass(const std::vector<float>& features) {
    // First layer: simple weighted sum
    float psqt_sum = 0.0f;
    for (size_t i = 0; i < features.size(); i++) {
        psqt_sum += features[i] * psqt_weights[i][0];
    }
    
    // Hidden layer
    std::vector<float> hidden(128, 0.0f);
    for (int i = 0; i < 128; i++) {
        float sum = hidden_bias[i];
        for (size_t j = 0; j < features.size(); j++) {
            sum += features[j] * hidden_weights[i][j];
        }
        // ReLU activation
        hidden[i] = std::max(0.0f, sum);
    }
    
    // Output layer
    float output = output_bias;
    for (int i = 0; i < 128; i++) {
        output += hidden[i] * output_weights[i];
    }
    
    // Add PSQT contribution
    output += psqt_sum;
    
    return output;
}

int NNUEEvaluator::evaluate(ChessBoard& board, Color perspective) {
    // Extract features
    std::vector<float> features = extract_features(board, perspective);
    
    // Forward pass through neural network
    float nnue_output = forward_pass(features);
    
    // Convert to centipawns (simplified scaling)
    int score = static_cast<int>(nnue_output * 100.0f);
    
    return score;
}

bool NNUEEvaluator::load_weights(const std::string& filename) {
    std::ifstream file(filename, std::ios::binary);
    if (!file.is_open()) {
        std::cerr << "Failed to open NNUE weights file: " << filename << std::endl;
        return false;
    }
    
    try {
        // Load PSQT weights
        for (auto& weight_vec : psqt_weights) {
            file.read(reinterpret_cast<char*>(&weight_vec[0]), sizeof(float));
        }
        
        // Load hidden weights
        for (auto& weight_vec : hidden_weights) {
            for (auto& weight : weight_vec) {
                file.read(reinterpret_cast<char*>(&weight), sizeof(float));
            }
        }
        
        // Load hidden bias
        for (auto& bias : hidden_bias) {
            file.read(reinterpret_cast<char*>(&bias), sizeof(float));
        }
        
        // Load output weights
        for (auto& weight : output_weights) {
            file.read(reinterpret_cast<char*>(&weight), sizeof(float));
        }
        
        // Load output bias
        file.read(reinterpret_cast<char*>(&output_bias), sizeof(float));
        
        std::cout << "NNUE weights loaded successfully from " << filename << std::endl;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Error loading NNUE weights: " << e.what() << std::endl;
        return false;
    }
}

bool NNUEEvaluator::save_weights(const std::string& filename) {
    std::ofstream file(filename, std::ios::binary);
    if (!file.is_open()) {
        std::cerr << "Failed to create NNUE weights file: " << filename << std::endl;
        return false;
    }
    
    try {
        // Save PSQT weights
        for (const auto& weight_vec : psqt_weights) {
            file.write(reinterpret_cast<const char*>(&weight_vec[0]), sizeof(float));
        }
        
        // Save hidden weights
        for (const auto& weight_vec : hidden_weights) {
            for (const auto& weight : weight_vec) {
                file.write(reinterpret_cast<const char*>(&weight), sizeof(float));
            }
        }
        
        // Save hidden bias
        for (const auto& bias : hidden_bias) {
            file.write(reinterpret_cast<const char*>(&bias), sizeof(float));
        }
        
        // Save output weights
        for (const auto& weight : output_weights) {
            file.write(reinterpret_cast<const char*>(&weight), sizeof(float));
        }
        
        // Save output bias
        file.write(reinterpret_cast<const char*>(&output_bias), sizeof(float));
        
        std::cout << "NNUE weights saved successfully to " << filename << std::endl;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Error saving NNUE weights: " << e.what() << std::endl;
        return false;
    }
}

void NNUEEvaluator::train_from_example(ChessBoard& board, int target_score, Color perspective, float learning_rate) {
    // Simple gradient descent training
    std::vector<float> features = extract_features(board, perspective);
    float current_output = forward_pass(features);
    float target = static_cast<float>(target_score) / 100.0f;  // Convert to NNUE scale
    float error = target - current_output;
    
    // Backpropagation (simplified)
    // Update output weights
    for (int i = 0; i < 128; i++) {
        output_weights[i] += learning_rate * error * get_hidden_activation(features, i);
    }
    output_bias += learning_rate * error;
    
    // Update PSQT weights (simplified - just direct gradient)
    for (size_t i = 0; i < features.size(); i++) {
        if (features[i] > 0.5f) {  // Only update active features
            psqt_weights[i][0] += learning_rate * error * 0.1f;
        }
    }
}

float NNUEEvaluator::get_hidden_activation(const std::vector<float>& features, int hidden_index) {
    float sum = hidden_bias[hidden_index];
    for (size_t j = 0; j < features.size(); j++) {
        sum += features[j] * hidden_weights[hidden_index][j];
    }
    return std::max(0.0f, sum);  // ReLU
}
