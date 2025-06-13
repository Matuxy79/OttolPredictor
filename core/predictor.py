"""Main prediction engine that coordinates strategies"""

from typing import Dict, List, Optional
from datetime import datetime
import logging
import pandas as pd

from strategies.adaptive_selector import AdaptiveStrategySelector
from core.data_manager import LotteryDataManager

logger = logging.getLogger(__name__)

class LottoPredictor:
    """Main prediction engine that coordinates strategies"""
    
    def __init__(self):
        self.data_manager = LotteryDataManager()
        self.strategy_selector = AdaptiveStrategySelector()
        self.cache = {}
    
    def predict_numbers(self, game: str, strategy: str = 'auto') -> Dict:
        """
        Main prediction interface
        
        Args:
            game: Game code ('649', 'max', etc.)
            strategy: Strategy to use ('auto' for automatic selection)
            
        Returns:
            Dictionary with prediction results and metadata
        """
        try:
            # Load historical data
            draws = self.data_manager.load_game_data(game)
            
            if not draws:
                logger.warning(f"No historical data for {game}")
                return self._fallback_prediction(game, strategy)
            
            # Determine pick count based on game
            pick_count = 7 if game.lower() == 'max' else 6
            
            # Select strategy
            if strategy == 'auto':
                # Use adaptive selector to find best strategy
                strategy_name, strategy_func = self.strategy_selector.select_best_strategy(draws, game)
                confidence = 'high'  # Adaptive selector picks the best strategy
            else:
                # Use specified strategy
                if strategy not in self.strategy_selector.strategies:
                    logger.warning(f"Unknown strategy: {strategy}, falling back to uniform")
                    strategy = 'uniform'
                
                strategy_name = strategy
                strategy_func = self.strategy_selector.strategies[strategy]
                confidence = 'medium'  # User-selected strategy
            
            # Generate prediction
            predicted_numbers = strategy_func(draws, pick_count)
            
            # Get performance data
            performance = self.strategy_selector.get_performance_summary(game)
            
            # Create prediction record
            prediction = {
                'predicted_numbers': predicted_numbers,
                'strategy_used': strategy_name,
                'strategy_display_name': self.strategy_selector.get_strategy_name(strategy_name),
                'confidence': confidence,
                'explanation': self._generate_explanation(strategy_name, performance),
                'metadata': {
                    'total_draws_analyzed': len(draws),
                    'strategy_backtest_score': performance.get('avg_scores', {}).get(strategy_name, 0.0),
                    'data_freshness': self._get_data_freshness(draws),
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            logger.info(f"Generated {game} prediction: {predicted_numbers} (strategy: {strategy_name})")
            return prediction
            
        except Exception as e:
            logger.error(f"Prediction generation failed: {e}")
            return self._fallback_prediction(game, strategy)
    
    def _fallback_prediction(self, game: str, strategy: str) -> Dict:
        """Generate fallback random prediction if all else fails"""
        import random
        
        count = 7 if game.lower() == 'max' else 6
        max_number = 50 if game.lower() == 'max' else 49
        
        numbers = sorted(random.sample(range(1, max_number + 1), count))
        
        return {
            'predicted_numbers': numbers,
            'strategy_used': 'random_fallback',
            'strategy_display_name': 'Random (Fallback)',
            'confidence': 'low',
            'explanation': 'Using random selection due to error or insufficient data.',
            'metadata': {
                'total_draws_analyzed': 0,
                'strategy_backtest_score': 0.0,
                'data_freshness': None,
                'timestamp': datetime.now().isoformat(),
                'error': True
            }
        }
    
    def _generate_explanation(self, strategy: str, performance: Dict) -> str:
        """Generate human-readable explanation for the prediction"""
        if strategy == 'uniform':
            return "Based on the overall frequency of numbers across all historical draws."
        elif strategy.startswith('recency'):
            intensity = strategy.split('_')[1]
            return f"Emphasizing {intensity} weighting toward recent draw patterns."
        elif strategy == 'era_based':
            return "Using different weights for different lottery rule periods."
        elif strategy == 'random':
            return "Random selection with no historical analysis."
        else:
            return "Using advanced statistical analysis of historical patterns."
    
    def _get_data_freshness(self, draws: List[Dict]) -> Optional[str]:
        """Get the most recent date in the dataset"""
        if not draws:
            return None
        
        dates = []
        for draw in draws:
            date_str = draw.get('date')
            if date_str:
                try:
                    dates.append(date_str)
                except:
                    pass
        
        if dates:
            return max(dates)
        return None
    
    def get_available_strategies(self) -> Dict[str, str]:
        """Return dictionary of available strategy keys and display names"""
        return self.strategy_selector.get_all_strategies()
    
    def get_strategy_performance(self, game: str) -> Dict:
        """Get performance metrics for all strategies for a specific game"""
        return self.strategy_selector.get_performance_summary(game)

# Backward compatibility function
def get_predictor() -> LottoPredictor:
    """Get or create a LottoPredictor instance"""
    return LottoPredictor()