"""Exponential decay weighting - recent draws matter more"""

import numpy as np
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

def recency_weighted_frequency(draws: List[Dict], lambda_decay: float = 0.2, pick_count: int = 6) -> List[int]:
    """
    Exponential decay weighting for lottery number frequency analysis
    
    Formula: weight = exp(-λ * days_ago / 365.25)
    
    Args:
        draws: List of draw dictionaries with 'numbers' and 'date' fields
        lambda_decay: Controls how quickly old data loses influence
            - 0.1 = slow decay (5+ year half-life)
            - 0.3 = medium decay (~2 year half-life)  
            - 0.5 = fast decay (~1 year half-life)
        pick_count: Number of numbers to pick (6 for 649, 7 for Max)
        
    Returns:
        List of top N most frequent numbers weighted by recency
    """
    # Validate input
    if not draws:
        return []
    
    # Get the most recent date as reference point
    most_recent_date = _get_most_recent_date(draws)
    if not most_recent_date:
        # Fallback to uniform frequency if dates can't be parsed
        logger.warning("Could not determine most recent date, falling back to uniform weighting")
        from strategies.uniform import uniform_frequency
        return uniform_frequency(draws, pick_count)
    
    # Calculate weighted frequencies
    weighted_counts = defaultdict(float)
    total_weights = 0.0
    
    for draw in draws:
        # Get date and calculate days ago
        date_str = draw.get('date', '')
        if not date_str:
            continue
        
        try:
            date_obj = _parse_date(date_str)
            if not date_obj:
                continue
            
            days_ago = (most_recent_date - date_obj).days
            
            # Calculate weight using exponential decay
            weight = np.exp(-lambda_decay * days_ago / 365.25)
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

def recency_weighted_frequency_with_stats(draws: List[Dict], lambda_decay: float = 0.2, pick_count: int = 6) -> Dict:
    """
    Enhanced recency-weighted frequency analysis with statistics
    
    Args:
        draws: List of draw dictionaries with 'numbers' and 'date' fields
        lambda_decay: Controls how quickly old data loses influence
        pick_count: Number of numbers to pick (6 for 649, 7 for Max)
        
    Returns:
        Dictionary with predicted numbers and statistics
    """
    # Validate input
    if not draws:
        return {
            'numbers': [],
            'stats': {
                'method': 'recency_weighted',
                'lambda': lambda_decay,
                'confidence': 0.0,
                'sample_size': 0
            }
        }
    
    # Get the most recent date as reference point
    most_recent_date = _get_most_recent_date(draws)
    if not most_recent_date:
        # Fallback to uniform frequency if dates can't be parsed
        logger.warning("Could not determine most recent date, falling back to uniform weighting")
        from strategies.uniform import uniform_frequency_with_stats
        return uniform_frequency_with_stats(draws, pick_count)
    
    # Calculate weighted frequencies
    weighted_counts = defaultdict(float)
    total_weights = 0.0
    processed_draws = 0
    
    # Track date range for statistics
    oldest_date = most_recent_date
    date_weights = []  # List of (date, weight) tuples for analysis
    
    for draw in draws:
        # Get date and calculate days ago
        date_str = draw.get('date', '')
        if not date_str:
            continue
        
        try:
            date_obj = _parse_date(date_str)
            if not date_obj:
                continue
            
            days_ago = (most_recent_date - date_obj).days
            
            # Update oldest date
            if date_obj < oldest_date:
                oldest_date = date_obj
            
            # Calculate weight using exponential decay
            weight = np.exp(-lambda_decay * days_ago / 365.25)
            total_weights += weight
            date_weights.append((date_obj, weight))
            
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
    
    # Calculate statistics
    date_range_days = (most_recent_date - oldest_date).days if oldest_date < most_recent_date else 0
    
    # Calculate effective sample size (sum of weights relative to uniform weights)
    uniform_weight = 1.0
    effective_sample = total_weights / uniform_weight if processed_draws > 0 else 0
    
    # Calculate confidence based on effective sample size and lambda
    # Higher lambda = more focus on recent data = potentially lower confidence
    # But also depends on how much data we have
    confidence_factor = min(1.0, effective_sample / 100)  # Scale by effective sample
    lambda_factor = 1.0 - (lambda_decay / 2.0)  # Higher lambda = slightly lower confidence
    confidence = min(0.9, confidence_factor * lambda_factor)
    
    # Calculate weighted frequencies for top numbers
    top_weighted_freqs = [count for _, count in sorted_numbers[:pick_count]]
    avg_weighted_freq = sum(top_weighted_freqs) / len(top_weighted_freqs) if top_weighted_freqs else 0
    
    return {
        'numbers': top_numbers,
        'stats': {
            'method': 'recency_weighted',
            'lambda': lambda_decay,
            'confidence': confidence,
            'sample_size': processed_draws,
            'effective_sample': effective_sample,
            'date_range_days': date_range_days,
            'avg_weighted_freq': avg_weighted_freq,
            'weighted_frequencies': {num: count for num, count in sorted_numbers[:20]}  # Top 20
        }
    }

