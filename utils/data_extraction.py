"""
Universal data extraction utilities for bulletproof number handling
"""
import numpy as np
import ast
import json
import logging
from typing import List, Any

logger = logging.getLogger(__name__)

def safe_number_list(raw: Any) -> List[int]:
    """
    Safely extract flat list of ints from any structure
    This is our universal extractor that handles ALL edge cases
    """
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return []
    
    # Handle NumPy arrays first (convert to list)
    if isinstance(raw, np.ndarray):
        try:
            raw = raw.tolist()
        except Exception:
            return []
    
    # Handle string representations
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw or raw.lower() in ['nan', 'none', 'null']:
            return []
            
        # Try JSON parsing first
        if raw.startswith('[') and raw.endswith(']'):
            try:
                raw = json.loads(raw)
            except:
                try:
                    raw = ast.literal_eval(raw)
                except:
                    # Manual parsing as fallback
                    try:
                        nums_str = raw.strip('[]')
                        if nums_str:
                            raw = [int(n.strip()) for n in nums_str.split(',') if n.strip()]
                        else:
                            return []
                    except:
                        return []
        
        # Handle comma-separated without brackets
        elif ',' in raw:
            try:
                raw = [int(n.strip()) for n in raw.split(',') if n.strip()]
            except:
                return []
        
        # Handle space-separated
        elif ' ' in raw:
            try:
                raw = [int(n.strip()) for n in raw.split() if n.strip()]
            except:
                return []
        
        # Single number string
        else:
            try:
                return [int(raw)]
            except:
                return []
    
    # Handle lists (including nested lists)
    if isinstance(raw, list):
        flat = []
        for item in raw:
            if isinstance(item, list):
                # Recursively flatten nested lists
                flat.extend(safe_number_list(item))
            elif isinstance(item, (int, float)) and not (isinstance(item, float) and np.isnan(item)):
                try:
                    flat.append(int(item))
                except:
                    continue
            elif isinstance(item, str) and item.strip():
                try:
                    flat.append(int(item.strip()))
                except:
                    continue
        return flat
    
    # Handle other iterables
    try:
        result = []
        for item in raw:
            if isinstance(item, (int, float)) and not (isinstance(item, float) and np.isnan(item)):
                result.append(int(item))
        return result
    except:
        pass
    
    # Last resort: try to convert directly
    try:
        return [int(raw)]
    except:
        return []

def safe_data_extraction(data, numbers_column='numbers_list') -> List[List[int]]:
    """
    Extract all valid number lists from a DataFrame or list of records
    Returns: List of number lists (each inner list is one draw)
    """
    valid_draws = []
    
    if hasattr(data, 'iterrows'):  # DataFrame
        for idx, row in data.iterrows():
            numbers = safe_number_list(row.get(numbers_column, []))
            if numbers:  # Only include non-empty draws
                valid_draws.append(numbers)
    
    elif isinstance(data, list):  # List of dicts
        for record in data:
            numbers = safe_number_list(record.get(numbers_column, []))
            if numbers:
                valid_draws.append(numbers)
    
    return valid_draws

def validate_draw_numbers(numbers: List[int], game: str = "649") -> bool:
    """
    Validate that numbers make sense for the given game
    """
    if not numbers:
        return False
    
    # Basic validation rules by game
    game_rules = {
        "649": {"count": 6, "min": 1, "max": 49},
        "max": {"count": 7, "min": 1, "max": 50},
        "western649": {"count": 6, "min": 1, "max": 49},
        "westernmax": {"count": 7, "min": 1, "max": 50},
        "dailygrand": {"count": 5, "min": 1, "max": 49}
    }
    
    rules = game_rules.get(game, {"count": 6, "min": 1, "max": 50})
    
    # Check count (allow some flexibility for bonus numbers)
    if len(numbers) < rules["count"] - 1 or len(numbers) > rules["count"] + 2:
        return False
    
    # Check range
    for num in numbers:
        if num < rules["min"] or num > rules["max"]:
            return False
    
    # Check for duplicates
    if len(set(numbers)) != len(numbers):
        return False
    
    return True