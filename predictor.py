"""
Predictor Module for Saskatoon Lotto Predictor

This module provides prediction algorithms for lottery numbers.
It works with the data_manager and analytics modules to generate
predictions based on historical data and statistical analysis.
"""

import random
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging

from data_manager import get_data_manager
from analytics import get_analytics_engine

logger = logging.getLogger(__name__)

class LotteryPredictor:
    """
    Provides prediction algorithms for lottery numbers
    """
    
    def __init__(self):
        """Initialize the predictor engine"""
        self.data_manager = get_data_manager()
        self.analytics = get_analytics_engine()
    
    def quick_pick(self, game: str, num_sets: int = 1) -> List[Dict]:
        """
        Generate random number picks (quick pick)
        
        Args:
            game: Game type (649, max, etc.)
            num_sets: Number of sets to generate
            
        Returns:
            List of dictionaries with 'numbers' and 'bonus' keys
        """
        # Define number ranges for each game
        game_config = {
            '649': {'count': 6, 'max': 49, 'bonus_max': 49},
            'max': {'count': 7, 'max': 50, 'bonus_max': 50},
            'western649': {'count': 6, 'max': 49, 'bonus_max': 49},
            'westernmax': {'count': 7, 'max': 50, 'bonus_max': 50},
            'dailygrand': {'count': 5, 'max': 49, 'bonus_max': 7}
        }
        
        config = game_config.get(game, game_config['649'])
        
        results = []
        for _ in range(num_sets):
            # Generate main numbers
            numbers = sorted(random.sample(range(1, config['max'] + 1), config['count']))
            
            # Generate bonus number
            bonus = random.randint(1, config['bonus_max'])
            
            results.append({
                'numbers': numbers,
                'bonus': bonus,
                'confidence': 1  # Low confidence for random picks
            })
        
        logger.info(f"Generated {num_sets} quick picks for {game}")
        return results
    
    def smart_pick(self, game: str, strategy: str = 'balanced', num_sets: int = 1) -> List[Dict]:
        """
        Generate data-driven number picks (smart pick)
        
        Args:
            game: Game type (649, max, etc.)
            strategy: Prediction strategy ('balanced', 'hot', 'cold', 'random')
            num_sets: Number of sets to generate
            
        Returns:
            List of dictionaries with 'numbers', 'bonus', and 'confidence' keys
        """
        frequency_data = self.analytics.analyze_number_frequency(game)
        
        if not frequency_data:
            logger.warning(f"No frequency data available for {game}")
            return self.quick_pick(game, num_sets)
        
        # Game configuration
        game_config = {
            '649': {'count': 6, 'max': 49},
            'max': {'count': 7, 'max': 50},
            'western649': {'count': 6, 'max': 49},
            'westernmax': {'count': 7, 'max': 50},
            'dailygrand': {'count': 5, 'max': 49}
        }
        
        config = game_config.get(game, game_config['649'])
        
        # Sort numbers by frequency
        sorted_numbers = sorted(frequency_data.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for _ in range(num_sets):
            if strategy.lower() == 'hot':
                # Focus on most frequent numbers
                hot_numbers = [num for num, freq in sorted_numbers[:15]]
                numbers = sorted(random.sample(hot_numbers, min(config['count'], len(hot_numbers))))
                confidence = 4
                
            elif strategy.lower() == 'cold':
                # Focus on least frequent numbers
                cold_numbers = [num for num, freq in sorted_numbers[-15:]]
                numbers = sorted(random.sample(cold_numbers, min(config['count'], len(cold_numbers))))
                confidence = 2
                
            else:  # balanced or random
                # Mix of hot, medium, and cold numbers
                hot_numbers = [num for num, freq in sorted_numbers[:10]]
                cold_numbers = [num for num, freq in sorted_numbers[-10:]]
                medium_numbers = [num for num, freq in sorted_numbers[10:-10]]
                
                # Select 2 hot, 2 cold, rest medium
                selected = []
                selected.extend(random.sample(hot_numbers, min(2, len(hot_numbers))))
                selected.extend(random.sample(cold_numbers, min(2, len(cold_numbers))))
                
                remaining = config['count'] - len(selected)
                if remaining > 0 and medium_numbers:
                    selected.extend(random.sample(medium_numbers, min(remaining, len(medium_numbers))))
                
                # Fill remaining with any available numbers if needed
                while len(selected) < config['count']:
                    available = [i for i in range(1, config['max'] + 1) if i not in selected]
                    if available:
                        selected.append(random.choice(available))
                    else:
                        break
                
                numbers = sorted(selected[:config['count']])
                confidence = 3
            
            # Ensure we have the right number of numbers
            while len(numbers) < config['count']:
                available = [i for i in range(1, config['max'] + 1) if i not in numbers]
                if available:
                    numbers.append(random.choice(available))
                    numbers.sort()
                else:
                    break
            
            # Generate bonus number
            bonus = random.randint(1, config['max'])
            
            results.append({
                'numbers': numbers,
                'bonus': bonus,
                'confidence': confidence
            })
        
        logger.info(f"Generated {num_sets} smart picks for {game} using {strategy} strategy")
        return results
    
    def advanced_prediction(self, game: str, num_sets: int = 1) -> List[Dict]:
        """
        Generate advanced predictions using multiple algorithms
        
        Args:
            game: Game type (649, max, etc.)
            num_sets: Number of sets to generate
            
        Returns:
            List of dictionaries with prediction results
        """
        # Placeholder for future implementation
        logger.info(f"Advanced prediction requested for {game}")
        return self.smart_pick(game, 'balanced', num_sets)


# Convenience function
def get_predictor_engine() -> LotteryPredictor:
    """Get a shared instance of the predictor engine"""
    if not hasattr(get_predictor_engine, '_instance'):
        get_predictor_engine._instance = LotteryPredictor()
    return get_predictor_engine._instance