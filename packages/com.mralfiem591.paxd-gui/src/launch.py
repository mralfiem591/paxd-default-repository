#!/usr/bin/env python3
"""
PaxD GUI Launcher
Simple launcher script for the PaxD GUI application
"""

import sys
import os

# Add the src directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from paxd_gui import PaxDGUI
    
    if __name__ == "__main__":
        app = PaxDGUI()
        app.run()
except ImportError as e:
    print(f"Error importing PaxD GUI: {e}")
    print("Make sure all dependencies are installed.")
    sys.exit(1)
except Exception as e:
    print(f"Error starting PaxD GUI: {e}")
    sys.exit(1)