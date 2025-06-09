"""
Saskatoon Lotto Predictor - Main Application Entry Point

This is the main entry point for the Saskatoon Lotto Predictor application.
It launches the GUI and provides access to all functionality.
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
    """Main application entry point"""
    logger.info("Starting Saskatoon Lotto Predictor")

    # Import the GUI module
    try:
        from gui.main_window import main as launch_gui
        logger.info("Successfully imported GUI module")
    except ImportError as e:
        logger.error(f"Failed to import GUI module: {e}")
        print(f"Error: Failed to import GUI module: {e}")
        return 1

    # Launch the GUI
    try:
        logger.info("Launching GUI...")
        launch_gui()
        return 0
    except Exception as e:
        logger.error(f"Error launching GUI: {e}")
        print(f"Error: Failed to launch GUI: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
