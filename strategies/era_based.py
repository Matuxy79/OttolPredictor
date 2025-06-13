"""Era-based weighting - different weights for different game periods"""

from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# Define eras for different games
LOTTO_649_ERAS = [
    {
        'name': 'Classic Era',
        'start_date': '1982-06-12',
        'end_date': '2013-09-14',
        'weight': 0.3,
        'description': 'Original Lotto 6/49 format'
    },
    {
        'name': 'Guaranteed Prize Era',
        'start_date': '2013-09-15',
        'end_date': '2022-09-09',
        'weight': 0.7,
        'description': 'Added guaranteed $1M prize'
    },
    {
        'name': 'Gold Ball Era',
        'start_date': '2022-09-10',
        'end_date': None,  # None means "to present"
        'weight': 1.0,
        'description': 'New format with Gold Ball Jackpot'
    }
]

LOTTO_MAX_ERAS = [
    {
        'name': 'Original Era',
        'start_date': '2009-09-25',
        'end_date': '2019-05-13',
        'weight': 0.4,
        'description': 'Original Lotto Max with 7/49 format'
    },
    {
        'name': 'Expanded Era',
        'start_date': '2019-05-14',
        'end_date': None,  # None means "to present"
        'weight': 1.0,
        'description': 'New format with 7/50 and higher jackpots'
    }
]

