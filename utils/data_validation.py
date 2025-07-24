"""
Utility for validating and normalizing lottery draw records to a canonical schema.
"""
import logging
from typing import Dict, Any

def validate_draw_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure a draw record has all canonical fields and correct types.
    Canonical fields:
      - 'date': str or datetime (draw date)
      - 'numbers_list': list of int (main numbers)
      - 'bonus': int or None (bonus number, optional)
      - 'game': str (game code, e.g., '649', 'max')
    """
    # Date
    if 'date' not in record:
        record['date'] = None
    # Numbers list
    if 'numbers_list' not in record:
        # Try to convert from 'numbers' or similar
        nums = record.get('numbers')
        if isinstance(nums, list):
            record['numbers_list'] = [int(n) for n in nums]
        elif isinstance(nums, str):
            record['numbers_list'] = [int(n) for n in nums.split(',') if n.strip().isdigit()]
        else:
            record['numbers_list'] = []
    else:
        # Ensure it's a list of int
        record['numbers_list'] = [int(n) for n in record['numbers_list'] if str(n).isdigit()]
    # Bonus
    if 'bonus' not in record:
        record['bonus'] = None
    # Game
    if 'game' not in record:
        record['game'] = None
    return record

def validate_draw_dataframe(df):
    """
    Apply validate_draw_record to each row of a pandas DataFrame.
    """
    import pandas as pd
    return df.apply(lambda row: validate_draw_record(row.to_dict()), axis=1)
