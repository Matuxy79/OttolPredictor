"""
Test script for the Saskatoon Lotto Predictor GUI

This script launches the GUI and tests basic functionality.
"""

import sys
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Main test function"""
    logger.info("Starting Saskatoon Lotto Predictor GUI test")
    
    # Import the GUI module
    try:
        from gui.main_window import main
        logger.info("Successfully imported GUI module")
    except ImportError as e:
        logger.error(f"Failed to import GUI module: {e}")
        return False
    
    # Launch the GUI
    try:
        logger.info("Launching GUI...")
        main()
        return True
    except Exception as e:
        logger.error(f"Error launching GUI: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        logger.info("GUI test completed successfully")
    else:
        logger.error("GUI test failed")
        sys.exit(1)