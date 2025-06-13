"""Simple uniform weighting - all historical draws equal"""

from typing import List, Dict
import pandas as pd
import numpy as np
from collections import Counter

def uniform_frequency(draws: List[Dict], pick_count: int = 6) -> List[int]:
    """
    Basic frequency analysis with uniform weighting
    
    Args:
        draws: List of draw dictionaries with 'numbers' field
        pick_count: Number of numbers to pick (6 for 649, 7 for Max)
        
    Returns:
        List of top N most frequent numbers
    """
    # Validate input
    if not draws:
        return []
    
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
    
    # Get the most common numbers
    most_common = counter.most_common()
    
    # Extract just the numbers (not the counts)
    top_numbers = [num for num, count in most_common[:pick_count]]
    
    return top_numbers

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