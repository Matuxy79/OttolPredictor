"""
Saskatoon Lotto Predictor - Main Application Entry Point

This is the main entry point for the Saskatoon Lotto Predictor application.
It launches the GUI by default, or runs batch scraping operations when command-line
arguments are provided.

The application now uses a modular architecture with:
- Historical PDF archives (authoritative data source)
- Live web scraping (recent draws only)
- Self-optimizing prediction strategies
- Statistical regime detection

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
import logging
from logging_config import setup_logging, get_logger

# Configure logging
# TEMP: Set to DEBUG level to identify where the application might be hanging
logging.basicConfig(
    level=logging.DEBUG,  # TEMP: Switch back to INFO later
    format='%(asctime)s [%(levelname)s] %(message)s',
    encoding='utf-8'  # Fix UnicodeEncodeError for emojis in logs
)

# Use the existing logging setup with DEBUG level
setup_logging(level=logging.DEBUG)  # TEMP: Switch back to INFO later

logger = get_logger(__name__)

def main():
    """Main application entry point"""
    logger.info("Starting Enhanced Saskatoon Lotto Predictor")

    # Pre-initialize data manager for better UX
    try:
        from core.data_manager import get_data_manager
        data_manager = get_data_manager()
        # Pre-load data in background (optional)
        # data_manager.load_game_data('649', full_refresh=False)
    except Exception as e:
        logger.warning(f"Data manager initialization failed, using fallback: {e}")

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
    # Only use the centralized batch/manual data interface
    return run_legacy_scraper()

def run_legacy_scraper():
    """Run the legacy scraper as a fallback."""

    # Centralized analytics/strategy interface for matplotlib and batch/manual data
    from wclc_scraper import WCLCScraper
    logger.info("Running in command-line mode with legacy scraper")
    # Example: expose a single interface for analytics/strategy modules
    scraper = WCLCScraper()
    # You can now use scraper.save_to_csv, save_to_sqlite, deduplicate_draws, etc.
    # For analytics/strategy testing, import this interface elsewhere as needed
    # If you want to run a batch operation, add it here or in a dedicated analytics module
    print("Legacy batch/manual data interface ready for analytics/strategy modules.")
    return 0

if __name__ == '__main__':
    sys.exit(main())
