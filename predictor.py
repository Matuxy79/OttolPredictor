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
from datetime import datetime

from data_manager import get_data_manager
from analytics import get_analytics_engine
from metrics import PredictionMetrics, GameType, quick_uplift_check, generate_random_baseline

logger = logging.getLogger(__name__)

class LotteryPredictor:
    """
    Provides prediction algorithms for lottery numbers with statistical performance evaluation
    """

    def __init__(self):
        """Initialize the predictor engine with metrics capabilities"""
        self.data_manager = get_data_manager()
        self.analytics = get_analytics_engine()
        self.metrics_engine = PredictionMetrics()

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
        Generate smart predictions with performance metrics

        Args:
            game: Game type (649, max, etc.)
            strategy: Prediction strategy ('balanced', 'hot', 'cold', 'random')
            num_sets: Number of sets to generate

        Returns:
            List of dictionaries with 'numbers', 'bonus', 'confidence', and performance metrics
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

        # Enhance predictions with performance metrics
        enhanced_predictions = self._add_performance_evaluation(
            results, game, strategy
        )

        logger.info(f"Generated {num_sets} smart picks for {game} using {strategy} strategy")
        return enhanced_predictions

    def _add_performance_evaluation(self, 
                                  predictions: List[Dict], 
                                  game: str, 
                                  strategy: str) -> List[Dict]:
        """Add statistical performance evaluation to predictions"""

        if not predictions:
            return predictions

        try:
            # Convert game string to enum
            game_type = GameType.LOTTO_649 if game == '649' else GameType.LOTTO_MAX

            # Extract number lists from predictions
            prediction_numbers = []
            for pred in predictions:
                if 'numbers' in pred and isinstance(pred['numbers'], list):
                    prediction_numbers.append(pred['numbers'])
                else:
                    logger.warning(f"Invalid prediction format: {pred}")
                    continue

            if not prediction_numbers:
                logger.warning("No valid prediction numbers found")
                return self._add_basic_metadata(predictions, "invalid_format")

            # Generate random baseline for comparison
            random_baseline = generate_random_baseline(len(prediction_numbers), game_type)

            # Get recent historical draws
            recent_draws = self._get_evaluation_draws(game, lookback_days=90)

            if len(recent_draws) < 15:  # Minimum for meaningful analysis
                logger.warning(f"Insufficient historical data: {len(recent_draws)} draws")
                return self._add_basic_metadata(predictions, "insufficient_data")

            # Calculate performance metrics
            metrics_result = quick_uplift_check(
                prediction_numbers, random_baseline, recent_draws, game_type
            )

            # Enhance each prediction with metrics
            evaluation_timestamp = datetime.now().isoformat()

            for pred in predictions:
                pred.update({
                    'performance_metrics': {
                        'uplift_percent': metrics_result['uplift_percent'],
                        'is_significant': metrics_result['is_significant'],
                        'tier': metrics_result['tier'],
                        'sample_size': metrics_result['sample_size'],
                        'confidence_interval': metrics_result['confidence_interval'],
                        'status': metrics_result['status'],
                        'strategy': strategy,
                        'evaluation_timestamp': evaluation_timestamp
                    },
                    'uplift_headline': metrics_result['headline'],
                    'display_class': metrics_result.get('display_class', 'neutral')
                })

            logger.info(f"Performance evaluation completed: {metrics_result['headline']}")
            return predictions

        except Exception as e:
            logger.error(f"Performance evaluation failed: {e}")
            return self._add_basic_metadata(predictions, "evaluation_error")

    def _get_evaluation_draws(self, game: str, lookback_days: int = 90) -> List[List[int]]:
        """Get recent draws formatted for metrics evaluation"""

        try:
            # Use existing data_manager method
            recent_data = self.data_manager.get_recent_draws(game, days=lookback_days)

            formatted_draws = []
            for draw in recent_data:
                try:
                    if hasattr(draw, 'numbers'):
                        # Handle DrawRecord objects
                        if isinstance(draw.numbers, list):
                            formatted_draws.append(draw.numbers)
                        elif isinstance(draw.numbers, str):
                            # Parse string format: "1,2,3,4,5,6"
                            numbers = [int(x.strip()) for x in draw.numbers.split(',')]
                            formatted_draws.append(numbers)
                    elif isinstance(draw, dict) and 'numbers' in draw:
                        # Handle dictionary format
                        numbers = draw['numbers']
                        if isinstance(numbers, str):
                            numbers = [int(x.strip()) for x in numbers.split(',')]
                        formatted_draws.append(numbers)
                    else:
                        logger.debug(f"Skipping draw with unknown format: {type(draw)}")

                except (ValueError, AttributeError) as e:
                    logger.debug(f"Error parsing draw {draw}: {e}")
                    continue

            logger.debug(f"Formatted {len(formatted_draws)} draws for evaluation")
            return formatted_draws

        except Exception as e:
            logger.error(f"Failed to get evaluation draws: {e}")
            return []

    def _add_basic_metadata(self, predictions: List[Dict], status: str) -> List[Dict]:
        """Add basic metadata when metrics evaluation fails"""

        status_messages = {
            "insufficient_data": "📊 Need more data",
            "invalid_format": "📊 Format error", 
            "evaluation_error": "📊 Eval error"
        }

        headline = status_messages.get(status, "📊 Unknown")

        for pred in predictions:
            pred.update({
                'performance_metrics': {
                    'status': status,
                    'evaluation_timestamp': datetime.now().isoformat()
                },
                'uplift_headline': headline,
                'display_class': 'warning'
            })

        return predictions

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
