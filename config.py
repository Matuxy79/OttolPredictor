"""
Centralized configuration management for Saskatoon Lotto Predictor
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional
import json

@dataclass
class GameConfig:
    """Configuration for a specific lottery game"""
    name: str
    display_name: str
    url: str
    number_count: int
    number_max: int
    has_bonus: bool
    has_gold_ball: bool = False
    bonus_max: Optional[int] = None

class AppConfig:
    """Application-wide configuration"""
    
    # Game configurations
    GAMES = {
        '649': GameConfig(
            name='649',
            display_name='Lotto 6/49',
            url='https://www.wclc.com/winning-numbers/lotto-649-extra.htm',
            number_count=6,
            number_max=49,
            has_bonus=True,
            has_gold_ball=True,
            bonus_max=49
        ),
        'max': GameConfig(
            name='max',
            display_name='Lotto Max',
            url='https://www.wclc.com/winning-numbers/lotto-max-extra.htm',
            number_count=7,
            number_max=50,
            has_bonus=True,
            bonus_max=50
        ),
        'western649': GameConfig(
            name='western649',
            display_name='Western 649',
            url='https://www.wclc.com/winning-numbers/western-649-extra.htm',
            number_count=6,
            number_max=49,
            has_bonus=True,
            bonus_max=49
        ),
        'westernmax': GameConfig(
            name='westernmax',
            display_name='Western Max',
            url='https://www.wclc.com/winning-numbers/western-max-extra.htm',
            number_count=7,
            number_max=50,
            has_bonus=True,
            bonus_max=50
        ),
        'dailygrand': GameConfig(
            name='dailygrand',
            display_name='Daily Grand',
            url='https://www.wclc.com/winning-numbers/daily-grand-extra.htm',
            number_count=5,
            number_max=49,
            has_bonus=True,
            bonus_max=49
        )
    }
    
    # Directories
    DATA_DIR = os.getenv('LOTTO_DATA_DIR', 'data')
    LOG_DIR = os.getenv('LOTTO_LOG_DIR', 'logs')
    
    # Scraping settings
    SCRAPER_TIMEOUT = int(os.getenv('LOTTO_SCRAPER_TIMEOUT', '30'))
    SCRAPER_RETRIES = int(os.getenv('LOTTO_SCRAPER_RETRIES', '3'))
    BATCH_DELAY = int(os.getenv('LOTTO_BATCH_DELAY', '1'))  # seconds between requests
    
    # HTTP Headers
    HTTP_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-CA,en-US;q=0.7,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Referer': 'https://www.wclc.com/'
    }
    
    # HTML Validation
    LOTTERY_INDICATORS = [
        'winning numbers', 'draw', 'lotto', 'jackpot', 'bonus',
        'wclc', 'lottery', 'numbers', 'draw date', 'past winning numbers'
    ]
    
    # GUI settings
    WINDOW_SIZE = (1200, 800)
    THEME = 'light'
    
    @classmethod
    def get_game_config(cls, game: str) -> Optional[GameConfig]:
        """Get configuration for a specific game"""
        return cls.GAMES.get(game)
    
    @classmethod
    def get_supported_games(cls) -> List[str]:
        """Get list of supported game codes"""
        return list(cls.GAMES.keys())
    
    @classmethod
    def get_game_display_name(cls, game: str) -> str:
        """Get display name for a game"""
        game_config = cls.get_game_config(game)
        return game_config.display_name if game_config else game
    
    @classmethod
    def get_game_url(cls, game: str) -> Optional[str]:
        """Get URL for a specific game"""
        game_config = cls.get_game_config(game)
        return game_config.url if game_config else None