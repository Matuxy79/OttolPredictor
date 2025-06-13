"""
Wrapper around existing wclc_scraper.py for recent data only
"""

from wclc_scraper import WCLCScraper, run_scraper
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import pandas as pd

class LiveResultsScraper:
    """
    Wrapper around existing WCLCScraper that focuses on recent data only
    
    This class provides a more efficient interface for getting only recent
    lottery data, avoiding the full historical scrape when not needed.
    """
    
    def __init__(self):
        """Initialize the scraper with the existing WCLCScraper"""
        self.scraper = WCLCScraper()
        self.logger = logging.getLogger(__name__)
    
    def get_recent_draws(self, game: str, since_date: Optional[str] = None, max_days: int = 30) -> List[Dict]:
        """
        Get recent draws for a specific game
        
        Args:
            game: Game code ('649', 'max', etc.)
            since_date: Only get draws since this date (format: YYYY-MM-DD)
            max_days: Maximum number of days to look back
            
        Returns:
            List of draw dictionaries in the same format as the current scraper
        """
        self.logger.info(f"Getting recent draws for {game} (max_days={max_days})")
        
        try:
            # Get URL for the game
            url = self.scraper.get_game_url(game)
            
            # Fetch HTML
            html = self.scraper.fetch_html_with_retry(url)
            
            # Parse draws
            draws = self.scraper._parse_draws_by_game(html, game)
            
            if not draws:
                self.logger.warning(f"No draws found for {game}")
                return []
            
            # Filter by date if specified
            if since_date:
                try:
                    since_date_obj = datetime.strptime(since_date, "%Y-%m-%d")
                    filtered_draws = []
                    
                    for draw in draws:
                        try:
                            draw_date = draw.get('date', '')
                            draw_date_obj = datetime.strptime(draw_date, "%Y-%m-%d")
                            
                            if draw_date_obj >= since_date_obj:
                                filtered_draws.append(draw)
                        except Exception as e:
                            self.logger.warning(f"Error parsing draw date: {e}")
                            # Include draws with unparseable dates just to be safe
                            filtered_draws.append(draw)
                    
                    draws = filtered_draws
                except Exception as e:
                    self.logger.warning(f"Error filtering by date: {e}")
            
            # Filter by max_days
            if max_days > 0:
                cutoff_date = datetime.now() - timedelta(days=max_days)
                filtered_draws = []
                
                for draw in draws:
                    try:
                        draw_date = draw.get('date', '')
                        draw_date_obj = datetime.strptime(draw_date, "%Y-%m-%d")
                        
                        if draw_date_obj >= cutoff_date:
                            filtered_draws.append(draw)
                    except Exception as e:
                        self.logger.warning(f"Error filtering by max_days: {e}")
                        # Include draws with unparseable dates just to be safe
                        filtered_draws.append(draw)
                
                draws = filtered_draws
            
            self.logger.info(f"Found {len(draws)} recent draws for {game}")
            return draws
        
        except Exception as e:
            self.logger.error(f"Error getting recent draws: {e}")
            return []
    
    def get_latest_draw_only(self, game: str) -> Optional[Dict]:
        """
        Get just the most recent draw for GUI refresh
        
        Args:
            game: Game code ('649', 'max', etc.)
            
        Returns:
            Dictionary with the most recent draw, or None if no draws found
        """
        self.logger.info(f"Getting latest draw for {game}")
        
        try:
            # Get recent draws (limit to 5 to ensure we get the latest)
            draws = self.get_recent_draws(game, max_days=7)
            
            if not draws:
                self.logger.warning(f"No draws found for {game}")
                return None
            
            # Sort by date (newest first)
            sorted_draws = sorted(
                draws,
                key=lambda x: datetime.strptime(x.get('date', '1900-01-01'), "%Y-%m-%d"),
                reverse=True
            )
            
            latest_draw = sorted_draws[0]
            self.logger.info(f"Latest draw for {game}: {latest_draw.get('date', 'Unknown date')}")
            
            return latest_draw
        
        except Exception as e:
            self.logger.error(f"Error getting latest draw: {e}")
            return None
    
    def convert_game_name(self, game: str) -> str:
        """
        Convert game names to match existing scraper format
        
        Args:
            game: Game name or code
            
        Returns:
            Standardized game code for the scraper
        """
        game_lower = game.lower()
        
        if '649' in game_lower:
            if 'western' in game_lower:
                return 'western649'
            else:
                return '649'
        
        elif 'max' in game_lower:
            if 'western' in game_lower:
                return 'westernmax'
            else:
                return 'max'
        
        elif 'grand' in game_lower or 'daily' in game_lower:
            return 'dailygrand'
        
        # Default to original value
        return game
    
    def save_to_csv(self, draws: List[Dict], filename: Optional[str] = None) -> str:
        """
        Save draws to CSV file
        
        Args:
            draws: List of draw dictionaries
            filename: Optional filename (default: auto-generated)
            
        Returns:
            Path to the saved file
        """
        if not draws:
            self.logger.warning("No draws to save")
            return ""
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame(draws)
            
            # Generate filename if not provided
            if not filename:
                game = draws[0].get('game', 'unknown').lower().replace(' ', '_')
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{game}_recent_{timestamp}.csv"
            
            # Save to CSV
            df.to_csv(filename, index=False)
            self.logger.info(f"Saved {len(draws)} draws to {filename}")
            
            return filename
        
        except Exception as e:
            self.logger.error(f"Error saving to CSV: {e}")
            return ""
    
    def batch_scrape_recent(self, games: List[str], max_days: int = 30) -> Dict[str, List[Dict]]:
        """
        Batch scrape recent data for multiple games
        
        Args:
            games: List of game codes
            max_days: Maximum number of days to look back
            
        Returns:
            Dictionary mapping game codes to lists of draws
        """
        self.logger.info(f"Batch scraping recent data for {len(games)} games")
        
        results = {}
        
        for game in games:
            try:
                # Convert game name if needed
                game_code = self.convert_game_name(game)
                
                # Get recent draws
                draws = self.get_recent_draws(game_code, max_days=max_days)
                
                results[game_code] = draws
                
                self.logger.info(f"Found {len(draws)} recent draws for {game_code}")
            
            except Exception as e:
                self.logger.error(f"Error scraping {game}: {e}")
                results[game] = []
        
        return results