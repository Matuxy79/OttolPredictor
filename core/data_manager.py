"""
Unified Data Manager for Lottery Data

IMPLEMENTATION STRATEGY:
1. Maintain existing interface that GUI expects
2. Internally coordinate PDF + live scraping
3. Handle caching to avoid re-parsing PDFs
4. Detect and resolve data conflicts
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
import logging
from datetime import datetime, timedelta
import json

# Import components
from data_sources.pdf_parser import WCLCPDFParser
from wclc_scraper import WCLCScraper
from core.data_validator import DataValidator

class LotteryDataManager:
    """
    Unified data manager that combines PDF archives with live scraping

    This class maintains the same interface that the GUI expects while
    internally coordinating data from multiple sources.
    """

    def __init__(self, data_dir: str = "data"):
        """Initialize the data manager"""
        self.data_dir = data_dir
        self.processed_dir = os.path.join(data_dir, "processed")
        self.logger = logging.getLogger(__name__)

        # Initialize data sources
        self.pdf_parser = WCLCPDFParser(data_dir)
        self.live_scraper = WCLCScraper()

        # Create cache directory
        os.makedirs(self.processed_dir, exist_ok=True)

        # Initialize cache
        self._cache = {}
        self._last_refresh = {}

    def load_game_data(self, game: str, full_refresh: bool = False) -> pd.DataFrame:
        """Load and combine data from all sources with proper normalization"""
        cache_key = f"{game}_combined"

        if not full_refresh and cache_key in self._cache:
            cache_entry = self._cache[cache_key]
            if datetime.now() - cache_entry['timestamp'] < timedelta(hours=1):
                self.logger.info(f"Using cached data for {game} (age: {datetime.now() - cache_entry['timestamp']})")
                return cache_entry['data']

        self.logger.info(f"Loading data for game: {game}, full_refresh: {full_refresh}")

        # Load from all sources
        pdf_data = self._load_pdf_data(game)
        csv_data = self._load_csv_data(game) 

        # Check if we need to scrape recent data
        need_scraping = self._check_if_scraping_needed(game, pdf_data, csv_data)

        # Scrape recent data if needed
        recent_data = pd.DataFrame()
        if need_scraping or full_refresh:
            recent_data = self._scrape_recent_data(game)

        # Combine sources
        combined_data = self._combine_data_sources(game, pdf_data, csv_data, recent_data)

        # CRITICAL: Add numbers_list normalization to fix analytics
        if not combined_data.empty:
            try:
                self.logger.info("Normalizing numbers field to numbers_list...")

                # Create numbers_list column from existing numbers column
                def normalize_numbers_for_row(numbers_value):
                    """Enhanced normalization with list guarantee"""
                    try:
                        if pd.isna(numbers_value) or numbers_value is None:
                            return []

                        # CRITICAL FIX: Handle NumPy arrays explicitly
                        import numpy as np
                        if isinstance(numbers_value, np.ndarray):
                            return [int(n) for n in numbers_value.tolist() if n is not None]

                        # Use existing validator for other types
                        from core.data_validator import DataValidator
                        result = DataValidator.normalize_numbers_field(numbers_value)

                        # Force conversion to ensure it's always a Python list
                        if isinstance(result, np.ndarray):
                            return [int(n) for n in result.tolist() if n is not None]
                        elif isinstance(result, list):
                            return [int(n) for n in result if n is not None]
                        else:
                            return list(result) if result else []

                    except Exception as e:
                        self.logger.warning(f"Failed to normalize numbers value: {numbers_value}, error: {e}")
                        return []

                combined_data['numbers_list'] = combined_data['numbers'].apply(normalize_numbers_for_row)

                # Verify the normalization worked
                valid_numbers = combined_data['numbers_list'].apply(lambda x: len(x) > 0).sum()
                self.logger.info(f"Successfully normalized {valid_numbers}/{len(combined_data)} rows")

            except Exception as e:
                self.logger.error(f"Error normalizing numbers_list: {e}")
                # Create empty lists as fallback
                combined_data['numbers_list'] = [[] for _ in range(len(combined_data))]

        # Cache the result
        self._cache[cache_key] = {
            'data': combined_data,
            'timestamp': datetime.now()
        }

        self.logger.info(f"Loaded {len(combined_data)} records for {game}")
        return combined_data

    def _load_pdf_data(self, game: str) -> pd.DataFrame:
        """Load data from PDF archives"""
        try:
            # Check for cached processed PDF data first
            pdf_cache_file = self._get_latest_processed_file(game, "pdf_archive")

            if pdf_cache_file:
                self.logger.info(f"Loading PDF data from cache: {pdf_cache_file}")
                return pd.read_csv(pdf_cache_file)

            # No cache, parse PDF directly
            self.logger.info(f"Parsing PDF data for {game}")

            if game == '649':
                pdf_data = self.pdf_parser.parse_649_archive()
                if not pdf_data.empty:
                    # Save processed data for future use
                    cache_file = self.pdf_parser.save_processed_data(pdf_data, "lotto_649")
                    self.logger.info(f"Saved processed PDF data to {cache_file}")
                return pdf_data

            elif game == 'max':
                pdf_data = self.pdf_parser.parse_max_archive()
                if not pdf_data.empty:
                    # Save processed data for future use
                    cache_file = self.pdf_parser.save_processed_data(pdf_data, "lotto_max")
                    self.logger.info(f"Saved processed PDF data to {cache_file}")
                return pdf_data

            else:
                self.logger.warning(f"No PDF archive available for game: {game}")
                return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"Error loading PDF data for {game}: {e}")
            return pd.DataFrame()

    def _load_csv_data(self, game: str) -> pd.DataFrame:
        """Load data from existing CSV files"""
        try:
            # Find CSV files for this game
            csv_files = []
            for file in os.listdir():
                if file.endswith('.csv') and game in file.lower():
                    csv_files.append(file)

            if not csv_files:
                self.logger.info(f"No CSV files found for game: {game}")
                return pd.DataFrame()

            # Load and combine all CSV files
            all_data = []
            for file in csv_files:
                try:
                    df = pd.read_csv(file)
                    if not df.empty:
                        all_data.append(df)
                except Exception as e:
                    self.logger.warning(f"Error reading CSV file {file}: {e}")

            if not all_data:
                return pd.DataFrame()

            # Combine all dataframes
            combined_df = pd.concat(all_data, ignore_index=True)

            # Remove duplicates based on date
            if 'date' in combined_df.columns:
                combined_df = combined_df.drop_duplicates(subset=['date'], keep='first')

            self.logger.info(f"Loaded {len(combined_df)} records from CSV files for {game}")
            return combined_df

        except Exception as e:
            self.logger.error(f"Error loading CSV data for {game}: {e}")
            return pd.DataFrame()

    def _check_if_scraping_needed(self, game: str, pdf_data: pd.DataFrame, csv_data: pd.DataFrame) -> bool:
        """Check if we need to scrape recent data"""
        # Always scrape if we have no data
        if pdf_data.empty and csv_data.empty:
            return True

        # Get the latest date from our data
        latest_date = None

        # Check PDF data
        if not pdf_data.empty and 'date' in pdf_data.columns:
            pdf_dates = pd.to_datetime(pdf_data['date'], errors='coerce')
            pdf_latest = pdf_dates.max()
            if pd.notna(pdf_latest):
                latest_date = pdf_latest

        # Check CSV data
        if not csv_data.empty and 'date' in csv_data.columns:
            csv_dates = pd.to_datetime(csv_data['date'], errors='coerce')
            csv_latest = csv_dates.max()
            if pd.notna(csv_latest) and (latest_date is None or csv_latest > latest_date):
                latest_date = csv_latest

        # If we have no valid dates, we need to scrape
        if latest_date is None:
            return True

        # Check if the latest date is recent enough
        today = pd.Timestamp(datetime.now().date())
        days_since_latest = (today - latest_date).days

        # For 649, draws are twice a week (Wed/Sat)
        if game == '649':
            return days_since_latest > 4  # More than 4 days old

        # For Max, draws are twice a week (Tue/Fri)
        elif game == 'max':
            return days_since_latest > 4  # More than 4 days old

        # For other games, use a default threshold
        else:
            return days_since_latest > 7  # More than a week old

    def _scrape_recent_data(self, game: str) -> pd.DataFrame:
        """Scrape recent data from the website"""
        try:
            self.logger.info(f"Scraping recent data for {game}")

            # Get URL for the game
            url = self.live_scraper.get_game_url(game)

            # Scrape only the current page (recent data)
            html = self.live_scraper.fetch_html_with_retry(url)

            # Parse the data based on game type
            data = self.live_scraper._parse_draws_by_game(html, game)

            if not data:
                self.logger.warning(f"No data scraped for {game}")
                return pd.DataFrame()

            # CRITICAL FIX: Ensure numbers are always Python lists before creating DataFrame
            for draw in data:
                if 'numbers' in draw:
                    numbers = draw['numbers']
                    import numpy as np
                    if isinstance(numbers, np.ndarray):
                        draw['numbers'] = numbers.tolist()
                    elif not isinstance(numbers, list):
                        draw['numbers'] = list(numbers) if numbers else []

            # Convert to DataFrame
            df = pd.DataFrame(data)

            self.logger.info(f"Scraped {len(df)} recent records for {game}")
            return df

        except Exception as e:
            self.logger.error(f"Error scraping recent data for {game}: {e}")
            return pd.DataFrame()

    def _combine_data_sources(self, game: str, pdf_data: pd.DataFrame, 
                             csv_data: pd.DataFrame, scraped_data: pd.DataFrame) -> pd.DataFrame:
        """Combine data from all sources, resolving conflicts"""
        # Start with empty DataFrame
        combined = pd.DataFrame()

        # Add PDF data (most authoritative for historical data)
        if not pdf_data.empty:
            combined = pdf_data.copy()

        # Add CSV data (for dates not in PDF)
        if not csv_data.empty:
            if combined.empty:
                combined = csv_data.copy()
            else:
                # Get dates from combined data
                if 'date' in combined.columns:
                    combined_dates = set(combined['date'])

                    # Filter CSV data to only include dates not in combined
                    if 'date' in csv_data.columns:
                        new_csv_data = csv_data[~csv_data['date'].isin(combined_dates)]

                        # Append new data
                        if not new_csv_data.empty:
                            combined = pd.concat([combined, new_csv_data], ignore_index=True)

        # Add scraped data (most recent)
        if not scraped_data.empty:
            if combined.empty:
                combined = scraped_data.copy()
            else:
                # Get dates from combined data
                if 'date' in combined.columns and 'date' in scraped_data.columns:
                    combined_dates = set(combined['date'])

                    # For dates in both, prefer scraped data for recent dates
                    overlap_dates = set(scraped_data['date']).intersection(combined_dates)

                    if overlap_dates:
                        # Remove overlapping dates from combined
                        combined = combined[~combined['date'].isin(overlap_dates)]

                    # Append scraped data
                    combined = pd.concat([combined, scraped_data], ignore_index=True)

        # Sort by date (newest first)
        if not combined.empty and 'date' in combined.columns:
            try:
                combined['date_temp'] = pd.to_datetime(combined['date'], errors='coerce')
                combined = combined.sort_values('date_temp', ascending=False)
                combined = combined.drop('date_temp', axis=1)
            except Exception as e:
                self.logger.warning(f"Error sorting by date: {e}")

        return combined

    def _get_latest_processed_file(self, game: str, file_type: str) -> Optional[str]:
        """Get the latest processed file for a game"""
        try:
            if not os.path.exists(self.processed_dir):
                return None

            # Find matching files
            matching_files = []
            for file in os.listdir(self.processed_dir):
                if file.endswith('.csv') and game in file.lower() and file_type in file.lower():
                    matching_files.append(os.path.join(self.processed_dir, file))

            if not matching_files:
                return None

            # Sort by modification time (newest first)
            matching_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

            return matching_files[0]

        except Exception as e:
            self.logger.error(f"Error finding processed file: {e}")
            return None

    def get_latest_draw_date(self, game: str) -> Optional[str]:
        """Get the most recent draw date from combined dataset"""
        try:
            # Load data (use cache if available)
            data = self.load_game_data(game)

            if data.empty or 'date' not in data.columns:
                return None

            # Convert to datetime for proper sorting
            data['date_temp'] = pd.to_datetime(data['date'], errors='coerce')

            # Get the most recent valid date
            valid_dates = data[data['date_temp'].notna()]
            if valid_dates.empty:
                return None

            latest_date = valid_dates['date_temp'].max()

            # Find the row with this date
            latest_row = data[data['date_temp'] == latest_date].iloc[0]

            # Return the original date string
            return latest_row['date']

        except Exception as e:
            self.logger.error(f"Error getting latest draw date: {e}")
            return None

    def refresh_recent_data_only(self, game: str) -> pd.DataFrame:
        """Scrape only the most recent draws (for GUI refresh button)"""
        try:
            self.logger.info(f"Refreshing recent data for {game}")

            # Scrape recent data
            scraped_data = self._scrape_recent_data(game)

            if scraped_data.empty:
                self.logger.warning(f"No recent data found for {game}")
                return pd.DataFrame()

            # Load existing data
            cache_key = f"{game}_data"
            existing_data = self._cache.get(cache_key, pd.DataFrame())

            if existing_data.empty:
                # No existing data, just return scraped data
                self._cache[cache_key] = scraped_data
                self._last_refresh[cache_key] = datetime.now()
                return scraped_data

            # Combine with existing data
            if 'date' in existing_data.columns and 'date' in scraped_data.columns:
                # Get dates from existing data
                existing_dates = set(existing_data['date'])

                # For dates in both, prefer scraped data
                overlap_dates = set(scraped_data['date']).intersection(existing_dates)

                if overlap_dates:
                    # Remove overlapping dates from existing data
                    existing_data = existing_data[~existing_data['date'].isin(overlap_dates)]

                # Combine data
                combined = pd.concat([existing_data, scraped_data], ignore_index=True)

                # Sort by date
                try:
                    combined['date_temp'] = pd.to_datetime(combined['date'], errors='coerce')
                    combined = combined.sort_values('date_temp', ascending=False)
                    combined = combined.drop('date_temp', axis=1)
                except Exception as e:
                    self.logger.warning(f"Error sorting by date: {e}")

                # Update cache
                self._cache[cache_key] = combined
                self._last_refresh[cache_key] = datetime.now()

                return combined

            else:
                # Can't merge properly, just return scraped data
                return scraped_data

        except Exception as e:
            self.logger.error(f"Error refreshing recent data: {e}")
            return pd.DataFrame()

    def get_recent_draws(self, game: str, count: int = 10) -> List[Dict]:
        """Get the most recent draws for a game"""
        try:
            # Load data
            data = self.load_game_data(game)

            if data.empty:
                return []

            # Sort by date if possible
            if 'date' in data.columns:
                try:
                    data['date_temp'] = pd.to_datetime(data['date'], errors='coerce')
                    data = data.sort_values('date_temp', ascending=False)
                    data = data.drop('date_temp', axis=1)
                except Exception as e:
                    self.logger.warning(f"Error sorting by date: {e}")

            # Get the most recent draws
            recent_data = data.head(count)

            # Convert to list of dictionaries
            draws = []
            for _, row in recent_data.iterrows():
                draw = row.to_dict()

                # Normalize numbers field
                if 'numbers' in draw:
                    try:
                        numbers_str = draw['numbers']
                        if isinstance(numbers_str, str):
                            # Parse string representation of list
                            if numbers_str.startswith('[') and numbers_str.endswith(']'):
                                numbers = DataValidator.normalize_numbers_field(numbers_str)
                                draw['numbers'] = numbers
                    except Exception as e:
                        self.logger.warning(f"Error normalizing numbers: {e}")

                draws.append(draw)

            return draws

        except Exception as e:
            self.logger.error(f"Error getting recent draws: {e}")
            return []

    def get_game_summary(self, game: str) -> Dict:
        """Get summary statistics for a game"""
        try:
            # Load data
            data = self.load_game_data(game)

            # Debug logging
            self.logger.info(f"Loaded {len(data)} rows for game: {game}")

            # Create summary with defaults
            summary = {
                'game': game,
                'total_draws': 0,
                'date_range': 'No data',
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'most_frequent_numbers': [],
                'least_frequent_numbers': [],
                'recent_draws': 0
            }

            if data.empty:
                self.logger.info(f"Returning empty summary for game: {game}")
                return summary

            # Extract all numbers for frequency analysis
            all_numbers = []
            problematic_rows = 0

            for idx, row in data.iterrows():
                try:
                    numbers = row.get('numbers_list', [])
                    if isinstance(numbers, np.ndarray):
                        numbers = numbers.tolist()
                    if isinstance(numbers, list) and numbers:
                        all_numbers.extend(numbers)
                except Exception as e:
                    problematic_rows += 1
                    self.logger.warning(f"Row {idx} has problematic numbers: {e}")

            self.logger.info(f"Extracted {len(all_numbers)} total numbers from {len(data)} rows")
            self.logger.info(f"Found {problematic_rows} problematic rows")

            # Update total draws
            summary['total_draws'] = len(data)

            # Calculate date range
            if 'date' in data.columns:
                try:
                    data['date_temp'] = pd.to_datetime(data['date'], errors='coerce')
                    valid_dates = data[data['date_temp'].notna()]

                    if not valid_dates.empty:
                        min_date = valid_dates['date_temp'].min().strftime('%Y-%m-%d')
                        max_date = valid_dates['date_temp'].max().strftime('%Y-%m-%d')
                        summary['date_range'] = f"{min_date} to {max_date}"

                    # Count recent draws (last 30 days)
                    today = pd.Timestamp(datetime.now().date())
                    thirty_days_ago = today - pd.Timedelta(days=30)
                    recent_draws = valid_dates[valid_dates['date_temp'] >= thirty_days_ago]
                    summary['recent_draws'] = len(recent_draws)

                    data = data.drop('date_temp', axis=1)
                except Exception as e:
                    self.logger.warning(f"Error calculating date range: {e}")

            # Calculate number frequencies
            if all_numbers:
                try:
                    # Count frequencies
                    number_counts = {}
                    for num in all_numbers:
                        number_counts[num] = number_counts.get(num, 0) + 1

                    # Sort by frequency
                    sorted_numbers = sorted(number_counts.items(), key=lambda x: x[1], reverse=True)

                    # Get most and least frequent
                    summary['most_frequent_numbers'] = [num for num, count in sorted_numbers[:10]]
                    summary['least_frequent_numbers'] = [num for num, count in sorted_numbers[-10:]]

                    self.logger.info(f"Hot numbers: {summary['most_frequent_numbers'][:6]}")
                    self.logger.info(f"Cold numbers: {summary['least_frequent_numbers'][:6]}")
                except Exception as e:
                    self.logger.warning(f"Error calculating number frequencies: {e}")

            return summary

        except Exception as e:
            self.logger.error(f"Error getting game summary: {e}")
            return {
                'game': game,
                'total_draws': 0,
                'date_range': f'Error: {e}',
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'most_frequent_numbers': [],
                'least_frequent_numbers': [],
                'recent_draws': 0
            }

    def refresh_all_data(self) -> None:
        """Refresh all data from files and scraping"""
        try:
            self.logger.info("Refreshing all data")

            # Clear cache
            self._cache = {}
            self._last_refresh = {}

            # Refresh data for each game
            for game in ['649', 'max', 'western649', 'westernmax', 'dailygrand']:
                self.load_game_data(game, full_refresh=True)

            self.logger.info("All data refreshed")

        except Exception as e:
            self.logger.error(f"Error refreshing all data: {e}")


# Singleton instance for global access
_data_manager_instance = None

def get_data_manager() -> LotteryDataManager:
    """Get the singleton instance of the data manager"""
    global _data_manager_instance
    if _data_manager_instance is None:
        _data_manager_instance = LotteryDataManager()
    return _data_manager_instance
