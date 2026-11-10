# Makefile for C++ chess engine

CXX = clang++
CXXFLAGS = -std=c++17 -O3 -march=native -fPIC
LDFLAGS = -shared

# Source files
SOURCES = types.cpp board.cpp movegen.cpp evaluation.cpp search.cpp zobrist.cpp chess_engine_new.cpp nnue_eval.cpp
OBJECTS = $(SOURCES:.cpp=.o)

# Output library
LIBRARY = libchess_engine.dylib

# Build the new refactored library
new: $(LIBRARY)

# Default target
all: $(LIBRARY)

# Compile the library
$(LIBRARY): $(OBJECTS)
	$(CXX) $(LDFLAGS) -o $@ $^

# Compile source files
%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

# Clean up
clean:
	rm -f $(OBJECTS) $(LIBRARY)

# Install library to parent directory
install: $(LIBRARY)
	cp $(LIBRARY) ../

.PHONY: all clean install