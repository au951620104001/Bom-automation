import sys
import os

# Add the parent directory (project root) to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
