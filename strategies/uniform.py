"""Simple uniform weighting - all historical draws equal"""

from typing import List, Dict, Union, Tuple
import pandas as pd
import numpy as np
from collections import Counter
import logging

# Set up logger
logger = logging.getLogger(__name__)

def uniform_frequency(data: Union[Dict, List[Dict]], pick_count: int = 6) -> List[int]:
    """Enhanced frequency-based prediction with robust data handling"""
    try:
        # Handle different input formats
        if isinstance(data, dict):
            # Data manager provides dict with 'numbers_list' key
            if 'numbers_list' in data:
                numbers_lists = data['numbers_list']
                if not numbers_lists:
                    logger.warning("Empty numbers_list in data dict")
                    return list(range(1, pick_count + 1))  # Fallback
            else:
                logger.warning("Dict format but no 'numbers_list' key found")
                return list(range(1, pick_count + 1))
        else:
            # Handle list of draw dictionaries
            numbers_lists = []
            for draw in data:
                numbers = draw.get('numbers', [])
                if isinstance(numbers, list) and len(numbers) > 0:
                    numbers_lists.append(numbers)
                elif isinstance(numbers, str):
                    # Try to parse string format
                    try:
                        from schema import DataValidator
                        parsed_numbers = DataValidator.normalize_numbers_field(numbers)
                        if parsed_numbers is not None and len(parsed_numbers) > 0:
                            numbers_lists.append(parsed_numbers)
                    except Exception:
                        continue

        if not numbers_lists:
            logger.warning("No valid numbers found in strategy input")
            return list(range(1, pick_count + 1))

        # Count frequency of each number
        frequency_counter = Counter()
        valid_range = range(1, 50)  # Valid for 649

        for numbers in numbers_lists:
            for num in numbers:
                if isinstance(num, (int, float)) and int(num) in valid_range:
                    frequency_counter[int(num)] += 1

        if not frequency_counter:
            logger.warning("No valid numbers in range found")
            return list(range(1, pick_count + 1))

        # Return the most frequent numbers
        most_common = frequency_counter.most_common(pick_count)
        result = [num for num, count in most_common]

        # Fill with sequential numbers if we don't have enough
        while len(result) < pick_count:
            for i in range(1, 50):
                if i not in result:
                    result.append(i)
                    if len(result) >= pick_count:
                        break

        logger.info(f"Generated frequency-based prediction: {result[:pick_count]}")
        return result[:pick_count]

    except Exception as e:
        logger.error(f"Error in uniform_frequency strategy: {e}")
        return list(range(1, pick_count + 1))  # Safe fallback

def uniform_frequency_with_stats(draws: List[Dict], pick_count: int = 6) -> Dict:
    """
    Enhanced frequency analysis with statistics

    Args:
        draws: List of draw dictionaries with 'numbers' field
        pick_count: Number of numbers to pick (6 for 649, 7 for Max)

    Returns:
        Dictionary with predicted numbers and statistics
    """
    # Validate input
    if not draws:
        return {
            'numbers': [],
            'stats': {
                'method': 'uniform_frequency',
                'confidence': 0.0,
                'sample_size': 0
            }
        }

    # Extract all numbers from all draws
    all_numbers = []
    for draw in draws:
        numbers = draw.get('numbers', [])

        # Handle different formats of numbers field
        if isinstance(numbers, str):
            # Handle string representation of list
            if numbers.startswith('[') and numbers.endswith(']'):
                try:
                    # Remove brackets and split by comma
                    nums_str = numbers.strip('[]')
                    # Handle various formats: "[1, 2, 3]" or "[1,2,3]"
                    nums = [int(n.strip()) for n in nums_str.split(',') if n.strip()]
                    all_numbers.extend(nums)
                except Exception:
                    pass
        elif isinstance(numbers, list):
            all_numbers.extend(numbers)

    # Count frequency of each number
    counter = Counter(all_numbers)

    # Get the most common numbers with counts
    most_common = counter.most_common()

    # Extract just the numbers (not the counts)
    top_numbers = [num for num, count in most_common[:pick_count]]

    # Calculate statistics
    total_draws = len(draws)
    total_numbers = len(all_numbers)

    # Calculate average frequency of top numbers
    top_counts = [count for num, count in most_common[:pick_count]]
    avg_frequency = sum(top_counts) / len(top_counts) if top_counts else 0

    # Calculate frequency percentage
    frequency_pct = avg_frequency / total_draws if total_draws > 0 else 0

    # Calculate confidence based on sample size and frequency
    # More draws = higher confidence, higher frequency = higher confidence
    confidence = min(0.9, (total_draws / 1000) * frequency_pct * 2)

    return {
        'numbers': top_numbers,
        'stats': {
            'method': 'uniform_frequency',
            'confidence': confidence,
            'sample_size': total_draws,
            'avg_frequency': avg_frequency,
            'frequency_pct': frequency_pct,
            'frequencies': {num: count for num, count in most_common[:20]}  # Top 20 frequencies
        }
    }

def get_number_range(game: str) -> tuple:
    """Get the valid number range for a game"""
    if 'max' in game.lower():
        return 1, 50  # Lotto Max: 1-50
    else:
        return 1, 49  # Lotto 649: 1-49

def validate_prediction(numbers: List[int], game: str) -> List[int]:
    """Validate and fix prediction if needed"""
    if not numbers:
        return []

    min_val, max_val = get_number_range(game)

    # Filter out invalid numbers
    valid_numbers = [n for n in numbers if min_val <= n <= max_val]

    # If we lost some numbers, add the next most likely ones
    if len(valid_numbers) < len(numbers):
        # Add sequential numbers from the valid range that aren't already in the list
        for n in range(min_val, max_val + 1):
            if n not in valid_numbers:
                valid_numbers.append(n)
                if len(valid_numbers) == len(numbers):
                    break

    return valid_numbers
