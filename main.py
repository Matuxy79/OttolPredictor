"""
Saskatchewan Lotto Scraper - Phase 2
Multi-game lottery data extraction with CLI support, batch processing, and automation
"""

import argparse
import requests
import os
import sqlite3
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LottoScraper:
    """Main scraper class supporting multiple Saskatchewan lottery games"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def fetch_html(self, url, save_file=None):
        """
        Fetch HTML from URL and optionally save to file

        Args:
            url (str): URL to fetch
            save_file (str): Optional file path to save HTML

        Returns:
            str: HTML content
        """
        try:
            logger.info(f"Fetching HTML from: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            html = response.text

            if save_file:
                with open(save_file, 'w', encoding='utf-8') as f:
                    f.write(html)
                logger.info(f"HTML saved to: {save_file}")

            return html

        except requests.RequestException as e:
            logger.error(f"Error fetching URL {url}: {e}")
            raise

    def read_html(self, file_path):
        """
        Read HTML from local file

        Args:
            file_path (str): Path to HTML file

        Returns:
            str: HTML content
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html = f.read()
            logger.info(f"HTML loaded from: {file_path}")
            return html
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise

    def parse_lotto649(self, html):
        """
        Parse Lotto 6/49 draw data

        Args:
            html (str): HTML content

        Returns:
            list: List of draw dictionaries
        """
        soup = BeautifulSoup(html, 'lxml')
        draws = []

        # Look for draw blocks
        draw_blocks = soup.find_all('div', class_='pastWinNum')

        if not draw_blocks:
            logger.warning("No Lotto 649 draw blocks found with class 'pastWinNum'")
            return draws

        logger.info(f"Found {len(draw_blocks)} Lotto 649 draw blocks")

        for block in draw_blocks:
            try:
                # Get date
                date_element = block.find('div', class_='pastWinNumDate')
                date = date_element.get_text(strip=True) if date_element else ''

                # Get main numbers
                number_elements = block.find_all('li', class_='pastWinNumber')
                numbers = [li.get_text(strip=True) for li in number_elements]

                # Get bonus number
                bonus = ''
                bonus_element = block.find('li', class_='pastWinNumberBonus')
                if bonus_element:
                    bonus_text = bonus_element.get_text(strip=True)
                    bonus = ''.join(filter(str.isdigit, bonus_text))

                # Get Gold Ball if present
                gold_ball = ''
                gold_element = block.find('li', class_='pastWinNumberGold')
                if gold_element:
                    gold_ball = ''.join(filter(str.isdigit, gold_element.get_text()))

                draw_data = {
                    'game': 'Lotto 649',
                    'date': date,
                    'numbers': ','.join(numbers),
                    'bonus': bonus,
                    'gold_ball': gold_ball,
                    'scraped_at': datetime.now().isoformat()
                }

                draws.append(draw_data)

            except Exception as e:
                logger.warning(f"Error parsing draw block: {e}")
                continue

        return draws

    def parse_lottomax(self, html):
        """
        Parse Lotto Max draw data

        Args:
            html (str): HTML content

        Returns:
            list: List of draw dictionaries
        """
        soup = BeautifulSoup(html, 'lxml')
        draws = []

        # Lotto Max might use different selectors - adapt as needed
        draw_blocks = soup.find_all('div', class_='pastWinNum') or soup.find_all('div', class_='lottomax-draw')

        if not draw_blocks:
            logger.warning("No Lotto Max draw blocks found")
            return draws

        logger.info(f"Found {len(draw_blocks)} Lotto Max draw blocks")

        for block in draw_blocks:
            try:
                # Similar parsing logic but adapted for Lotto Max structure
                date_element = block.find('div', class_='pastWinNumDate') or block.find('span', class_='draw-date')
                date = date_element.get_text(strip=True) if date_element else ''

                # Lotto Max has 7 main numbers
                number_elements = block.find_all('li', class_='pastWinNumber') or block.find_all('span', class_='number')
                numbers = [li.get_text(strip=True) for li in number_elements]

                # Bonus number
                bonus = ''
                bonus_element = block.find('li', class_='pastWinNumberBonus') or block.find('span', class_='bonus')
                if bonus_element:
                    bonus_text = bonus_element.get_text(strip=True)
                    bonus = ''.join(filter(str.isdigit, bonus_text))

                draw_data = {
                    'game': 'Lotto Max',
                    'date': date,
                    'numbers': ','.join(numbers),
                    'bonus': bonus,
                    'gold_ball': '',  # Lotto Max doesn't have Gold Ball
                    'scraped_at': datetime.now().isoformat()
                }

                draws.append(draw_data)

            except Exception as e:
                logger.warning(f"Error parsing Lotto Max draw block: {e}")
                continue

        return draws

    def parse_western649(self, html):
        """
        Parse Western 649 draw data

        Args:
            html (str): HTML content

        Returns:
            list: List of draw dictionaries
        """
        soup = BeautifulSoup(html, 'lxml')
        draws = []

        # Western 649 might use similar structure to regular 649
        draw_blocks = soup.find_all('div', class_='pastWinNum') or soup.find_all('div', class_='western649-draw')

        if not draw_blocks:
            logger.warning("No Western 649 draw blocks found")
            return draws

        logger.info(f"Found {len(draw_blocks)} Western 649 draw blocks")

        for block in draw_blocks:
            try:
                date_element = block.find('div', class_='pastWinNumDate')
                date = date_element.get_text(strip=True) if date_element else ''

                number_elements = block.find_all('li', class_='pastWinNumber')
                numbers = [li.get_text(strip=True) for li in number_elements]

                bonus = ''
                bonus_element = block.find('li', class_='pastWinNumberBonus')
                if bonus_element:
                    bonus_text = bonus_element.get_text(strip=True)
                    bonus = ''.join(filter(str.isdigit, bonus_text))

                draw_data = {
                    'game': 'Western 649',
                    'date': date,
                    'numbers': ','.join(numbers),
                    'bonus': bonus,
                    'gold_ball': '',
                    'scraped_at': datetime.now().isoformat()
                }

                draws.append(draw_data)

            except Exception as e:
                logger.warning(f"Error parsing Western 649 draw block: {e}")
                continue

        return draws

    def scrape_batch_history(self, base_url, game_type, months_back=12):
        """
        Scrape historical data by following month/year navigation links

        Args:
            base_url (str): Base URL for the lottery results
            game_type (str): Game type (649, max, western649)
            months_back (int): How many months of history to scrape

        Returns:
            list: Combined list of all draws
        """
        all_draws = []

        logger.info(f"Starting batch scrape for {game_type}, {months_back} months back")

        # This would need to be customized based on the actual website structure
        # For now, just scrape the current page
        html = self.fetch_html(base_url)

        if game_type == '649':
            draws = self.parse_lotto649(html)
        elif game_type == 'max':
            draws = self.parse_lottomax(html)
        elif game_type == 'western649':
            draws = self.parse_western649(html)
        else:
            raise ValueError(f"Unknown game type: {game_type}")

        all_draws.extend(draws)

        # TODO: Implement actual historical navigation
        # This would involve finding and following "Previous" or month links

        logger.info(f"Batch scrape completed. Total draws: {len(all_draws)}")
        return all_draws

    def save_to_csv(self, data, output_file):
        """Save data to CSV file"""
        if not data:
            logger.warning("No data to save")
            return

        df = pd.DataFrame(data)
        df.to_csv(output_file, index=False)
        logger.info(f"Saved {len(data)} records to {output_file}")

        # Show preview
        print("\nData Preview:")
        print(df.head())

    def save_to_sqlite(self, data, db_file, table_name='lottery_draws'):
        """Save data to SQLite database"""
        if not data:
            logger.warning("No data to save")
            return

        df = pd.DataFrame(data)

        # Create/connect to database
        conn = sqlite3.connect(db_file)

        # Save to database (append mode)
        df.to_sql(table_name, conn, if_exists='append', index=False)

        conn.close()
        logger.info(f"Saved {len(data)} records to SQLite database: {db_file}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Saskatchewan Lotto Scraper - Extract lottery draw data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --url https://example.com/lotto649 --game 649 --output results.csv
  python main.py --file lotto649.html --game 649 --format sqlite --output results.db
  python main.py --url https://example.com/lottomax --game max --batch 6
        """
    )

    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--url', type=str, help='URL of the lottery results page')
    input_group.add_argument('--file', type=str, help='Path to saved HTML file')

    # Game configuration
    parser.add_argument('--game', type=str, choices=['649', 'max', 'western649'], 
                       required=True, help='Lottery game type')

    # Output configuration
    parser.add_argument('--output', type=str, help='Output file path (default: auto-generated)')
    parser.add_argument('--format', type=str, choices=['csv', 'sqlite', 'both'], 
                       default='csv', help='Output format (default: csv)')

    # Batch processing
    parser.add_argument('--batch', type=int, help='Scrape historical data (months back)')
    parser.add_argument('--save-html', action='store_true', 
                       help='Save downloaded HTML for debugging')

    args = parser.parse_args()

    # Initialize scraper
    scraper = LottoScraper()

    try:
        # Determine HTML source
        if args.url:
            save_file = f"{args.game}_latest.html" if args.save_html else None

            if args.batch:
                # Batch scraping mode
                data = scraper.scrape_batch_history(args.url, args.game, args.batch)
            else:
                # Single page scraping
                html = scraper.fetch_html(args.url, save_file)

                # Parse based on game type
                if args.game == '649':
                    data = scraper.parse_lotto649(html)
                elif args.game == 'max':
                    data = scraper.parse_lottomax(html)
                elif args.game == 'western649':
                    data = scraper.parse_western649(html)

        elif args.file:
            # File-based scraping
            html = scraper.read_html(args.file)

            # Parse based on game type
            if args.game == '649':
                data = scraper.parse_lotto649(html)
            elif args.game == 'max':
                data = scraper.parse_lottomax(html)
            elif args.game == 'western649':
                data = scraper.parse_western649(html)

        # Generate output filename if not provided
        if not args.output:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if args.format == 'csv':
                args.output = f"{args.game}_results_{timestamp}.csv"
            elif args.format == 'sqlite':
                args.output = f"{args.game}_results_{timestamp}.db"
            elif args.format == 'both':
                args.output = f"{args.game}_results_{timestamp}"

        # Save output
        if args.format == 'csv':
            scraper.save_to_csv(data, args.output)
        elif args.format == 'sqlite':
            scraper.save_to_sqlite(data, args.output)
        elif args.format == 'both':
            scraper.save_to_csv(data, f"{args.output}.csv")
            scraper.save_to_sqlite(data, f"{args.output}.db")

        print(f"\n✅ Success! Extracted {len(data)} draws for {args.game}")
        print(f"📁 Output saved to: {args.output}")

        if args.format in ['sqlite', 'both']:
            print("💡 Tip: Use SQLite browser or pandas.read_sql() to analyze the database")

    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        print(f"\n❌ Error: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Check your internet connection (if using --url)")
        print("2. Verify the HTML file exists (if using --file)")
        print("3. Ensure the website structure hasn't changed")
        print("4. Try adding --save-html to debug HTML content")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
