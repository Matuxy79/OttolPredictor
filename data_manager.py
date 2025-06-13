"""
Data Manager - Clean API for lottery data access
Provides unified interface for GUI and prediction modules
"""

import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from logging_config import get_logger
from config import AppConfig
from schema import DrawRecord, DataValidator

logger = get_logger(__name__)

class LotteryDataManager:
    """Centralized data access and management for lottery data"""

    def __init__(self, data_directory: str = None):
        """
        Initialize data manager

        Args:
            data_directory: Directory containing CSV/SQLite files (defaults to AppConfig.DATA_DIR)
        """
        self.data_dir = data_directory or AppConfig.DATA_DIR
        self.ensure_data_directory()
        self._cache = {}  # Simple caching for performance

    def ensure_data_directory(self):
        """Create data directory if it doesn't exist"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            logger.info(f"Created data directory: {self.data_dir}")

    def load_game_data(self, game: str, refresh_cache: bool = False) -> pd.DataFrame:
        """
        Load data for a specific game

        Args:
            game: Game type (649, max, etc.)
            refresh_cache: Force reload from file

        Returns:
            DataFrame with lottery draw data
        """
        supported_games = AppConfig.get_supported_games()
        if game not in supported_games:
            raise ValueError(f"Unsupported game: {game}. Supported: {supported_games}")

        cache_key = f"game_{game}"

        # Return cached data if available and not refreshing
        if not refresh_cache and cache_key in self._cache:
            logger.debug(f"Returning cached data for {game}")
            return self._cache[cache_key]

        # Try to load from CSV files first
        data = self._load_from_csv(game)

        # If no CSV, try SQLite
        if data.empty:
            data = self._load_from_sqlite(game)

        # Process and clean the data
        if not data.empty:
            data = self._clean_and_process_data(data, game)
            self._cache[cache_key] = data
            logger.info(f"Loaded {len(data)} draws for {game}")
        else:
            logger.warning(f"No data found for game: {game}")

        return data

    def _load_from_csv(self, game: str) -> pd.DataFrame:
        """Load data from CSV files with enhanced format handling"""
        # Look for CSV files matching the game
        csv_patterns = [
            f"*{game}*.csv",
            f"wclc_{game}*.csv",
            f"{game}_results*.csv"
        ]

        csv_files = []
        for pattern in csv_patterns:
            import glob
            files = glob.glob(os.path.join(self.data_dir, pattern))
            csv_files.extend(files)

        # Also check current directory for CSV files
        for pattern in csv_patterns:
            files = glob.glob(pattern)
            csv_files.extend(files)

        if not csv_files:
            return pd.DataFrame()

        # Load and combine all CSV files
        all_data = []
        for csv_file in csv_files:
            try:
                # Read CSV with converters to handle different formats
                df = pd.read_csv(csv_file)

                # Process the numbers column if it exists
                if 'numbers' in df.columns:
                    # Apply the _parse_numbers function to handle different formats
                    df['numbers_list'] = df['numbers'].apply(self._parse_numbers)

                # Process date column if it exists
                if 'date' in df.columns:
                    # Try to parse dates, but don't fail if some are invalid
                    try:
                        df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

                        # For rows where date parsing failed, try to use scraped_at as fallback
                        if 'scraped_at' in df.columns:
                            mask = df['date_parsed'].isna()
                            if mask.any():
                                # Extract date part from scraped_at
                                df.loc[mask, 'date_parsed'] = pd.to_datetime(
                                    df.loc[mask, 'scraped_at'].apply(
                                        lambda x: x.split('T')[0] if isinstance(x, str) and 'T' in x else x
                                    ), 
                                    errors='coerce'
                                )
                    except Exception as e:
                        logger.warning(f"Error parsing dates in {csv_file}: {e}")

                all_data.append(df)
                logger.debug(f"Loaded CSV: {csv_file} ({len(df)} rows)")
            except Exception as e:
                logger.warning(f"Error loading CSV {csv_file}: {e}")

        if all_data:
            combined = pd.concat(all_data, ignore_index=True)
            return combined.drop_duplicates()

        return pd.DataFrame()

    def _load_from_sqlite(self, game: str) -> pd.DataFrame:
        """Load data from SQLite database with JSON handling"""
        # Check both data directory and current directory
        db_files = []

        # Common database filenames
        db_patterns = [
            f"wclc_{game}*.db", 
            f"{game}_results*.db", 
            "lottery_data.db"
        ]

        # Search in data directory
        for pattern in db_patterns:
            import glob
            files = glob.glob(os.path.join(self.data_dir, pattern))
            db_files.extend(files)

        # Also check current directory
        for pattern in db_patterns:
            files = glob.glob(pattern)
            db_files.extend(files)

        if not db_files:
            logger.debug(f"No SQLite database files found for game {game}")
            return pd.DataFrame()

        # Try each database file
        for db_path in db_files:
            if os.path.exists(db_path):
                try:
                    conn = sqlite3.connect(db_path)
                    # Try common table names
                    table_names = ['lottery_draws', 'draws', game, f"{game}_draws"]

                    for table in table_names:
                        try:
                            # Get table schema to check columns
                            cursor = conn.cursor()
                            cursor.execute(f"PRAGMA table_info({table})")
                            columns = cursor.fetchall()

                            if not columns:
                                continue

                            # Check if table exists and has required columns
                            query = f"SELECT * FROM {table} WHERE game LIKE '%{game}%' OR game LIKE '%{game.upper()}%'"
                            df = pd.read_sql_query(query, conn)

                            if not df.empty:
                                # Process the numbers column if it exists (convert JSON to list)
                                if 'numbers' in df.columns:
                                    import json
                                    # Parse JSON strings to lists
                                    df['numbers_list'] = df['numbers'].apply(
                                        lambda x: self._parse_numbers(x)
                                    )

                                # Process dates
                                if 'date' in df.columns:
                                    df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

                                    # Use scraped_at as fallback for missing dates
                                    if 'scraped_at' in df.columns:
                                        mask = df['date_parsed'].isna()
                                        if mask.any():
                                            df.loc[mask, 'date_parsed'] = pd.to_datetime(
                                                df.loc[mask, 'scraped_at'].apply(
                                                    lambda x: x.split('T')[0] if isinstance(x, str) and 'T' in x else x
                                                ),
                                                errors='coerce'
                                            )

                                conn.close()
                                logger.info(f"Loaded from SQLite: {db_path}.{table} ({len(df)} rows)")
                                return df
                        except Exception as e:
                            logger.warning(f"Error querying table {table} in {db_path}: {e}")
                            continue

                    conn.close()
                except Exception as e:
                    logger.warning(f"Error loading SQLite {db_path}: {e}")

        logger.warning(f"No valid data found in any SQLite database for game {game}")
        return pd.DataFrame()

    def _clean_and_process_data(self, data: pd.DataFrame, game: str) -> pd.DataFrame:
        """Clean and process lottery data"""
        if data.empty:
            return data

        # Ensure required columns exist
        required_columns = ['game', 'date', 'numbers']
        for col in required_columns:
            if col not in data.columns:
                logger.error(f"Missing required column: {col}")
                return pd.DataFrame()

        # Clean and standardize data
        df = data.copy()

        # Parse dates
        try:
            df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')
        except:
            df['date_parsed'] = None

        # Parse numbers into lists
        df['numbers_list'] = df['numbers'].apply(self._parse_numbers)

        # Parse bonus numbers
        if 'bonus' in df.columns:
            df['bonus_int'] = pd.to_numeric(df['bonus'], errors='coerce')

        # Add derived columns
        df['draw_count'] = range(len(df))
        df['year'] = df['date_parsed'].dt.year if 'date_parsed' in df.columns else None
        df['month'] = df['date_parsed'].dt.month if 'date_parsed' in df.columns else None
        df['day_of_week'] = df['date_parsed'].dt.day_name() if 'date_parsed' in df.columns else None

        # Sort by date (newest first)
        if 'date_parsed' in df.columns and df['date_parsed'].notna().any():
            df = df.sort_values('date_parsed', ascending=False).reset_index(drop=True)

        # Remove duplicates
        df = df.drop_duplicates(subset=['game', 'date', 'numbers'], keep='first')

        logger.debug(f"Cleaned data for {game}: {len(df)} draws")
        return df

    def _parse_numbers(self, numbers_data) -> List[int]:
        """
        Parse numbers data into list of integers, handling multiple formats

        Args:
            numbers_data: Could be a list, JSON string, or string representation of a list

        Returns:
            List of integers
        """
        # If already a list, return it (possibly after converting elements to int)
        if isinstance(numbers_data, list):
            try:
                return [int(num) for num in numbers_data]
            except (ValueError, TypeError):
                logger.warning(f"Could not convert list elements to integers: {numbers_data}")
                return []

        # If it's None or empty, return empty list
        if not numbers_data:
            return []

        # If it's a string, try different parsing strategies
        if isinstance(numbers_data, str):
            # Remove quotes and whitespace from the string
            numbers_str = numbers_data.strip('\'"')

            # Try JSON parsing first (for SQLite stored data)
            try:
                import json
                parsed_list = json.loads(numbers_str)
                if isinstance(parsed_list, list):
                    return [int(num) for num in parsed_list]
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

            # Try ast.literal_eval for string representation of list like "[1, 2, 3]"
            if numbers_str.startswith('[') and numbers_str.endswith(']'):
                try:
                    import ast
                    parsed_list = ast.literal_eval(numbers_str)
                    if isinstance(parsed_list, list):
                        return [int(num) for num in parsed_list]
                except (SyntaxError, ValueError, TypeError):
                    # Fallback: manual parsing
                    try:
                        numbers_str = numbers_str.strip('[]')
                        return [int(x.strip()) for x in numbers_str.split(',') if x.strip()]
                    except (ValueError, TypeError):
                        pass

            # Try comma-separated values
            if ',' in numbers_str:
                try:
                    # Remove brackets if present
                    cleaned = numbers_str.strip('[]() ')
                    return [int(num.strip()) for num in cleaned.split(',') if num.strip()]
                except (ValueError, TypeError):
                    pass

        # If all parsing attempts fail, log warning and use DrawRecord as fallback
        logger.warning(f"Using fallback parsing for numbers: {numbers_data}")
        try:
            dummy_record = DrawRecord(game="", date="", date_parsed=None, numbers=numbers_data)
            return dummy_record.numbers
        except Exception as e:
            logger.error(f"Failed to parse numbers with fallback method: {e}")
            return []

    def get_game_summary(self, game: str) -> Dict:
        """Get summary statistics for a game"""
        data = self.load_game_data(game)

        # Create a complete summary dictionary with default values
        summary = {
            'game': game,
            'total_draws': 0,
            'date_range': 'No data',
            'last_updated': 'Never',
            'most_frequent_numbers': [],
            'least_frequent_numbers': [],
            'recent_draws': 0
        }

        if data.empty:
            logger.info(f"Returning empty summary for game: {game}")
            return summary

        # Update summary with actual data
        summary.update({
            'total_draws': len(data),
            'date_range': self._get_date_range(data),
            'last_updated': self._get_last_updated(data),
            'most_frequent_numbers': self._get_hot_numbers(data, top_n=6),
            'least_frequent_numbers': self._get_cold_numbers(data, top_n=6),
            'recent_draws': len(data[data['date_parsed'] > datetime.now() - timedelta(days=30)]) if 'date_parsed' in data.columns else 0
        })

        return summary

    def _get_date_range(self, data: pd.DataFrame) -> str:
        """Get human-readable date range"""
        if 'date_parsed' in data.columns and data['date_parsed'].notna().any():
            min_date = data['date_parsed'].min()
            max_date = data['date_parsed'].max()
            return f"{min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}"
        return "Unknown"

    def _get_last_updated(self, data: pd.DataFrame) -> str:
        """Get last update time"""
        if 'scraped_at' in data.columns and data['scraped_at'].notna().any():
            last_scraped = pd.to_datetime(data['scraped_at'].iloc[0])
            return last_scraped.strftime('%Y-%m-%d %H:%M')
        return "Unknown"

    def _get_hot_numbers(self, data: pd.DataFrame, top_n: int = 6) -> List[int]:
        """Get most frequently drawn numbers"""
        all_numbers = []
        for numbers_list in data['numbers_list']:
            all_numbers.extend(numbers_list)

        if not all_numbers:
            return []

        from collections import Counter
        counter = Counter(all_numbers)
        return [num for num, count in counter.most_common(top_n)]

    def _get_cold_numbers(self, data: pd.DataFrame, top_n: int = 6) -> List[int]:
        """Get least frequently drawn numbers"""
        all_numbers = []
        for numbers_list in data['numbers_list']:
            all_numbers.extend(numbers_list)

        if not all_numbers:
            return []

        from collections import Counter
        counter = Counter(all_numbers)
        return [num for num, count in counter.most_common()[-top_n:]]

    def get_all_games_summary(self) -> Dict[str, Dict]:
        """Get summary for all supported games"""
        summaries = {}
        for game in AppConfig.get_supported_games():
            summaries[game] = self.get_game_summary(game)
        return summaries

    def refresh_all_data(self):
        """Clear cache and reload all data"""
        self._cache.clear()
        logger.info("Data cache cleared - will reload from files")

    def get_number_frequency(self, game: str) -> Dict[int, int]:
        """Get frequency count for each number"""
        data = self.load_game_data(game)
        all_numbers = []

        for numbers_list in data['numbers_list']:
            all_numbers.extend(numbers_list)

        from collections import Counter
        return dict(Counter(all_numbers))

    def get_recent_draws(self, game: str, count: int = 10) -> List[Dict]:
        """
        Get recent draws with proper data structure

        Args:
            game: Game type (649, max, etc.)
            count: Number of recent draws to return

        Returns:
            List of draw dictionaries
        """
        try:
            # Load game data
            data = self.load_game_data(game)

            if data.empty:
                logger.warning(f"No data available for game {game}")
                return []

            # Get the most recent draws
            # If date_parsed is available, use it to sort
            if 'date_parsed' in data.columns and data['date_parsed'].notna().any():
                data = data.sort_values('date_parsed', ascending=False)

            # Limit to requested count
            recent_count = min(count, len(data))
            recent_draws = []

            # Convert to list of dictionaries
            for i in range(recent_count):
                row = data.iloc[i]

                # Extract numbers (either from numbers_list or by parsing numbers)
                if 'numbers_list' in row and row['numbers_list']:
                    numbers = row['numbers_list']
                else:
                    numbers = self._parse_numbers(row.get('numbers', []))

                # Get date (use scraped_at as fallback if date is missing)
                date = row.get('date', '')
                if not date and 'scraped_at' in row:
                    # Extract date part from ISO timestamp
                    scraped_at = row['scraped_at']
                    if scraped_at and isinstance(scraped_at, str):
                        date = scraped_at.split('T')[0]

                draw = {
                    'numbers': numbers,
                    'date': date or 'Unknown',
                    'game': game.upper(),
                    'draw_index': i
                }

                # Add bonus if available
                if 'bonus' in row and row['bonus']:
                    draw['bonus'] = row['bonus']

                recent_draws.append(draw)

            logger.info(f"Retrieved {len(recent_draws)} recent draws for {game}")
            return recent_draws

        except Exception as e:
            logger.error(f"Error getting recent draws for {game}: {e}")
            return []


# Convenience function for GUI
def get_data_manager() -> LotteryDataManager:
    """Get a shared instance of the data manager"""
    if not hasattr(get_data_manager, '_instance'):
        get_data_manager._instance = LotteryDataManager()
    return get_data_manager._instance
