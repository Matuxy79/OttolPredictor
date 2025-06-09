"""
Saskatchewan Lotto Scraper - WCLC Integration with Batch Historical Scraping
Multi-game lottery data extraction with robust error handling and complete history
"""

import argparse
import requests
import os
import sqlite3
import time
import re
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin, urlparse
import logging
from typing import List, Dict, Optional, Set

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WCLCScraperError(Exception):
    """Custom exception for WCLC scraper errors"""
    pass

class DataValidationError(Exception):
    """Custom exception for data validation errors"""
    pass

class WCLCScraper:
    """Western Canada Lottery Corporation scraper with batch historical processing"""

    # WCLC official URLs
    WCLC_URLS = {
        '649': 'https://www.wclc.com/winning-numbers/lotto-649-extra.htm',
        'max': 'https://www.wclc.com/winning-numbers/lotto-max-extra.htm',
        'western649': 'https://www.wclc.com/winning-numbers/western-649-extra.htm',
        'westernmax': 'https://www.wclc.com/winning-numbers/western-max-extra.htm',
        'dailygrand': 'https://www.wclc.com/winning-numbers/daily-grand-extra.htm'
    }

    def __init__(self, max_retries=3, timeout=30):
        """
        Initialize WCLC scraper with configuration

        Args:
            max_retries (int): Maximum number of retry attempts
            timeout (int): Request timeout in seconds
        """
        self.max_retries = max_retries
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-CA,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.wclc.com/'
        })

        # Track processed URLs to avoid duplicates
        self.processed_urls: Set[str] = set()
        self.duplicate_draws: Set[str] = set()

    def fetch_html_with_retry(self, url: str, save_file: Optional[str] = None) -> str:
        """
        Fetch HTML from URL with retry logic and proper error handling

        Args:
            url (str): URL to fetch
            save_file (str): Optional file path to save HTML

        Returns:
            str: HTML content

        Raises:
            WCLCScraperError: If all retry attempts fail
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                logger.info(f"Fetching HTML from: {url} (attempt {attempt + 1}/{self.max_retries})")

                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()

                # Check if response looks like HTML
                content_type = response.headers.get('content-type', '').lower()
                if 'html' not in content_type:
                    logger.warning(f"Unexpected content type: {content_type}")

                html = response.text

                # Basic validation - check if HTML contains lottery-related content
                if not self._validate_html_content(html):
                    raise WCLCScraperError("HTML content doesn't appear to contain lottery data")

                if save_file:
                    with open(save_file, 'w', encoding='utf-8') as f:
                        f.write(html)
                    logger.info(f"HTML saved to: {save_file}")

                logger.info(f"Successfully fetched HTML ({len(html)} characters)")
                return html

            except requests.exceptions.Timeout as e:
                last_exception = e
                logger.warning(f"Timeout on attempt {attempt + 1}: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff

            except requests.exceptions.ConnectionError as e:
                last_exception = e
                logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
                time.sleep(2 ** attempt)

            except requests.exceptions.HTTPError as e:
                last_exception = e
                if e.response.status_code in [503, 502, 504]:  # Server errors - retry
                    logger.warning(f"Server error {e.response.status_code} on attempt {attempt + 1}")
                    time.sleep(2 ** attempt)
                else:  # Client errors - don't retry
                    raise WCLCScraperError(f"HTTP error {e.response.status_code}: {e}")

            except Exception as e:
                last_exception = e
                logger.warning(f"Unexpected error on attempt {attempt + 1}: {e}")
                time.sleep(2 ** attempt)

        # All attempts failed
        raise WCLCScraperError(f"Failed to fetch HTML after {self.max_retries} attempts. Last error: {last_exception}")

    def _validate_html_content(self, html: str) -> bool:
        """
        Validate that HTML contains expected lottery content

        Args:
            html (str): HTML content to validate

        Returns:
            bool: True if content appears valid
        """
        # Check for common lottery-related terms
        lottery_indicators = [
            'winning numbers', 'draw', 'lotto', 'jackpot', 'bonus',
            'wclc', 'lottery', 'numbers', 'draw date', 'past winning numbers'
        ]

        html_lower = html.lower()
        found_indicators = sum(1 for indicator in lottery_indicators if indicator in html_lower)

        # Require at least 3 lottery indicators
        return found_indicators >= 3 and len(html) > 1000

    def extract_month_links(self, html: str, base_url: str) -> List[str]:
        """
        Extract historical month links from the HTML using rel attributes

        Args:
            html (str): HTML content to parse
            base_url (str): Base URL for resolving relative links

        Returns:
            list: List of month URLs to scrape
        """
        soup = BeautifulSoup(html, 'lxml')
        month_links = []

        # Look for month navigation links in the pastWinNumMonths table
        selectors_to_try = [
            'a.pastMonthYearWinners[rel]',  # Primary selector
            'a[rel*="back="]',              # Alternative: any link with back parameter
            '.pastWinNumMonths a[rel]',     # Links within month table
            '.month-nav a[rel]',            # Alternative month navigation
            'a[href*="back="]',             # Links with back parameter in href
            '.pastWinNumMonths a',          # Any links in month table
            '.month-nav a',                 # Any links in month navigation
            'a[href*="month="]',            # Links with month parameter
            'a[href*="year="]'              # Links with year parameter
        ]

        found_links = []
        for selector in selectors_to_try:
            links = soup.select(selector)
            if links:
                logger.info(f"Found {len(links)} month links using selector: {selector}")
                found_links = links
                break

        if not found_links:
            logger.warning("No month navigation links found. Will only scrape current page.")
            return []

        # Extract rel or href URLs and convert to absolute URLs
        for link in found_links:
            # Try rel attribute first, then href if rel is not available
            rel_url = link.get('rel') or link.get('href')
            if rel_url:
                # Handle relative URLs
                if rel_url.startswith('/'):
                    parsed_base = urlparse(base_url)
                    full_url = f"{parsed_base.scheme}://{parsed_base.netloc}{rel_url}"
                elif rel_url.startswith('http'):
                    full_url = rel_url
                else:
                    full_url = urljoin(base_url, rel_url)

                month_links.append(full_url)

                # Log the month for debugging
                month_text = link.get_text(strip=True)
                logger.debug(f"Found month link: {month_text} -> {full_url}")

        # Remove duplicates while preserving order
        unique_links = []
        seen = set()
        for link in month_links:
            if link not in seen:
                unique_links.append(link)
                seen.add(link)

        logger.info(f"Extracted {len(unique_links)} unique month URLs for batch scraping")
        return unique_links

    def create_draw_fingerprint(self, draw_data: Dict) -> str:
        """
        Create a unique fingerprint for a draw to detect duplicates

        Args:
            draw_data (dict): Draw data dictionary

        Returns:
            str: Unique fingerprint string
        """
        # Use game, date, and numbers to create fingerprint
        game = draw_data.get('game', '')
        date = draw_data.get('date', '')
        numbers = draw_data.get('numbers', '')

        # Normalize date (remove extra whitespace)
        date_normalized = re.sub(r'\s+', ' ', date.strip())

        fingerprint = f"{game}|{date_normalized}|{numbers}"
        return fingerprint

    def read_html(self, file_path: str) -> str:
        """
        Read HTML from local file with validation

        Args:
            file_path (str): Path to HTML file

        Returns:
            str: HTML content

        Raises:
            WCLCScraperError: If file cannot be read or is invalid
        """
        try:
            if not os.path.exists(file_path):
                raise WCLCScraperError(f"HTML file not found: {file_path}")

            with open(file_path, 'r', encoding='utf-8') as f:
                html = f.read()

            if not self._validate_html_content(html):
                logger.warning(f"HTML file {file_path} may not contain valid lottery data")

            logger.info(f"HTML loaded from: {file_path} ({len(html)} characters)")
            return html

        except Exception as e:
            raise WCLCScraperError(f"Error reading HTML file {file_path}: {e}")

    def _validate_draw_data(self, draw_data: Dict, game_type: str) -> bool:
        """
        Validate extracted draw data format

        Args:
            draw_data (dict): Draw data to validate
            game_type (str): Game type for validation rules

        Returns:
            bool: True if data is valid
        """
        try:
            # Check required fields
            required_fields = ['game', 'date', 'numbers']
            for field in required_fields:
                if field not in draw_data or not draw_data[field]:
                    logger.warning(f"Missing required field: {field}")
                    return False

            # Validate numbers format
            numbers = draw_data['numbers'].split(',')
            numbers = [n.strip() for n in numbers if n.strip().isdigit()]

            # Game-specific validation
            if game_type in ['649', 'western649']:
                if len(numbers) != 6:
                    logger.warning(f"Lotto 649 should have 6 numbers, found {len(numbers)}")
                    return False
                if any(int(n) < 1 or int(n) > 49 for n in numbers):
                    logger.warning("Lotto 649 numbers should be between 1-49")
                    return False

            elif game_type in ['max', 'westernmax']:
                if len(numbers) != 7:
                    logger.warning(f"Lotto Max should have 7 numbers, found {len(numbers)}")
                    return False
                if any(int(n) < 1 or int(n) > 50 for n in numbers):
                    logger.warning("Lotto Max numbers should be between 1-50")
                    return False

            elif game_type == 'dailygrand':
                if len(numbers) != 5:
                    logger.warning(f"Daily Grand should have 5 numbers, found {len(numbers)}")
                    return False
                if any(int(n) < 1 or int(n) > 49 for n in numbers):
                    logger.warning("Daily Grand numbers should be between 1-49")
                    return False

            # Validate bonus number if present
            if draw_data.get('bonus'):
                bonus = draw_data['bonus']
                if not bonus.isdigit():
                    logger.warning(f"Invalid bonus number format: {bonus}")
                    return False

            return True

        except Exception as e:
            logger.warning(f"Error validating draw data: {e}")
            return False

    def parse_lotto649(self, html: str) -> List[Dict]:
        """
        Parse Lotto 6/49 draw data with enhanced error handling

        Args:
            html (str): HTML content

        Returns:
            list: List of validated draw dictionaries
        """
        soup = BeautifulSoup(html, 'lxml')
        draws = []

        # Multiple possible selectors for robustness
        selectors_to_try = [
            {'blocks': 'div.pastWinNum', 'date': 'div.pastWinNumDate', 'numbers': 'li.pastWinNumber', 'bonus': 'li.pastWinNumberBonus'},
            {'blocks': 'div.draw-result', 'date': '.draw-date', 'numbers': '.winning-number', 'bonus': '.bonus-number'},
            {'blocks': 'div.winning-numbers', 'date': '.date', 'numbers': '.number', 'bonus': '.bonus'},
            {'blocks': 'tr.draw-row', 'date': 'td.date', 'numbers': 'td.number', 'bonus': 'td.bonus'}
        ]

        draw_blocks = []
        used_selectors = None

        # Try different selector sets
        for selectors in selectors_to_try:
            draw_blocks = soup.select(selectors['blocks'])
            if draw_blocks:
                used_selectors = selectors
                logger.info(f"Found {len(draw_blocks)} Lotto 649 blocks using selector: {selectors['blocks']}")
                break

        if not draw_blocks:
            logger.warning("No Lotto 649 draw blocks found with any known selectors")
            return draws

        for i, block in enumerate(draw_blocks):
            try:
                # Get date
                date_element = block.select_one(used_selectors['date'])
                date = date_element.get_text(strip=True) if date_element else ''

                # Clean up date format
                date = re.sub(r'\s+', ' ', date.strip())

                # Get main numbers
                number_elements = block.select(used_selectors['numbers'])
                numbers = []
                for elem in number_elements:
                    num_text = elem.get_text(strip=True)
                    # Extract only digits
                    num_match = re.search(r'\d+', num_text)
                    if num_match:
                        numbers.append(num_match.group())

                # Get bonus number
                bonus = ''
                bonus_element = block.select_one(used_selectors['bonus'])
                if bonus_element:
                    bonus_text = bonus_element.get_text(strip=True)
                    bonus_match = re.search(r'\d+', bonus_text)
                    if bonus_match:
                        bonus = bonus_match.group()

                # Get Gold Ball if present (649-specific)
                gold_ball = ''
                gold_selectors = ['li.pastWinNumberGold', '.gold-ball', '.gold-number']
                for selector in gold_selectors:
                    gold_element = block.select_one(selector)
                    if gold_element:
                        gold_text = gold_element.get_text(strip=True)
                        gold_match = re.search(r'\d+', gold_text)
                        if gold_match:
                            gold_ball = gold_match.group()
                            break

                draw_data = {
                    'game': 'Lotto 649',
                    'date': date,
                    'numbers': ','.join(numbers),
                    'bonus': bonus,
                    'gold_ball': gold_ball,
                    'scraped_at': datetime.now().isoformat(),
                    'source_block_index': i
                }

                # Validate before adding
                if self._validate_draw_data(draw_data, '649'):
                    draws.append(draw_data)
                    logger.debug(f"Valid 649 draw added: {date}")
                else:
                    logger.warning(f"Invalid 649 draw data skipped: {date}")

            except Exception as e:
                logger.warning(f"Error parsing 649 draw block {i}: {e}")
                continue

        logger.info(f"Successfully parsed {len(draws)} valid Lotto 649 draws")
        return draws

    def parse_lottomax(self, html: str) -> List[Dict]:
        """
        Parse Lotto Max draw data with enhanced error handling

        Args:
            html (str): HTML content

        Returns:
            list: List of validated draw dictionaries
        """
        soup = BeautifulSoup(html, 'lxml')
        draws = []

        # Lotto Max specific selectors
        selectors_to_try = [
            {'blocks': 'div.pastWinNum', 'date': 'div.pastWinNumDate', 'numbers': 'li.pastWinNumber', 'bonus': 'li.pastWinNumberBonus'},
            {'blocks': 'div.lottomax-draw', 'date': '.draw-date', 'numbers': '.winning-number', 'bonus': '.bonus-number'},
            {'blocks': 'div.max-result', 'date': '.date', 'numbers': '.number', 'bonus': '.bonus'}
        ]

        draw_blocks = []
        used_selectors = None

        for selectors in selectors_to_try:
            draw_blocks = soup.select(selectors['blocks'])
            if draw_blocks:
                used_selectors = selectors
                logger.info(f"Found {len(draw_blocks)} Lotto Max blocks using selector: {selectors['blocks']}")
                break

        if not draw_blocks:
            logger.warning("No Lotto Max draw blocks found")
            return draws

        for i, block in enumerate(draw_blocks):
            try:
                # Get date
                date_element = block.select_one(used_selectors['date'])
                date = date_element.get_text(strip=True) if date_element else ''
                date = re.sub(r'\s+', ' ', date.strip())

                # Get main numbers (Lotto Max has 7)
                number_elements = block.select(used_selectors['numbers'])
                numbers = []
                for elem in number_elements:
                    num_text = elem.get_text(strip=True)
                    num_match = re.search(r'\d+', num_text)
                    if num_match:
                        numbers.append(num_match.group())

                # Get bonus number
                bonus = ''
                bonus_element = block.select_one(used_selectors['bonus'])
                if bonus_element:
                    bonus_text = bonus_element.get_text(strip=True)
                    bonus_match = re.search(r'\d+', bonus_text)
                    if bonus_match:
                        bonus = bonus_match.group()

                draw_data = {
                    'game': 'Lotto Max',
                    'date': date,
                    'numbers': ','.join(numbers),
                    'bonus': bonus,
                    'gold_ball': '',  # Lotto Max doesn't have Gold Ball
                    'scraped_at': datetime.now().isoformat(),
                    'source_block_index': i
                }

                # Validate before adding
                if self._validate_draw_data(draw_data, 'max'):
                    draws.append(draw_data)
                    logger.debug(f"Valid Max draw added: {date}")
                else:
                    logger.warning(f"Invalid Max draw data skipped: {date}")

            except Exception as e:
                logger.warning(f"Error parsing Max draw block {i}: {e}")
                continue

        logger.info(f"Successfully parsed {len(draws)} valid Lotto Max draws")
        return draws

    def parse_western649(self, html: str) -> List[Dict]:
        """
        Parse Western 649 draw data with enhanced error handling

        Args:
            html (str): HTML content

        Returns:
            list: List of validated draw dictionaries
        """
        soup = BeautifulSoup(html, 'lxml')
        draws = []

        # Western 649 specific selectors (similar to regular 649 but may have different CSS)
        selectors_to_try = [
            {'blocks': 'div.pastWinNum', 'date': 'div.pastWinNumDate', 'numbers': 'li.pastWinNumber', 'bonus': 'li.pastWinNumberBonus'},
            {'blocks': 'div.western649-draw', 'date': '.draw-date', 'numbers': '.winning-number', 'bonus': '.bonus-number'},
            {'blocks': 'div.western-result', 'date': '.date', 'numbers': '.number', 'bonus': '.bonus'}
        ]

        draw_blocks = []
        used_selectors = None

        for selectors in selectors_to_try:
            draw_blocks = soup.select(selectors['blocks'])
            if draw_blocks:
                used_selectors = selectors
                logger.info(f"Found {len(draw_blocks)} Western 649 blocks using selector: {selectors['blocks']}")
                break

        if not draw_blocks:
            logger.warning("No Western 649 draw blocks found")
            return draws

        for i, block in enumerate(draw_blocks):
            try:
                # Get date
                date_element = block.select_one(used_selectors['date'])
                date = date_element.get_text(strip=True) if date_element else ''
                date = re.sub(r'\s+', ' ', date.strip())

                # Get main numbers
                number_elements = block.select(used_selectors['numbers'])
                numbers = []
                for elem in number_elements:
                    num_text = elem.get_text(strip=True)
                    num_match = re.search(r'\d+', num_text)
                    if num_match:
                        numbers.append(num_match.group())

                # Get bonus number
                bonus = ''
                bonus_element = block.select_one(used_selectors['bonus'])
                if bonus_element:
                    bonus_text = bonus_element.get_text(strip=True)
                    bonus_match = re.search(r'\d+', bonus_text)
                    if bonus_match:
                        bonus = bonus_match.group()

                draw_data = {
                    'game': 'Western 649',
                    'date': date,
                    'numbers': ','.join(numbers),
                    'bonus': bonus,
                    'gold_ball': '',  # Western 649 typically doesn't have Gold Ball
                    'scraped_at': datetime.now().isoformat(),
                    'source_block_index': i
                }

                # Validate before adding
                if self._validate_draw_data(draw_data, '649'):  # Use 649 validation rules
                    draws.append(draw_data)
                    logger.debug(f"Valid Western 649 draw added: {date}")
                else:
                    logger.warning(f"Invalid Western 649 draw data skipped: {date}")

            except Exception as e:
                logger.warning(f"Error parsing Western 649 draw block {i}: {e}")
                continue

        logger.debug(f"Successfully parsed {len(draws)} valid Western 649 draws")
        return draws

    def parse_westernmax(self, html: str) -> List[Dict]:
        """
        Parse Western Max draw data with enhanced error handling

        Args:
            html (str): HTML content

        Returns:
            list: List of validated draw dictionaries
        """
        soup = BeautifulSoup(html, 'lxml')
        draws = []

        # Western Max specific selectors (similar to Lotto Max)
        selectors_to_try = [
            {'blocks': 'div.pastWinNum', 'date': 'div.pastWinNumDate', 'numbers': 'li.pastWinNumber', 'bonus': 'li.pastWinNumberBonus'},
            {'blocks': 'div.westernmax-draw', 'date': '.draw-date', 'numbers': '.winning-number', 'bonus': '.bonus-number'},
            {'blocks': 'div.western-max-result', 'date': '.date', 'numbers': '.number', 'bonus': '.bonus'}
        ]

        draw_blocks = []
        used_selectors = None

        for selectors in selectors_to_try:
            draw_blocks = soup.select(selectors['blocks'])
            if draw_blocks:
                used_selectors = selectors
                logger.info(f"Found {len(draw_blocks)} Western Max blocks using selector: {selectors['blocks']}")
                break

        if not draw_blocks:
            logger.warning("No Western Max draw blocks found")
            return draws

        for i, block in enumerate(draw_blocks):
            try:
                date_element = block.select_one(used_selectors['date'])
                date = date_element.get_text(strip=True) if date_element else ''
                date = re.sub(r'\s+', ' ', date.strip())

                number_elements = block.select(used_selectors['numbers'])
                numbers = []
                for elem in number_elements:
                    num_text = elem.get_text(strip=True)
                    num_match = re.search(r'\d+', num_text)
                    if num_match:
                        numbers.append(num_match.group())

                bonus = ''
                bonus_element = block.select_one(used_selectors['bonus'])
                if bonus_element:
                    bonus_text = bonus_element.get_text(strip=True)
                    bonus_match = re.search(r'\d+', bonus_text)
                    if bonus_match:
                        bonus = bonus_match.group()

                draw_data = {
                    'game': 'Western Max',
                    'date': date,
                    'numbers': ','.join(numbers),
                    'bonus': bonus,
                    'gold_ball': '',
                    'scraped_at': datetime.now().isoformat(),
                    'source_block_index': i
                }

                if self._validate_draw_data(draw_data, 'westernmax'):
                    draws.append(draw_data)
                    logger.debug(f"Valid Western Max draw added: {date}")
                else:
                    logger.warning(f"Invalid Western Max draw data skipped: {date}")

            except Exception as e:
                logger.warning(f"Error parsing Western Max draw block {i}: {e}")
                continue

        logger.debug(f"Successfully parsed {len(draws)} valid Western Max draws")
        return draws

    def parse_dailygrand(self, html: str) -> List[Dict]:
        """
        Parse Daily Grand draw data with enhanced error handling

        Args:
            html (str): HTML content

        Returns:
            list: List of validated draw dictionaries
        """
        soup = BeautifulSoup(html, 'lxml')
        draws = []

        # Daily Grand specific selectors
        selectors_to_try = [
            {'blocks': 'div.pastWinNum', 'date': 'div.pastWinNumDate', 'numbers': 'li.pastWinNumber', 'bonus': 'li.pastWinNumberBonus'},
            {'blocks': 'div.dailygrand-draw', 'date': '.draw-date', 'numbers': '.winning-number', 'bonus': '.bonus-number'},
            {'blocks': 'div.daily-grand-result', 'date': '.date', 'numbers': '.number', 'bonus': '.bonus'}
        ]

        draw_blocks = []
        used_selectors = None

        for selectors in selectors_to_try:
            draw_blocks = soup.select(selectors['blocks'])
            if draw_blocks:
                used_selectors = selectors
                logger.info(f"Found {len(draw_blocks)} Daily Grand blocks using selector: {selectors['blocks']}")
                break

        if not draw_blocks:
            logger.warning("No Daily Grand draw blocks found")
            return draws

        for i, block in enumerate(draw_blocks):
            try:
                date_element = block.select_one(used_selectors['date'])
                date = date_element.get_text(strip=True) if date_element else ''
                date = re.sub(r'\s+', ' ', date.strip())

                number_elements = block.select(used_selectors['numbers'])
                numbers = []
                for elem in number_elements:
                    num_text = elem.get_text(strip=True)
                    num_match = re.search(r'\d+', num_text)
                    if num_match:
                        numbers.append(num_match.group())

                bonus = ''
                bonus_element = block.select_one(used_selectors['bonus'])
                if bonus_element:
                    bonus_text = bonus_element.get_text(strip=True)
                    bonus_match = re.search(r'\d+', bonus_text)
                    if bonus_match:
                        bonus = bonus_match.group()

                draw_data = {
                    'game': 'Daily Grand',
                    'date': date,
                    'numbers': ','.join(numbers),
                    'bonus': bonus,
                    'gold_ball': '',
                    'scraped_at': datetime.now().isoformat(),
                    'source_block_index': i
                }

                if self._validate_draw_data(draw_data, 'dailygrand'):
                    draws.append(draw_data)
                    logger.debug(f"Valid Daily Grand draw added: {date}")
                else:
                    logger.warning(f"Invalid Daily Grand draw data skipped: {date}")

            except Exception as e:
                logger.warning(f"Error parsing Daily Grand draw block {i}: {e}")
                continue

        logger.debug(f"Successfully parsed {len(draws)} valid Daily Grand draws")
        return draws

    def _deduplicate_draws(self, draws: List[Dict]) -> List[Dict]:
        """
        Remove duplicate draws from the list based on fingerprints

        Args:
            draws (list): List of draw dictionaries

        Returns:
            list: Deduplicated list of draws
        """
        seen_fingerprints = set()
        unique_draws = []
        duplicates_removed = 0

        for draw in draws:
            fingerprint = self.create_draw_fingerprint(draw)
            if fingerprint not in seen_fingerprints:
                unique_draws.append(draw)
                seen_fingerprints.add(fingerprint)
            else:
                duplicates_removed += 1

        if duplicates_removed > 0:
            logger.info(f"Removed {duplicates_removed} duplicate draws during final deduplication")

        return unique_draws

    def _parse_draws_by_game(self, html: str, game_type: str) -> List[Dict]:
        """
        Parse draws based on game type

        Args:
            html (str): HTML content
            game_type (str): Game type

        Returns:
            list: List of draw dictionaries
        """
        if game_type == '649':
            return self.parse_lotto649(html)
        elif game_type == 'max':
            return self.parse_lottomax(html)
        elif game_type == 'western649':
            return self.parse_western649(html)
        elif game_type == 'westernmax':
            return self.parse_westernmax(html)
        elif game_type == 'dailygrand':
            return self.parse_dailygrand(html)
        else:
            raise WCLCScraperError(f"Unknown game type: {game_type}")

    def scrape_batch_history(self, base_url: str, game_type: str, max_months: Optional[int] = None) -> List[Dict]:
        """
        Scrape historical data by following month navigation links

        Args:
            base_url (str): Base URL for the lottery results
            game_type (str): Game type (649, max, western649)
            max_months (int): Maximum number of months to scrape (None for all)

        Returns:
            list: Combined list of all draws with duplicates removed
        """
        all_draws = []
        self.processed_urls.clear()
        self.duplicate_draws.clear()

        logger.info(f"Starting batch scrape for {game_type.upper()}")

        try:
            # 1. Download and parse current month page
            logger.info("Scraping current month page...")
            current_html = self.fetch_html_with_retry(base_url)

            # Parse current page draws
            current_draws = self._parse_draws_by_game(current_html, game_type)
            all_draws.extend(current_draws)
            self.processed_urls.add(base_url)

            logger.info(f"Current page: {len(current_draws)} draws found")

            # 2. Extract month links from current page
            month_links = self.extract_month_links(current_html, base_url)

            if not month_links:
                logger.warning("No historical month links found. Only current page data available.")
                return all_draws

            # 3. Limit months if specified
            if max_months and len(month_links) > max_months:
                month_links = month_links[:max_months]
                logger.info(f"Limited to {max_months} months as requested")

            # 4. Scrape each month page
            for i, month_url in enumerate(month_links, 1):
                if month_url in self.processed_urls:
                    logger.debug(f"Skipping already processed URL: {month_url}")
                    continue

                try:
                    logger.info(f"Scraping month {i}/{len(month_links)}: {month_url}")

                    # Add small delay to be respectful to the server
                    time.sleep(1)

                    month_html = self.fetch_html_with_retry(month_url)
                    month_draws = self._parse_draws_by_game(month_html, game_type)

                    # Filter out duplicates
                    new_draws = []
                    for draw in month_draws:
                        fingerprint = self.create_draw_fingerprint(draw)
                        if fingerprint not in self.duplicate_draws:
                            new_draws.append(draw)
                            self.duplicate_draws.add(fingerprint)
                        else:
                            logger.debug(f"Duplicate draw filtered: {draw.get('date', 'Unknown date')}")

                    all_draws.extend(new_draws)
                    self.processed_urls.add(month_url)

                    logger.info(f"Month {i}: {len(new_draws)} new draws added ({len(month_draws)} total found)")

                except Exception as e:
                    logger.error(f"Error scraping month {i} ({month_url}): {e}")
                    continue

            # 5. Final deduplication across all draws
            final_draws = self._deduplicate_draws(all_draws)

            logger.info(f"Batch scrape completed: {len(final_draws)} unique draws total")
            logger.info(f"Processed {len(self.processed_urls)} pages")

            return final_draws

        except Exception as e:
            logger.error(f"Batch scraping failed: {e}")
            raise WCLCScraperError(f"Batch scraping error: {e}")

    def save_to_csv(self, data: List[Dict], output_file: str) -> None:
        """Save validated data to CSV file"""
        if not data:
            logger.warning("No data to save")
            return

        try:
            df = pd.DataFrame(data)

            # Sort by date (newest first) for better readability
            if 'date' in df.columns:
                # Note: Date sorting might need improvement based on actual date format
                df = df.sort_values('date', ascending=False)

            df.to_csv(output_file, index=False)
            logger.info(f"Saved {len(data)} records to {output_file}")

            # Show preview
            print("\n📊 Data Preview:")
            print(df.head(10))
            print(f"\n✅ Total records: {len(data)}")

            # Show date range
            if len(data) > 1 and 'date' in df.columns:
                first_date = df.iloc[-1]['date']  # Oldest (last in sorted order)
                last_date = df.iloc[0]['date']    # Newest (first in sorted order)
                print(f"📅 Date range: {first_date} to {last_date}")

        except Exception as e:
            raise WCLCScraperError(f"Error saving to CSV: {e}")

    def save_to_sqlite(self, data: List[Dict], db_file: str, table_name: str = 'lottery_draws') -> None:
        """Save validated data to SQLite database"""
        if not data:
            logger.warning("No data to save")
            return

        try:
            df = pd.DataFrame(data)

            # Create/connect to database
            conn = sqlite3.connect(db_file)

            # Save to database (append mode)
            df.to_sql(table_name, conn, if_exists='append', index=False)

            conn.close()
            logger.info(f"Saved {len(data)} records to SQLite database: {db_file}")

        except Exception as e:
            raise WCLCScraperError(f"Error saving to SQLite: {e}")


def main():
    """Main CLI entry point with batch processing support"""
    parser = argparse.ArgumentParser(
        description="WCLC Lottery Scraper - Extract Western Canada lottery draw data with batch history",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape current month only
  python main.py --game 649 --output results.csv

  # Scrape all available history
  python main.py --game 649 --batch --output complete_649_history.csv

  # Scrape last 6 months
  python main.py --game max --batch --max-months 6 --format both

  # Use custom URL
  python main.py --url https://www.wclc.com/winning-numbers/lotto-649-extra.htm --game 649 --batch

  # Run with different game types
  python main.py --game western649 --output western649_results.csv
  python main.py --game westernmax --output westernmax_results.csv
  python main.py --game dailygrand --output dailygrand_results.csv
        """
    )

    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument('--url', type=str, help='WCLC lottery results page URL')
    input_group.add_argument('--file', type=str, help='Path to saved HTML file')

    # Game configuration
    parser.add_argument('--game', type=str, choices=['649', 'max', 'western649', 'westernmax', 'dailygrand'], 
                       required=True, help='Lottery game type')

    # Batch processing options
    parser.add_argument('--batch', action='store_true',
                       help='Enable batch scraping of historical data')
    parser.add_argument('--max-months', type=int,
                       help='Maximum number of months to scrape (default: all available)')

    # Output configuration
    parser.add_argument('--output', type=str, help='Output file path (default: auto-generated)')
    parser.add_argument('--format', type=str, choices=['csv', 'sqlite', 'both'], 
                       default='csv', help='Output format (default: csv)')

    # Advanced options
    parser.add_argument('--save-html', action='store_true', 
                       help='Save downloaded HTML for debugging')
    parser.add_argument('--retries', type=int, default=3,
                       help='Maximum retry attempts (default: 3)')
    parser.add_argument('--timeout', type=int, default=30,
                       help='Request timeout in seconds (default: 30)')

    args = parser.parse_args()

    # Initialize scraper with configuration
    scraper = WCLCScraper(max_retries=args.retries, timeout=args.timeout)

    try:
        # Determine URL source
        if args.url:
            base_url = args.url
        elif args.file:
            # File mode - no batch processing
            if args.batch:
                logger.warning("Batch mode not supported with --file option. Using single file only.")
            html = scraper.read_html(args.file)
            data = scraper._parse_draws_by_game(html, args.game)
        else:
            # Use default WCLC URL for the game
            if args.game in scraper.WCLC_URLS:
                base_url = scraper.WCLC_URLS[args.game]
                logger.info(f"Using default WCLC URL for {args.game}: {base_url}")
            else:
                raise WCLCScraperError("No URL provided and no default URL available for this game")

        # Process data based on mode
        if not args.file:  # URL-based processing
            if args.batch:
                # Batch mode - scrape all available history
                logger.info("🕐 Starting batch historical scraping...")
                data = scraper.scrape_batch_history(base_url, args.game, args.max_months)
            else:
                # Single page mode
                save_file = f"{args.game}_latest.html" if args.save_html else None
                html = scraper.fetch_html_with_retry(base_url, save_file)
                data = scraper._parse_draws_by_game(html, args.game)

        if not data:
            raise WCLCScraperError("No valid draw data extracted. Check HTML structure or selectors.")

        # Generate output filename if not provided
        if not args.output:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            batch_suffix = "_batch" if args.batch else ""
            if args.format == 'csv':
                args.output = f"wclc_{args.game}_results{batch_suffix}_{timestamp}.csv"
            elif args.format == 'sqlite':
                args.output = f"wclc_{args.game}_results{batch_suffix}_{timestamp}.db"
            elif args.format == 'both':
                args.output = f"wclc_{args.game}_results{batch_suffix}_{timestamp}"

        # Save output
        if args.format == 'csv':
            scraper.save_to_csv(data, args.output)
        elif args.format == 'sqlite':
            scraper.save_to_sqlite(data, args.output)
        elif args.format == 'both':
            scraper.save_to_csv(data, f"{args.output}.csv")
            scraper.save_to_sqlite(data, f"{args.output}.db")

        # Success summary
        mode_desc = "batch historical" if args.batch else "current page"
        print(f"\n🎯 Success! Extracted {len(data)} draws for {args.game.upper()} ({mode_desc})")
        print(f"📁 Output saved to: {args.output}")

        if args.batch:
            print(f"🏆 Complete historical dataset ready for analysis!")

        if args.format in ['sqlite', 'both']:
            print("💡 Tip: Use SQLite browser or pandas.read_sql() to analyze the database")

        return 0

    except WCLCScraperError as e:
        logger.error(f"WCLC scraper error: {e}")
        print(f"\n❌ Scraper Error: {e}")
        return 1

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n💥 Unexpected Error: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Check your internet connection (if using --url)")
        print("2. Verify the HTML file exists (if using --file)")
        print("3. Try using --save-html to debug HTML content")
        print("4. Check if the WCLC website structure has changed")
        return 1


if __name__ == '__main__':
    exit(main())
