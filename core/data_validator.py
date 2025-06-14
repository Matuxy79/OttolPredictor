"""
Ensure data consistency between PDF and scraped sources
"""

from typing import Dict, List, Any, Optional
import json
import re
import logging
import numpy as np

class DataValidator:
    """Validate and normalize lottery draw data"""

    logger = logging.getLogger(__name__)

    @staticmethod
    def validate_draw_format(draw_data: Dict) -> bool:
        """Validate that draw data matches expected format"""
        required_fields = ['game', 'date', 'numbers']

        # Check required fields exist
        for field in required_fields:
            if field not in draw_data:
                DataValidator.logger.warning(f"Missing required field: {field}")
                return False

        # Validate game name
        valid_games = ['Lotto 649', 'Lotto Max', 'Western 649', 'Western Max', 'Daily Grand']
        if draw_data['game'] not in valid_games:
            DataValidator.logger.warning(f"Invalid game name: {draw_data['game']}")
            return False

        # Validate numbers field
        try:
            numbers = DataValidator.normalize_numbers_field(draw_data['numbers'])

            # Check correct number count based on game
            if draw_data['game'] == 'Lotto Max' or draw_data['game'] == 'Western Max':
                if len(numbers) != 7:
                    DataValidator.logger.warning(f"Invalid number count for {draw_data['game']}: {len(numbers)}")
                    return False
            else:  # Lotto 649, Western 649, Daily Grand
                if len(numbers) != 6 and draw_data['game'] != 'Daily Grand':
                    DataValidator.logger.warning(f"Invalid number count for {draw_data['game']}: {len(numbers)}")
                    return False
                elif len(numbers) != 5 and draw_data['game'] == 'Daily Grand':
                    DataValidator.logger.warning(f"Invalid number count for Daily Grand: {len(numbers)}")
                    return False

            # Check number range
            for num in numbers:
                if not isinstance(num, int):
                    DataValidator.logger.warning(f"Non-integer number found: {num}")
                    return False

                if draw_data['game'] == 'Lotto Max' or draw_data['game'] == 'Western Max':
                    if num < 1 or num > 50:
                        DataValidator.logger.warning(f"Number out of range for {draw_data['game']}: {num}")
                        return False
                elif draw_data['game'] == 'Lotto 649' or draw_data['game'] == 'Western 649':
                    if num < 1 or num > 49:
                        DataValidator.logger.warning(f"Number out of range for {draw_data['game']}: {num}")
                        return False
                elif draw_data['game'] == 'Daily Grand':
                    if num < 1 or num > 49:
                        DataValidator.logger.warning(f"Number out of range for Daily Grand: {num}")
                        return False

        except Exception as e:
            DataValidator.logger.warning(f"Error validating numbers: {e}")
            return False

        # Validate bonus number if present
        if 'bonus' in draw_data and draw_data['bonus'] is not None:
            try:
                bonus = int(draw_data['bonus'])

                # Check bonus range
                if draw_data['game'] == 'Lotto Max' or draw_data['game'] == 'Western Max':
                    if bonus < 1 or bonus > 50:
                        DataValidator.logger.warning(f"Bonus out of range for {draw_data['game']}: {bonus}")
                        return False
                elif draw_data['game'] == 'Lotto 649' or draw_data['game'] == 'Western 649':
                    if bonus < 1 or bonus > 49:
                        DataValidator.logger.warning(f"Bonus out of range for {draw_data['game']}: {bonus}")
                        return False
                elif draw_data['game'] == 'Daily Grand':
                    if bonus < 1 or bonus > 7:  # Grand Number is 1-7
                        DataValidator.logger.warning(f"Grand Number out of range for Daily Grand: {bonus}")
                        return False

            except Exception as e:
                DataValidator.logger.warning(f"Error validating bonus: {e}")
                return False

        # Validate date format (flexible validation)
        if not DataValidator._validate_date_format(draw_data['date']):
            DataValidator.logger.warning(f"Invalid date format: {draw_data['date']}")
            return False

        return True

    @staticmethod
    def normalize_numbers_field(numbers_field: Any) -> List[int]:
        """Normalize numbers field to Python list, handling all edge cases"""
        if numbers_field is None:
            return []

        # Handle NumPy arrays first (most critical fix)
        if isinstance(numbers_field, np.ndarray):
            return [int(n) for n in numbers_field.tolist() if n is not None]

        # Handle Python lists
        if isinstance(numbers_field, list):
            return [int(n) for n in numbers_field if n is not None]

        # Handle string representations
        if isinstance(numbers_field, str):
            # Handle string representation of list
            if numbers_field.startswith('[') and numbers_field.endswith(']'):
                # Parse string representation of list
                try:
                    # Remove brackets and split by comma
                    nums_str = numbers_field.strip('[]')
                    # Handle various formats: "[1, 2, 3]" or "[1,2,3]"
                    if not nums_str:
                        return []
                    nums = [int(n.strip()) for n in nums_str.split(',') if n.strip()]
                    return nums
                except Exception as e:
                    DataValidator.logger.warning(f"Error parsing numbers string: {numbers_field}. Error: {e}")
                    raise ValueError(f"Invalid numbers format: {numbers_field}")

            # Handle comma-separated string without brackets
            elif ',' in numbers_field:
                try:
                    return [int(n.strip()) for n in numbers_field.split(',') if n.strip()]
                except Exception as e:
                    DataValidator.logger.warning(f"Error parsing comma-separated numbers: {numbers_field}. Error: {e}")
                    raise ValueError(f"Invalid numbers format: {numbers_field}")

            # Handle space-separated string
            elif ' ' in numbers_field:
                try:
                    return [int(n.strip()) for n in numbers_field.split() if n.strip()]
                except Exception as e:
                    DataValidator.logger.warning(f"Error parsing space-separated numbers: {numbers_field}. Error: {e}")
                    raise ValueError(f"Invalid numbers format: {numbers_field}")

            # Try to parse as JSON
            else:
                try:
                    nums = json.loads(numbers_field)
                    if isinstance(nums, list):
                        return [int(n) for n in nums if n is not None]
                    else:
                        raise ValueError(f"JSON parsing did not produce a list: {numbers_field}")
                except Exception as e:
                    DataValidator.logger.warning(f"Error parsing numbers as JSON: {numbers_field}. Error: {e}")
                    raise ValueError(f"Invalid numbers format: {numbers_field}")

        # Handle other iterables
        try:
            return [int(n) for n in numbers_field if n is not None]
        except (TypeError, ValueError):
            DataValidator.logger.warning(f"Unsupported numbers field type: {type(numbers_field)}")
            return []

    @staticmethod
    def _validate_date_format(date_str: str) -> bool:
        """
        Validate date format with flexible patterns
        Accepts: YYYY-MM-DD, MM/DD/YYYY, DD Mon YYYY, etc.
        """
        # Common date patterns
        patterns = [
            r'^\d{4}-\d{2}-\d{2}$',                  # YYYY-MM-DD
            r'^\d{4}/\d{2}/\d{2}$',                  # YYYY/MM/DD
            r'^\d{2}/\d{2}/\d{4}$',                  # MM/DD/YYYY or DD/MM/YYYY
            r'^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}$',      # DD Mon YYYY
            r'^[A-Za-z]{3}\s+\d{1,2},?\s+\d{4}$'     # Mon DD, YYYY
        ]

        for pattern in patterns:
            if re.match(pattern, date_str):
                return True

        return False

    @staticmethod
    def standardize_draw_data(draw_data: Dict) -> Dict:
        """
        Standardize draw data to ensure consistent format
        Returns a new dictionary with standardized fields
        """
        standardized = {}

        # Copy original data
        for key, value in draw_data.items():
            standardized[key] = value

        # Standardize game name
        if 'game' in standardized:
            game = standardized['game']
            if '649' in game:
                if 'western' in game.lower() or 'west' in game.lower():
                    standardized['game'] = 'Western 649'
                else:
                    standardized['game'] = 'Lotto 649'
            elif 'max' in game.lower():
                if 'western' in game.lower() or 'west' in game.lower():
                    standardized['game'] = 'Western Max'
                else:
                    standardized['game'] = 'Lotto Max'
            elif 'grand' in game.lower() or 'daily' in game.lower():
                standardized['game'] = 'Daily Grand'

        # Standardize numbers
        if 'numbers' in standardized:
            try:
                standardized['numbers'] = DataValidator.normalize_numbers_field(standardized['numbers'])
            except Exception as e:
                DataValidator.logger.warning(f"Error standardizing numbers: {e}")

        # Standardize bonus
        if 'bonus' in standardized and standardized['bonus'] is not None:
            try:
                standardized['bonus'] = int(standardized['bonus'])
            except Exception as e:
                DataValidator.logger.warning(f"Error standardizing bonus: {e}")

        return standardized

    @staticmethod
    def merge_draw_sources(pdf_data: Dict, scraped_data: Dict) -> Dict:
        """
        Merge data from PDF and scraped sources, prioritizing the most reliable data
        Returns a new dictionary with merged fields
        """
        merged = {}

        # Start with scraped data as base
        for key, value in scraped_data.items():
            merged[key] = value

        # Add source information
        merged['source'] = 'scraped'

        # Override with PDF data for certain fields (PDF is authoritative for historical data)
        if 'date' in pdf_data:
            merged['date'] = pdf_data['date']

        if 'numbers' in pdf_data:
            # PDF numbers are authoritative, but keep scraped format
            pdf_numbers = DataValidator.normalize_numbers_field(pdf_data['numbers'])
            if isinstance(merged.get('numbers'), str) and merged['numbers'].startswith('['):
                # If scraped data has numbers as string representation of list, maintain that format
                merged['numbers'] = str(pdf_numbers)
            else:
                merged['numbers'] = pdf_numbers

        if 'bonus' in pdf_data and pdf_data['bonus'] is not None:
            merged['bonus'] = pdf_data['bonus']

        # Add metadata about the merge
        merged['merged_source'] = {
            'pdf': bool(pdf_data),
            'scraped': bool(scraped_data),
            'priority': 'pdf' if pdf_data else 'scraped'
        }

        return merged