def era_weighted_frequency(draws: List[Dict], pick_count: int = 6) -> List[int]:
    """
    Era-based weighting for lottery number frequency analysis
    
    Args:
        draws: List of draw dictionaries with 'numbers' and 'date' fields
        pick_count: Number of numbers to pick (6 for 649, 7 for Max)
        
    Returns:
        List of top N most frequent numbers weighted by era
    """
    # Validate input
    if not draws:
        return []
    
    # Determine game type from first draw
    game_type = _determine_game_type(draws)
    
    # Get appropriate eras for the game
    eras = _get_eras_for_game(game_type)
    
    if not eras:
        # Fallback to uniform frequency if no eras defined
        logger.warning(f"No eras defined for game type {game_type}, falling back to uniform weighting")
        from strategies.uniform import uniform_frequency
        return uniform_frequency(draws, pick_count)
    
    # Calculate weighted frequencies
    weighted_counts = defaultdict(float)
    total_weights = 0.0
    
    for draw in draws:
        # Get date
        date_str = draw.get('date', '')
        if not date_str:
            continue
        
        try:
            date_obj = _parse_date(date_str)
            if not date_obj:
                continue
            
            # Determine which era this draw belongs to
            era = _get_era_for_date(date_obj, eras)
            if not era:
                continue
            
            # Get weight for this era
            weight = era.get('weight', 1.0)
            total_weights += weight
            
            # Get numbers and add weighted counts
            numbers = _extract_numbers(draw)
            for num in numbers:
                weighted_counts[num] += weight
                
        except Exception as e:
            logger.warning(f"Error processing draw {date_str}: {e}")
            continue
    
    # Sort numbers by weighted frequency
    sorted_numbers = sorted(weighted_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Return top N numbers
    return [num for num, _ in sorted_numbers[:pick_count]]

def era_weighted_frequency_with_stats(draws: List[Dict], pick_count: int = 6) -> Dict:
    """
    Enhanced era-based frequency analysis with statistics
    
    Args:
        draws: List of draw dictionaries with 'numbers' and 'date' fields
        pick_count: Number of numbers to pick (6 for 649, 7 for Max)
        
    Returns:
        Dictionary with predicted numbers and statistics
    """
    # Validate input
    if not draws:
        return {
            'numbers': [],
            'stats': {
                'method': 'era_weighted',
                'confidence': 0.0,
                'sample_size': 0
            }
        }
    
    # Determine game type from first draw
    game_type = _determine_game_type(draws)
    
    # Get appropriate eras for the game
    eras = _get_eras_for_game(game_type)
    
    if not eras:
        # Fallback to uniform frequency if no eras defined
        logger.warning(f"No eras defined for game type {game_type}, falling back to uniform weighting")
        from strategies.uniform import uniform_frequency_with_stats
        return uniform_frequency_with_stats(draws, pick_count)
    
    # Calculate weighted frequencies
    weighted_counts = defaultdict(float)
    total_weights = 0.0
    processed_draws = 0
    
    # Track draws per era for statistics
    era_counts = {era['name']: 0 for era in eras}
    
    for draw in draws:
        # Get date
        date_str = draw.get('date', '')
        if not date_str:
            continue
        
        try:
            date_obj = _parse_date(date_str)
            if not date_obj:
                continue
            
            # Determine which era this draw belongs to
            era = _get_era_for_date(date_obj, eras)
            if not era:
                continue
            
            # Get weight for this era
            weight = era.get('weight', 1.0)
            total_weights += weight
            
            # Track era counts
            era_counts[era['name']] += 1
            
            # Get numbers and add weighted counts
            numbers = _extract_numbers(draw)
            for num in numbers:
                weighted_counts[num] += weight
            
            processed_draws += 1
                
        except Exception as e:
            logger.warning(f"Error processing draw {date_str}: {e}")
            continue
    
    # Sort numbers by weighted frequency
    sorted_numbers = sorted(weighted_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Get top numbers
    top_numbers = [num for num, _ in sorted_numbers[:pick_count]]
    
    # Calculate confidence based on data distribution across eras
    # More data in recent eras = higher confidence
    recent_era_weight = eras[-1]['weight'] if eras else 1.0
    recent_era_count = era_counts[eras[-1]['name']] if eras else 0
    
    # Calculate confidence factors
    data_factor = min(1.0, processed_draws / 100)  # More data = higher confidence
    recency_factor = min(1.0, recent_era_count / 20)  # More recent data = higher confidence
    era_weight_factor = recent_era_weight  # Higher weight on recent era = higher confidence
    
    # Combine factors for overall confidence
    confidence = min(0.9, data_factor * 0.5 + recency_factor * 0.3 + era_weight_factor * 0.2)
    
    # Calculate weighted frequencies for top numbers
    top_weighted_freqs = [count for _, count in sorted_numbers[:pick_count]]
    avg_weighted_freq = sum(top_weighted_freqs) / len(top_weighted_freqs) if top_weighted_freqs else 0
    
    return {
        'numbers': top_numbers,
        'stats': {
            'method': 'era_weighted',
            'confidence': confidence,
            'sample_size': processed_draws,
            'era_distribution': era_counts,
            'game_type': game_type,
            'avg_weighted_freq': avg_weighted_freq,
            'weighted_frequencies': {num: count for num, count in sorted_numbers[:20]},  # Top 20
            'eras_used': [era['name'] for era in eras]
        }
    }

def _determine_game_type(draws: List[Dict]) -> str:
    """Determine the game type from a list of draws"""
    # Try to get game from first draw
    if draws and 'game' in draws[0]:
        game = draws[0]['game'].lower()
        if '649' in game:
            return '649'
        elif 'max' in game:
            return 'max'
    
    # Try to infer from number count in first draw with numbers
    for draw in draws:
        numbers = _extract_numbers(draw)
        if numbers:
            if len(numbers) == 7:
                return 'max'
            elif len(numbers) == 6:
                return '649'
            break
    
    # Default to 649
    return '649'

def _get_eras_for_game(game_type: str) -> List[Dict]:
    """Get the appropriate eras for a game type"""
    if game_type == '649':
        return LOTTO_649_ERAS
    elif game_type == 'max':
        return LOTTO_MAX_ERAS
    else:
        return []

def _get_era_for_date(date: datetime, eras: List[Dict]) -> Optional[Dict]:
    """Determine which era a date belongs to"""
    for era in eras:
        start_date = _parse_date(era['start_date'])
        end_date = _parse_date(era['end_date']) if era['end_date'] else datetime.now()
        
        if start_date <= date <= end_date:
            return era
    
    return None

def _parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string with multiple format support"""
    if not date_str:
        return None
        
    formats = [
        '%Y-%m-%d',      # 2024-06-15
        '%Y/%m/%d',      # 2024/06/15
        '%m/%d/%Y',      # 06/15/2024
        '%d %b %Y',      # 15 Jun 2024
        '%b %d, %Y',     # Jun 15, 2024
        '%B %d, %Y',     # June 15, 2024
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None

def _extract_numbers(draw: Dict) -> List[int]:
    """Extract numbers from a draw with different format handling"""
    numbers = draw.get('numbers', [])
    
    # Handle different formats of numbers field
    if isinstance(numbers, str):
        # Handle string representation of list
        if numbers.startswith('[') and numbers.endswith(']'):
            try:
                # Remove brackets and split by comma
                nums_str = numbers.strip('[]')
                # Handle various formats: "[1, 2, 3]" or "[1,2,3]"
                return [int(n.strip()) for n in nums_str.split(',') if n.strip()]
            except Exception:
                return []
    elif isinstance(numbers, list):
        return numbers
    
    return []