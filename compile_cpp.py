#!/usr/bin/env python3
"""
Compile script for the C++ chess engine.
Run this to build the C++ engine before using --python=false
"""

import subprocess
import sys
from pathlib import Path

def compile_cpp_engine():
    """Compile the C++ engine using the Makefile."""
    source_dir = Path(__file__).parent / "source"
    makefile_path = source_dir / "Makefile"
    
    if not makefile_path.exists():
        print(f"Error: Makefile not found in {source_dir}")
        return False
    
    print("Compiling C++ chess engine...")
    print(f"Source directory: {source_dir}")
    
    try:
        result = subprocess.run(
            ["make", "-C", str(source_dir)],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Compilation failed!")
            print(f"Error output:\n{result.stderr}")
            return False
        
        print("C++ engine compiled successfully!")
        print(f"Library created: {source_dir}/libchess_engine.dylib")
        
        # Copy to parent directory for easier import
        try:
            import shutil
            lib_path = source_dir / "libchess_engine.dylib"
            parent_path = Path(__file__).parent / "libchess_engine.dylib"
            shutil.copy(lib_path, parent_path)
            print(f"Library copied to: {parent_path}")
        except Exception as e:
            print(f"Warning: Could not copy library to parent directory: {e}")
        
        return True
        
    except Exception as e:
        print(f"Error during compilation: {e}")
        return False

if __name__ == "__main__":
    success = compile_cpp_engine()
    sys.exit(0 if success else 1)