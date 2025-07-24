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
    try:
        # First try to use the new data sources module
        try:
            from data_sources.live_scraper import LiveResultsScraper
            from core.data_manager import get_data_manager

            logger.info("Running in command-line mode with enhanced data sources")

            # Parse arguments
            parser = argparse.ArgumentParser(description="Enhanced Lottery Data Tool")
            parser.add_argument('--game', type=str, required=True, help='Game code (649, max, etc.)')
            parser.add_argument('--recent', action='store_true', help='Get only recent draws (last 30 days)')
            parser.add_argument('--output', type=str, help='Output file path')
            parser.add_argument('--format', type=str, choices=['csv', 'sqlite', 'both'], default='csv')
            parser.add_argument('--refresh-all', action='store_true', help='Refresh all data sources')

            args, _ = parser.parse_known_args()

            # Initialize components
            data_manager = get_data_manager()
            live_scraper = LiveResultsScraper()

            if args.refresh_all:
                # Refresh all data
                data_manager.refresh_all_data()
                print("✅ All data refreshed successfully")
                return 0

            if args.recent:
                # Get only recent draws
                draws = live_scraper.get_recent_draws(args.game)

                if not draws:
                    print(f"❌ No recent draws found for {args.game}")
                    return 1

                # Save to file if output specified
                if args.output:
                    live_scraper.save_to_csv(draws, args.output)
                    print(f"✅ Saved {len(draws)} recent draws to {args.output}")
                else:
                    # Print summary
                    print(f"✅ Found {len(draws)} recent draws for {args.game}")
                    for draw in draws[:5]:  # Show first 5
                        print(f"  {draw.get('date', 'Unknown')}: {draw.get('numbers', [])}")

                    if len(draws) > 5:
                        print(f"  ... and {len(draws) - 5} more")

                return 0

            # Default: load all data and show summary
            data = data_manager.load_game_data(args.game)

            if data.empty:
                print(f"❌ No data found for {args.game}")
                return 1

            # Print summary
            print(f"✅ Loaded {len(data)} draws for {args.game}")
            print(f"📊 Date range: {data['date'].min()} to {data['date'].max()}")

            # Save to file if output specified
            if args.output:
                if args.format == 'csv':
                    data.to_csv(args.output, index=False)
                    print(f"✅ Saved to {args.output}")
                elif args.format == 'sqlite':
                    import sqlite3
                    conn = sqlite3.connect(args.output)
                    data.to_sql('lottery_draws', conn, if_exists='replace', index=False)
                    conn.close()
                    print(f"✅ Saved to SQLite database: {args.output}")
                elif args.format == 'both':
                    # Save CSV
                    csv_path = args.output + '.csv'
                    data.to_csv(csv_path, index=False)

                    # Save SQLite
                    db_path = args.output + '.db'
                    import sqlite3
                    conn = sqlite3.connect(db_path)
                    data.to_sql('lottery_draws', conn, if_exists='replace', index=False)
                    conn.close()

                    print(f"✅ Saved to CSV: {csv_path}")
                    print(f"✅ Saved to SQLite: {db_path}")

            return 0

        except Exception as e:
            logger.warning(f"Enhanced data sources initialization failed: {e}")
            # Fall back to the original scraper if initialization failed
            return run_legacy_scraper()

    except ImportError as e:
        logger.error(f"Failed to import scraper module: {e}")
        print(f"Error: Failed to import scraper module: {e}")
        return 1
    except Exception as e:
        logger.error(f"Error running scraper: {e}")
        print(f"Error: Failed to run scraper: {e}")
        return 1

def run_legacy_scraper():
    """Run the legacy scraper as a fallback."""
    from wclc_scraper import run_scraper
    logger.info("Running in command-line mode with legacy scraper")
    return run_scraper()

if __name__ == '__main__':
    sys.exit(main())
