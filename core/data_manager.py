def get_data_manager(data_dir: str = "data"):
    """Factory function to get a singleton LotteryDataManager instance."""
    # Use a module-level singleton to avoid multiple instances
    if not hasattr(get_data_manager, "_instance"):
        get_data_manager._instance = LotteryDataManager(data_dir)
    # Attach helper methods for GUI access
    _data_manager_singleton = get_data_manager._instance
    _data_manager_singleton.get_most_recent_draw = _data_manager_singleton.get_most_recent_draw
    _data_manager_singleton.get_most_common_combination = _data_manager_singleton.get_most_common_combination
    return _data_manager_singleton
"""
Unified Data Manager for Lottery Data

IMPLEMENTATION STRATEGY:
1. Maintain existing interface that GUI expects
2. Internally coordinate PDF data only (live scraping removed)
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

from core.activity_logger import ActivityLogger

# Import components
from data_sources.pdf_parser import WCLCPDFParser
from core.data_validator import DataValidator

class LotteryDataManager:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self._cache = {}
        self.logger = logging.getLogger(__name__)
        self.pdf_parser = WCLCPDFParser()
        self.validator = DataValidator()
        self.activity_logger = ActivityLogger()

    def get_most_recent_draw(self, game: str) -> Optional[dict]:
        """Return the most recent draw record for the specified game."""
        data = self.load_game_data(game)
        if data.empty or 'date' not in data.columns:
            return None
        try:
            data['date_temp'] = pd.to_datetime(data['date'], errors='coerce')
            valid_data = data[data['date_temp'].notna()]
            if valid_data.empty:
                return None
            most_recent = valid_data.sort_values('date_temp', ascending=False).iloc[0]
            return most_recent.to_dict()
        except Exception as e:
            self.logger.error(f"Error getting most recent draw: {e}")
            return None

    def get_most_common_combination(self, game: str) -> Optional[List[int]]:
        """Return the most common winning number combination for the specified game."""
        data = self.load_game_data(game)
        if data.empty or 'numbers_list' not in data.columns:
            return None
        try:
            # Convert lists to tuples for counting
            combos = data['numbers_list'].apply(lambda x: tuple(sorted(x)) if isinstance(x, list) else None)
            combos = combos.dropna()
            if combos.empty:
                return None
            from collections import Counter
            most_common_combo, _ = Counter(combos).most_common(1)[0]
            return list(most_common_combo)
        except Exception as e:
            self.logger.error(f"Error getting most common combination: {e}")
            return None

    def get_most_frequent_numbers(self, game: str, limit: int = 6) -> List[int]:
        """Get the most frequently drawn numbers for a game."""
        try:
            data = self.load_game_data(game)
            if data.empty:
                return []

            # Handle both 'numbers' and 'numbers_list' columns for compatibility
            numbers_col = 'numbers_list' if 'numbers_list' in data.columns else 'numbers'
            if numbers_col not in data.columns:
                return []
            
            # Convert string numbers to lists if needed
            if numbers_col == 'numbers' and isinstance(data[numbers_col].iloc[0], str):
                from schema import DrawRecord
                data['numbers_list'] = data[numbers_col].apply(
                    lambda x: DrawRecord._parse_numbers(None, x) if x else []
                )
                numbers_col = 'numbers_list'
            
            # Flatten all numbers and count frequencies, ensuring integers
            all_numbers = []
            for nums in data[numbers_col]:
                if isinstance(nums, (list, np.ndarray)):
                    all_numbers.extend(int(n) for n in nums if n is not None)
                
            if not all_numbers:
                return []
                
            from collections import Counter
            frequencies = Counter(all_numbers)
            
            # Get valid number range for game type
            max_num = 49 if game == '649' else 50
            
            # Only include numbers in valid range
            valid_numbers = {num: freq for num, freq in frequencies.items() 
                           if 1 <= num <= max_num}
            
            # Return the most common valid numbers
            return [num for num, _ in Counter(valid_numbers).most_common(limit)]
        except Exception as e:
            self.logger.error(f"Error getting most frequent numbers: {e}")
            return []

    def get_least_frequent_numbers(self, game: str, limit: int = 6) -> List[int]:
        """Get the least frequently drawn numbers for a game."""
        try:
            data = self.load_game_data(game)
            if data.empty:
                return []
            
            # Handle both 'numbers' and 'numbers_list' columns for compatibility
            numbers_col = 'numbers_list' if 'numbers_list' in data.columns else 'numbers'
            if numbers_col not in data.columns:
                return []
            
            # Convert string numbers to lists if needed
            if numbers_col == 'numbers' and isinstance(data[numbers_col].iloc[0], str):
                from schema import DrawRecord
                data['numbers_list'] = data[numbers_col].apply(
                    lambda x: DrawRecord._parse_numbers(None, x) if x else []
                )
                numbers_col = 'numbers_list'
            
            # Get the valid number range for this game
            max_num = 49 if game == '649' else 50
            
            # Initialize frequencies for all possible numbers
            frequencies = {n: 0 for n in range(1, max_num + 1)}
            
            # Count actual frequencies
            for nums in data[numbers_col]:
                if isinstance(nums, (list, np.ndarray)):
                    for n in nums:
                        if n is not None:
                            n = int(n)
                            if 1 <= n <= max_num:
                                frequencies[n] += 1
            
            # Return the least common numbers, breaking ties by number value
            return [num for num, _ in sorted(frequencies.items(), 
                                           key=lambda x: (x[1], x[0]))[:limit]]
        except Exception as e:
            self.logger.error(f"Error getting least frequent numbers: {e}")
            return []
    def refresh_all_data(self):
        """Refresh all data from files only (scraping removed)."""
        self.logger.info("Refreshing all data")
        self._cache = {}
        self._last_refresh = {}
        for game in ['649', 'max', 'western649', 'westernmax', 'dailygrand']:
            self.load_game_data(game, full_refresh=True)
        self.logger.info("All data refreshed")
    def get_game_summary(self, game: str) -> dict:
        """Return summary statistics for the specified game for dashboard/analytics."""
        data = self.load_game_data(game)
        summary = {
            'game_display_name': 'Lotto 6/49' if game == '649' else 'Lotto Max' if game == 'max' else game.title(),
            'total_draws': 0,
            'date_range': 'Error',
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'hot_numbers': 'No data',
            'cold_numbers': 'No data',
            'activity_messages': []
        }
        if not data.empty and 'numbers_list' in data.columns:
            summary['total_draws'] = len(data)
            # Log the analysis activity
            self.activity_logger.log_activity(
                f"Generated summary for {summary['game_display_name']}",
                "analysis",
                {"total_draws": len(data), "game": game},
                "data_manager"
            )
            # Date range
            if 'date' in data.columns:
                try:
                    dates = pd.to_datetime(data['date'], errors='coerce')
                    valid_dates = dates.dropna()
                    if not valid_dates.empty:
                        summary['date_range'] = f"{valid_dates.min().strftime('%Y-%m-%d')} to {valid_dates.max().strftime('%Y-%m-%d')}"
                except Exception as e:
                    summary['date_range'] = 'Error'
            # Hot/cold numbers
            all_numbers = [n for lst in data['numbers_list'] if isinstance(lst, list) for n in lst]
            if all_numbers:
                from collections import Counter
                counter = Counter(all_numbers)
                most_common = [str(n) for n, _ in counter.most_common(6)]
                least_common = [str(n) for n, _ in counter.most_common()[-6:]]
                summary['hot_numbers'] = ', '.join(most_common) if most_common else 'No data'
                summary['cold_numbers'] = ', '.join(least_common) if least_common else 'No data'
            summary['activity_messages'].append(f"📊 Statistics for {summary['game_display_name']}")
            summary['activity_messages'].append(f"📈 Based on all {summary['total_draws']:,} draws ({summary['date_range']})")
            summary['activity_messages'].append(f"🔥 Hot numbers for {summary['game_display_name']}: {summary['hot_numbers']}")
            summary['activity_messages'].append(f"❄️ Cold numbers for {summary['game_display_name']}: {summary['cold_numbers']}")
        else:
            summary['activity_messages'].append("⚠️ Errror loading data. Please try refreshing.")
        return summary
    """
    Unified data manager that combines PDF archives (live scraping removed)

    This class maintains the same interface that the GUI expects while
    internally coordinating data from multiple sources.
    """

    def __init__(self, data_dir: str = "data"):
        """Initialize the data manager"""
        self.data_dir = data_dir
        self.processed_dir = os.path.join(data_dir, "processed")
        self.logger = logging.getLogger(__name__)

        # Initialize activity logger
        from core.activity_logger import ActivityLogger
        self.activity_logger = ActivityLogger.get_instance()

        # Initialize data sources
        self.pdf_parser = WCLCPDFParser(data_dir)

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
                age = datetime.now() - cache_entry['timestamp']
                self.activity_logger.log_activity(
                    f"Using cached data for {game}",
                    "data",
                    {"age_minutes": age.total_seconds() / 60, "cache_key": cache_key},
                    "data_manager"
                )
                return cache_entry['data']

        self.logger.info(f"Loading data for game: {game}, full_refresh: {full_refresh}")

        # Load from all sources
        pdf_data = self._load_pdf_data(game)
        csv_data = self._load_csv_data(game) 

        # Combine sources (no live scraping)
        combined_data = self._combine_data_sources(game, pdf_data, csv_data, pd.DataFrame())

        # Ensure proper date format
        if 'date' in combined_data.columns:
            # Standardize date format to YYYY-MM-DD
            combined_data['date'] = pd.to_datetime(combined_data['date'], errors='coerce').dt.strftime('%Y-%m-%d')
            # Remove rows with invalid dates
            combined_data = combined_data.dropna(subset=['date'])        # CRITICAL: Add numbers_list normalization to fix analytics
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
        # Validate and normalize all draw records to canonical schema before returning
        try:
            from utils.data_validation import validate_draw_record
            import pandas as pd
            combined_data = combined_data.apply(lambda row: validate_draw_record(row.to_dict()), axis=1)
            combined_data = pd.DataFrame(list(combined_data))
        except Exception as e:
            self.logger.error(f"Error validating draw records: {e}")
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


    def _scrape_recent_data(self, game: str) -> pd.DataFrame:
        """Legacy: always returns empty DataFrame (scraping removed)"""
        return pd.DataFrame()

    def _combine_data_sources(self, game: str, pdf_data: pd.DataFrame, 
                             csv_data: pd.DataFrame, _: pd.DataFrame) -> pd.DataFrame:
        """Combine data from PDF and CSV only, resolving conflicts"""
        combined = pd.DataFrame()

        # Add PDF data (most authoritative for historical data)
        if not pdf_data.empty:
            combined = pdf_data.copy()

        # Add CSV data (for dates not in PDF)
        if not csv_data.empty:
            if combined.empty:
                combined = csv_data.copy()
            else:
                if 'date' in combined.columns:
                    combined_dates = set(combined['date'])
                    if 'date' in csv_data.columns:
                        new_csv_data = csv_data[~csv_data['date'].isin(combined_dates)]
                        if not new_csv_data.empty:
                            combined = pd.concat([combined, new_csv_data], ignore_index=True)

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
        """Refresh recent data (reload PDF/CSV only)"""
        try:
            self.logger.info(f"Refreshing recent data for {game}")
            data = self.load_game_data(game, full_refresh=True)
            cache_key = f"{game}_data"
            self._cache[cache_key] = data
            self._last_refresh[cache_key] = datetime.now()
            return data
        except Exception as e:
            self.logger.error(f"Error refreshing recent data: {e}")
            return pd.DataFrame()

    def get_recent_draws(self, game: str, count: int = 10) -> List[Dict]:
        """Get the most recent draws for a game"""
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
                numbers_str = draw['numbers']
                if isinstance(numbers_str, str):
                    pass
                         