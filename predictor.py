from typing import Dict, List, Optional
from datetime import datetime
import logging
import pandas as pd
from algorithms.prediction_strategies import (
    RandomStrategy, HotColdStrategy, FrequencyStrategy, BalancedStrategy
)

logger = logging.getLogger(__name__)

class SmartPredictor:
    """Main prediction engine coordinating multiple strategies"""

    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.strategies = {
            'random': RandomStrategy(),
            'hot_cold': HotColdStrategy(),
            'frequency': FrequencyStrategy(),
            'balanced': BalancedStrategy()
        }
        self.default_strategy = 'balanced'

    def _convert_df_to_dict(self, df):
        """Convert DataFrame to dictionary format expected by strategies"""
        # If df is already a dictionary, return it
        if isinstance(df, dict):
            return df

        if df is None or df.empty:
            return {'numbers_list': []}

        # Extract numbers_list from DataFrame
        numbers_list = []
        if 'numbers_list' in df.columns:
            # Filter out None or empty lists
            numbers_list = [lst for lst in df['numbers_list'].tolist() if lst]

        return {
            'numbers_list': numbers_list,
            'total_draws': len(df),
            'date_range': self._get_date_range(df) if not df.empty else None
        }

    def _get_date_range(self, df):
        """Get date range from DataFrame"""
        if 'date_parsed' in df.columns and df['date_parsed'].notna().any():
            try:
                min_date = df['date_parsed'].min()
                max_date = df['date_parsed'].max()
                if pd.notna(min_date) and pd.notna(max_date):
                    return (min_date, max_date)
            except Exception as e:
                logger.debug(f"Error getting date range: {e}")
        return None

    def generate_prediction(self, game: str, strategy: str = None) -> Dict:
        """Generate lottery prediction with metadata"""
        strategy = strategy or self.default_strategy

        try:
            # Load historical data
            df_historical_data = self.data_manager.load_game_data(game)

            # Convert DataFrame to dictionary format expected by strategies
            historical_data = self._convert_df_to_dict(df_historical_data)

            if not historical_data or not historical_data.get('numbers_list'):
                logger.warning(f"No historical data for {game}, using random strategy")
                strategy = 'random'

            # Determine number count based on game
            count = 6 if game == '649' else 7

            # Get strategy and generate prediction
            strategy_obj = self.strategies.get(strategy, self.strategies['random'])
            numbers = strategy_obj.predict(historical_data, count)
            confidence = strategy_obj.calculate_confidence(historical_data, numbers)

            # Create prediction record
            prediction = {
                'numbers': numbers,
                'game': game,
                'strategy': strategy,
                'strategy_name': strategy_obj.get_strategy_name(),
                'confidence': confidence,
                'confidence_stars': self._confidence_to_stars(confidence),
                'timestamp': datetime.now().isoformat(),
                'data_draws_count': len(historical_data.get('numbers_list', [])),
                'version': '1.0'
            }

            logger.info(f"Generated {game} prediction: {numbers} (strategy: {strategy}, confidence: {confidence:.2f})")
            return prediction

        except Exception as e:
            logger.error(f"Prediction generation failed: {e}")
            return self._fallback_prediction(game, strategy)

    def _confidence_to_stars(self, confidence: float) -> int:
        """Convert confidence score to 1-5 star rating"""
        if confidence >= 0.8:
            return 5
        elif confidence >= 0.6:
            return 4
        elif confidence >= 0.4:
            return 3
        elif confidence >= 0.2:
            return 2
        else:
            return 1

    def _fallback_prediction(self, game: str, strategy: str) -> Dict:
        """Generate fallback random prediction if all else fails"""
        count = 6 if game == '649' else 7
        max_number = 49 if game == '649' else 50

        import random
        numbers = sorted(random.sample(range(1, max_number + 1), count))

        return {
            'numbers': numbers,
            'game': game,
            'strategy': 'random_fallback',
            'strategy_name': 'Random (Fallback)',
            'confidence': 0.1,
            'confidence_stars': 1,
            'timestamp': datetime.now().isoformat(),
            'data_draws_count': 0,
            'version': '1.0',
            'error': True
        }

    def get_available_strategies(self) -> List[str]:
        """Return list of available strategy names"""
        return list(self.strategies.keys())

    def validate_prediction(self, prediction: Dict) -> bool:
        """Validate prediction format and content"""
        required_fields = ['numbers', 'game', 'strategy', 'confidence', 'timestamp']

        if not all(field in prediction for field in required_fields):
            return False

        numbers = prediction['numbers']
        game = prediction['game']

        # Validate number count
        expected_count = 6 if game == '649' else 7
        if len(numbers) != expected_count:
            return False

        # Validate number range
        max_number = 49 if game == '649' else 50
        if not all(1 <= num <= max_number for num in numbers):
            return False

        # Validate uniqueness
        if len(set(numbers)) != len(numbers):
            return False

        return True

# Backward compatibility function
def generate_lottery_prediction(game: str = '649') -> List[int]:
    """Legacy function for backward compatibility"""
    from data_manager import get_data_manager

    predictor = SmartPredictor(get_data_manager())
    prediction = predictor.generate_prediction(game)
    return prediction['numbers']
