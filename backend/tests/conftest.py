import sys
import os

# Add repository root to python path for pytest module resolution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
