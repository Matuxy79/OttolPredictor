"""
Data Manager - Clean API for lottery data access
Provides unified interface for GUI and prediction modules
"""

import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class LotteryDataManager:
    """Centralized data access and management for lottery data"""
    
    SUPPORTED_GAMES = ['649', 'max', 'western649', 'westernmax', 'dailygrand']
    
    def __init__(self, data_directory: str = 'data'):
        """
        Initialize data manager
        
        Args:
            data_directory: Directory containing CSV/SQLite files
        """
        self.data_dir = data_directory
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
        if game not in self.SUPPORTED_GAMES:
            raise ValueError(f"Unsupported game: {game}. Supported: {self.SUPPORTED_GAMES}")
        
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
        """Load data from CSV files"""
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
                df = pd.read_csv(csv_file)
                all_data.append(df)
                logger.debug(f"Loaded CSV: {csv_file} ({len(df)} rows)")
            except Exception as e:
                logger.warning(f"Error loading CSV {csv_file}: {e}")
        
        if all_data:
            combined = pd.concat(all_data, ignore_index=True)
            return combined.drop_duplicates()
        
        return pd.DataFrame()
    
    def _load_from_sqlite(self, game: str) -> pd.DataFrame:
        """Load data from SQLite database"""
        db_files = [f"wclc_{game}.db", f"{game}_results.db", "lottery_data.db"]
        
        for db_file in db_files:
            db_path = os.path.join(self.data_dir, db_file)
            if os.path.exists(db_path):
                try:
                    conn = sqlite3.connect(db_path)
                    # Try common table names
                    table_names = ['lottery_draws', 'draws', game, f"{game}_draws"]
                    
                    for table in table_names:
                        try:
                            query = f"SELECT * FROM {table} WHERE game LIKE '%{game}%' OR game LIKE '%{game.replace('649', '649')}%'"
                            df = pd.read_sql_query(query, conn)
                            if not df.empty:
                                conn.close()
                                logger.debug(f"Loaded from SQLite: {db_file}.{table} ({len(df)} rows)")
                                return df
                        except:
                            continue
                    
                    conn.close()
                except Exception as e:
                    logger.warning(f"Error loading SQLite {db_file}: {e}")
        
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
    
    def _parse_numbers(self, numbers_str: str) -> List[int]:
        """Parse number string into list of integers"""
        try:
            if pd.isna(numbers_str):
                return []
            
            # Handle different formats: "1,2,3,4,5,6" or "1 2 3 4 5 6"
            numbers_str = str(numbers_str).strip()
            
            if ',' in numbers_str:
                parts = numbers_str.split(',')
            else:
                parts = numbers_str.split()
            
            numbers = []
            for part in parts:
                try:
                    num = int(part.strip())
                    if 1 <= num <= 50:  # Valid lottery number range
                        numbers.append(num)
                except ValueError:
                    continue
            
            return sorted(numbers)
        except:
            return []
    
    def get_game_summary(self, game: str) -> Dict:
        """Get summary statistics for a game"""
        data = self.load_game_data(game)
        
        if data.empty:
            return {
                'game': game,
                'total_draws': 0,
                'date_range': 'No data',
                'last_updated': 'Never'
            }
        
        summary = {
            'game': game,
            'total_draws': len(data),
            'date_range': self._get_date_range(data),
            'last_updated': self._get_last_updated(data),
            'most_frequent_numbers': self._get_hot_numbers(data, top_n=6),
            'least_frequent_numbers': self._get_cold_numbers(data, top_n=6),
            'recent_draws': len(data[data['date_parsed'] > datetime.now() - timedelta(days=30)]) if 'date_parsed' in data.columns else 0
        }
        
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
        for game in self.SUPPORTED_GAMES:
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
    
    def get_recent_draws(self, game: str, days: int = 30) -> pd.DataFrame:
        """Get draws from the last N days"""
        data = self.load_game_data(game)
        
        if 'date_parsed' not in data.columns:
            return data.head(10)  # Fallback to first 10 draws
        
        cutoff_date = datetime.now() - timedelta(days=days)
        recent = data[data['date_parsed'] > cutoff_date]
        
        return recent


# Convenience function for GUI
def get_data_manager() -> LotteryDataManager:
    """Get a shared instance of the data manager"""
    if not hasattr(get_data_manager, '_instance'):
        get_data_manager._instance = LotteryDataManager()
    return get_data_manager._instance