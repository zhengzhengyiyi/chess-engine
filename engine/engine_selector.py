"""
Engine interface that can switch between Python and C++ implementations.
Use --python flag to choose engine: true for Python, false for C++.
"""

import sys
import argparse
from pathlib import Path

# Try to import C++ engine wrapper
try:
    from source.cpp_engine_wrapper import CppChessEngine
    CPP_ENGINE_AVAILABLE = True
except ImportError:
    CPP_ENGINE_AVAILABLE = False
    print("C++ engine not available, using Python engine")

# Import Python engine
from engine.Engine import ChessEngine as PythonChessEngine


def get_engine(depth=2, use_backward_search=False, search_time=1.0, 
              realtime=False, quiet=False, use_python=True):
    """
    Get chess engine instance based on --python flag.
    
    Args:
        depth: Search depth
        use_backward_search: Whether to use backward search
        search_time: Time limit for search
        realtime: Whether to use real-time updates
        quiet: Whether to suppress output
        use_python: True for Python engine, False for C++ engine
        
    Returns:
        Chess engine instance (Python or C++)
    """
    if use_python or not CPP_ENGINE_AVAILABLE:
        return PythonChessEngine(depth, use_backward_search, search_time, realtime, quiet)
    else:
        try:
            return CppChessEngine(depth, use_backward_search, search_time, realtime, quiet)
        except Exception as e:
            print(f"Failed to use C++ engine: {e}")
            print("Falling back to Python engine")
            return PythonChessEngine(depth, use_backward_search, search_time, realtime, quiet)


def parse_args():
    """Parse command line arguments for engine selection."""
    parser = argparse.ArgumentParser(description='Chess Engine with Python/C++ options')
    parser.add_argument('--python', type=bool, default=True,
                       help='Use Python engine (true) or C++ engine (false)')
    parser.add_argument('--depth', type=int, default=2,
                       help='Search depth')
    parser.add_argument('--compile-cpp', action='store_true',
                       help='Compile C++ engine')
    
    return parser.parse_args()


def main():
    """Main entry point for testing engine selection."""
    args = parse_args()
    
    if args.compile_cpp:
        from source.cpp_engine_wrapper import compile_cpp_engine
        compile_cpp_engine()
        return
    
    # Test engine selection
    engine = get_engine(depth=args.depth, use_python=args.python)
    print(f"Using engine: {'Python' if args.python else 'C++'}")
    print(f"Engine depth: {engine.depth}")
    
    # Test basic functionality
    engine.reset_board()
    print("Board reset to starting position")
    engine.display_board()


if __name__ == "__main__":
    main()