def _get_most_recent_date(draws: List[Dict]) -> Optional[datetime]:
    """Extract the most recent date from a list of draws"""
    most_recent = None
    
    for draw in draws:
        date_str = draw.get('date', '')
        if not date_str:
            continue
        
        date_obj = _parse_date(date_str)
        if not date_obj:
            continue
        
        if most_recent is None or date_obj > most_recent:
            most_recent = date_obj
    
    return most_recent

def _parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string with multiple format support"""
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

def get_optimal_lambda(draws: List[Dict], test_lambdas: List[float] = None) -> Tuple[float, Dict]:
    """
    Find the optimal lambda decay parameter by testing against historical data
    
    Args:
        draws: List of draw dictionaries
        test_lambdas: List of lambda values to test (default: [0.1, 0.2, 0.3, 0.5, 0.7, 1.0])
        
    Returns:
        Tuple of (best_lambda, performance_stats)
    """
    if test_lambdas is None:
        test_lambdas = [0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
    
    if not draws or len(draws) < 10:
        return 0.2, {'error': 'Insufficient data for optimization'}
    
    # Sort draws by date
    sorted_draws = _sort_draws_by_date(draws)
    
    # Use 80% for training, 20% for testing
    split_idx = int(len(sorted_draws) * 0.8)
    training_draws = sorted_draws[:split_idx]
    testing_draws = sorted_draws[split_idx:]
    
    if not training_draws or not testing_draws:
        return 0.2, {'error': 'Could not split data properly'}
    
    # Test each lambda value
    results = {}
    for lambda_val in test_lambdas:
        # For each test draw, train on all previous draws and evaluate
        correct_numbers = 0
        total_numbers = 0
        
        for i, test_draw in enumerate(testing_draws):
            # Training data is all draws before this test draw
            train_data = training_draws + testing_draws[:i]
            
            # Get the actual numbers from the test draw
            actual_numbers = _extract_numbers(test_draw)
            if not actual_numbers:
                continue
            
            # Get the pick count based on the game type
            pick_count = len(actual_numbers)
            
            # Make prediction using current lambda
            predicted = recency_weighted_frequency(train_data, lambda_decay=lambda_val, pick_count=pick_count)
            
            # Count how many numbers we got right
            matches = len(set(predicted) & set(actual_numbers))
            correct_numbers += matches
            total_numbers += pick_count
        
        # Calculate accuracy
        accuracy = correct_numbers / total_numbers if total_numbers > 0 else 0
        
        results[lambda_val] = {
            'accuracy': accuracy,
            'correct_numbers': correct_numbers,
            'total_numbers': total_numbers
        }
    
    # Find best lambda
    best_lambda = max(results.items(), key=lambda x: x[1]['accuracy'])[0]
    
    return best_lambda, results

def _sort_draws_by_date(draws: List[Dict]) -> List[Dict]:
    """Sort draws by date (oldest first)"""
    dated_draws = []
    
    for draw in draws:
        date_str = draw.get('date', '')
        if not date_str:
            continue
        
        date_obj = _parse_date(date_str)
        if not date_obj:
            continue
        
        dated_draws.append((date_obj, draw))
    
    # Sort by date
    dated_draws.sort(key=lambda x: x[0])
    
    # Return just the draws
    return [draw for _, draw in dated_draws]