"""
Data schema definitions and validation for lottery data
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import pandas as pd
from config import AppConfig

@dataclass
class DrawRecord:
    """Standardized lottery draw record"""
    game: str
    date: str
    date_parsed: Optional[datetime]
    numbers: List[int]
    bonus: Optional[int] = None
    gold_ball: Optional[int] = None
    scraped_at: Optional[datetime] = None
    source: str = 'wclc'
    
    def __post_init__(self):
        """Initialize default values and convert types"""
        if self.scraped_at is None:
            self.scraped_at = datetime.now()
        
        # Ensure numbers is a list of integers
        if isinstance(self.numbers, str):
            self.numbers = self._parse_numbers(self.numbers)
    
    def _parse_numbers(self, numbers_str: str) -> List[int]:
        """Parse number string into list of integers"""
        try:
            if not numbers_str or pd.isna(numbers_str):
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
                    numbers.append(num)
                except ValueError:
                    continue
            
            return sorted(numbers)
        except:
            return []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DataFrame"""
        return {
            'game': self.game,
            'date': self.date,
            'date_parsed': self.date_parsed.isoformat() if self.date_parsed else None,
            'numbers': ','.join(map(str, self.numbers)),
            'bonus': self.bonus,
            'gold_ball': self.gold_ball,
            'scraped_at': self.scraped_at.isoformat() if self.scraped_at else None,
            'source': self.source
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DrawRecord':
        """Create from dictionary"""
        numbers = []
        if 'numbers' in data:
            if isinstance(data['numbers'], list):
                numbers = data['numbers']
            else:
                try:
                    numbers = [int(x.strip()) for x in str(data['numbers']).split(',') if x.strip()]
                except:
                    numbers = []
        
        # Parse dates if they're strings
        date_parsed = data.get('date_parsed')
        if isinstance(date_parsed, str):
            try:
                date_parsed = pd.to_datetime(date_parsed)
            except:
                date_parsed = None
        
        scraped_at = data.get('scraped_at')
        if isinstance(scraped_at, str):
            try:
                scraped_at = pd.to_datetime(scraped_at)
            except:
                scraped_at = None
        
        return cls(
            game=data.get('game', ''),
            date=data.get('date', ''),
            date_parsed=date_parsed,
            numbers=numbers,
            bonus=data.get('bonus'),
            gold_ball=data.get('gold_ball'),
            scraped_at=scraped_at or datetime.now(),
            source=data.get('source', 'unknown')
        )


class DataValidator:
    """Validates lottery data integrity"""
    
    @staticmethod
    def validate_draw_record(record: Union[DrawRecord, Dict], game_code: str) -> List[str]:
        """
        Validate a single draw record
        
        Args:
            record: DrawRecord object or dictionary to validate
            game_code: Game code to use for validation rules
            
        Returns:

            List of error messages, empty if valid
        if not date_parsed:
            date_str = data.get('date', None)
            if date_str:
                try:
                    date_parsed = pd.to_datetime(date_str, errors='coerce')
                    if pd.isna(date_parsed):
                        date_parsed = None
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Failed to parse date '{date_str}': {e}")
                    date_parsed = None

        # If still missing, log a warning
        if not date_parsed:
            import logging
            logging.getLogger(__name__).warning(f"DrawRecord missing valid date_parsed for data: {data}")
        """
        errors = []
        
        # Convert dict to DrawRecord if needed
        if isinstance(record, dict):
            record = DrawRecord.from_dict(record)
        
        # Get game configuration
        game_config = AppConfig.get_game_config(game_code)
        if not game_config:
            return [f"Unknown game code: {game_code}"]
        
        # Check number count
        if len(record.numbers) != game_config.number_count:
            errors.append(f"Expected {game_config.number_count} numbers, got {len(record.numbers)}")
        
        # Check number ranges
        for num in record.numbers:
            if not (1 <= num <= game_config.number_max):
                errors.append(f"Number {num} out of range (1-{game_config.number_max})")
        
        # Check bonus
        if game_config.has_bonus and record.bonus is not None:
            if not (1 <= record.bonus <= (game_config.bonus_max or game_config.number_max)):
                errors.append(f"Bonus {record.bonus} out of range")
        
        # Check gold ball (specific to 649)
        if game_code == '649' and record.gold_ball is not None:
            if not (1 <= record.gold_ball <= game_config.number_max):
                errors.append(f"Gold ball {record.gold_ball} out of range")
        
        return errors
    
    @staticmethod
    def validate_draw_records(records: List[Union[DrawRecord, Dict]], game_code: str) -> Dict[int, List[str]]:
        """
        Validate multiple draw records
        
        Args:
            records: List of DrawRecord objects or dictionaries to validate
            game_code: Game code to use for validation rules
            
        Returns:
            Dictionary mapping record index to list of error messages
        """
        errors = {}
        for i, record in enumerate(records):
            record_errors = DataValidator.validate_draw_record(record, game_code)
            if record_errors:
                errors[i] = record_errors
        return errors