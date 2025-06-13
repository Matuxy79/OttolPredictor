"""
Saskatoon Lotto Predictor - Main Application Entry Point

This is the main entry point for the Saskatoon Lotto Predictor application.
It launches the GUI by default, or runs batch scraping operations when command-line
arguments are provided.

Examples:
  # Launch GUI (default)
  python main.py

  # Scrape Lotto Max data for the last month and save to CSV
  python main.py --game max --batch --max-months 1 --format csv

  # Scrape Western Max data for the last month and save to CSV
  python main.py --game westernmax --batch --max-months 1 --format csv

  # Scrape Daily Grand data for the last month and save to CSV
  python main.py --game dailygrand --batch --max-months 1 --format csv
"""

import sys
import os
import argparse
from logging_config import setup_logging, get_logger

# Configure logging
setup_logging()

logger = get_logger(__name__)

def main():
    """Main application entry point"""
    logger.info("Starting Saskatoon Lotto Predictor")

    # Check if command-line arguments are provided
    if len(sys.argv) > 1:
        # Command-line mode - parse arguments and run scraper
        return run_cli_mode()
    else:
        # GUI mode - launch the GUI
        return run_gui_mode()

def run_gui_mode():
    """Launch the GUI application"""
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

def run_cli_mode():
    """Run in command-line mode for batch scraping operations"""
    try:
        # Import the scraper module
        from wclc_scraper import run_scraper
        logger.info("Running in command-line mode")

        # Call the run_scraper function from wclc_scraper.py
        return run_scraper()
    except ImportError as e:
        logger.error(f"Failed to import scraper module: {e}")
        print(f"Error: Failed to import scraper module: {e}")
        return 1
    except Exception as e:
        logger.error(f"Error running scraper: {e}")
        print(f"Error: Failed to run scraper: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
