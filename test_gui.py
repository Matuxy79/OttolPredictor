"""
Legacy test script for the Saskatoon Lotto Predictor GUI

This script was used for testing the GUI during development.
It has been replaced by main.py as the primary entry point.
This file is kept for reference but is no longer needed for normal operation.

To run the application, use:
    python main.py
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
    """Legacy test function - use main.py instead"""
    logger.warning("This is a legacy test script. Please use main.py to run the application.")
    logger.info("Redirecting to main.py...")

    # Import and run the main module
    try:
        import main as app_main
        return app_main.main()
    except ImportError as e:
        logger.error(f"Failed to import main module: {e}")
        return False

if __name__ == "__main__":
    logger.warning("This is a legacy test script. Please use main.py to run the application.")
    success = main()
    if not success:
        sys.exit(1)
