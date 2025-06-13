"""
Self-learning strategy selector with backtesting
CRITICAL: This is the core intelligence of the system
"""

from typing import List, Dict, Callable, Tuple, Optional, Any
import logging
import json
import os
from datetime import datetime
import random

# Import strategies
from strategies.uniform import uniform_frequency
from strategies.recency_weighted import recency_weighted_frequency, get_optimal_lambda
from strategies.era_based import era_weighted_frequency

logger = logging.getLogger(__name__)

class AdaptiveStrategySelector:
    """
    Self-learning strategy selector that automatically chooses the best
    prediction strategy based on historical performance
    """
    
    def __init__(self):
        """Initialize the strategy selector with available strategies"""
        self.strategies = {
            'uniform': uniform_frequency,
            'recency_light': lambda draws, pick_count: recency_weighted_frequency(draws, 0.1, pick_count),
            'recency_medium': lambda draws, pick_count: recency_weighted_frequency(draws, 0.3, pick_count),
            'recency_heavy': lambda draws, pick_count: recency_weighted_frequency(draws, 0.5, pick_count),
            'era_based': era_weighted_frequency,
            'random': self._random_strategy
        }
        
        # Strategy display names for UI
        self.strategy_names = {
            'uniform': "Historical Frequency",
            'recency_light': "Recent Trends (Light)",
            'recency_medium': "Recent Trends (Medium)",
            'recency_heavy': "Recent Trends (Strong)",
            'era_based': "Era-Based Analysis",
            'random': "Random Selection"
        }
        
        # Performance history for each strategy
        self.performance_history = {}
        
        # Default backtest window size
        self.backtest_window = 100  # Test on last 100 draws
        
        # Cache for backtest results
        self._backtest_cache = {}
        self._cache_expiry = {}
        self._cache_duration = 3600  # Cache valid for 1 hour (in seconds)
    
    def select_best_strategy(self, draws: List[Dict], game: str) -> Tuple[str, Callable]:
        """
        Backtest all strategies and return the best performer
        
        Args:
            draws: List of draw dictionaries
            game: Game code ('649', 'max', etc.)
            
        Returns:
            Tuple of (strategy_name, strategy_function)
        """
        logger.info(f"Selecting best strategy for {game} with {len(draws)} draws")
        
        # Check if we have enough data for meaningful backtesting
        if len(draws) < 20:
            logger.warning(f"Insufficient data for backtesting ({len(draws)} draws). Using default strategy.")
            return 'uniform', self.strategies['uniform']
        
        # Check cache first
        cache_key = f"{game}_{len(draws)}"
        if cache_key in self._backtest_cache:
            cache_time = self._cache_expiry.get(cache_key, 0)
            if datetime.now().timestamp() - cache_time < self._cache_duration:
                best_strategy = self._backtest_cache[cache_key]
                logger.info(f"Using cached best strategy: {best_strategy}")
                return best_strategy, self.strategies[best_strategy]
        
        # Run backtests for each strategy
        results = {}
        for strategy_name, strategy_func in self.strategies.items():
            try:
                score = self._backtest_strategy(strategy_func, draws)
                results[strategy_name] = score
                logger.debug(f"Strategy {strategy_name} scored {score:.4f}")
            except Exception as e:
                logger.error(f"Error testing strategy {strategy_name}: {e}")
                results[strategy_name] = 0.0
        
        # Find the best strategy
        best_strategy = max(results.items(), key=lambda x: x[1])[0]
        
        # Update cache
        self._backtest_cache[cache_key] = best_strategy
        self._cache_expiry[cache_key] = datetime.now().timestamp()
        
        # Update performance history
        if game not in self.performance_history:
            self.performance_history[game] = {}
        
        self.performance_history[game][datetime.now().isoformat()] = {
            'best_strategy': best_strategy,
            'scores': results,
            'data_size': len(draws)
        }
        
        logger.info(f"Best strategy for {game}: {best_strategy} (score: {results[best_strategy]:.4f})")
        
        return best_strategy, self.strategies[best_strategy]
    
    def _backtest_strategy(self, strategy_func: Callable, draws: List[Dict]) -> float:
        """
        Test a single strategy on historical data
        
        Args:
            strategy_func: Strategy function to test
            draws: List of draw dictionaries
            
        Returns:
            Score between 0.0 and 1.0 (higher is better)
        """
        if len(draws) < 10:
            return 0.0
        
        # Sort draws by date if possible
        sorted_draws = self._sort_draws_by_date(draws)
        
        # Use only the backtest window size
        test_draws = sorted_draws[-self.backtest_window:] if len(sorted_draws) > self.backtest_window else sorted_draws
        
        # We'll use a sliding window approach:
        # For each draw, we'll use all previous draws to make a prediction,
        # then score how well we predicted the current draw
        total_score = 0.0
        tests_run = 0
        
        # Start testing after we have at least 10 draws for training
        min_training_size = 10
        
        for i in range(min_training_size, len(test_draws)):
            # Training data is all draws before this test draw
            train_data = test_draws[:i]
            
            # Test draw is the current draw
            test_draw = test_draws[i]
            
            # Get the actual numbers from the test draw
            actual_numbers = self._extract_numbers(test_draw)
            if not actual_numbers:
                continue
            
            # Get the pick count based on the game type
            pick_count = len(actual_numbers)
            
            # Make prediction using the strategy
            try:
                predicted_numbers = strategy_func(train_data, pick_count)
                
                # Score the prediction
                score = self._score_prediction(predicted_numbers, actual_numbers)
                total_score += score
                tests_run += 1
            except Exception as e:
                logger.warning(f"Error during backtesting: {e}")
                continue
        
        # Calculate average score
        avg_score = total_score / tests_run if tests_run > 0 else 0.0
        
        return avg_score
    
    def _score_prediction(self, predicted: List[int], actual: List[int]) -> float:
        """
        Score a prediction against actual draw numbers
        
        Scoring system:
        - 4+ matches: 1.0 points
        - 3 matches: 0.7 points
        - 2 matches: 0.3 points
        - <2 matches: 0.0 points
        
        Args:
            predicted: List of predicted numbers
            actual: List of actual drawn numbers
            
        Returns:
            Score between 0.0 and 1.0
        """
        if not predicted or not actual:
            return 0.0
        
        # Count matches
        matches = len(set(predicted) & set(actual))
        
        # Score based on matches
        if matches >= 4:
            return 1.0
        elif matches == 3:
            return 0.7
        elif matches == 2:
            return 0.3
        else:
            return 0.0
    
    def _sort_draws_by_date(self, draws: List[Dict]) -> List[Dict]:
        """Sort draws by date (oldest first)"""
        dated_draws = []
        
        for draw in draws:
            date_str = draw.get('date', '')
            if not date_str:
                continue
            
            date_obj = self._parse_date(date_str)
            if not date_obj:
                continue
            
            dated_draws.append((date_obj, draw))
        
        # Sort by date
        dated_draws.sort(key=lambda x: x[0])
        
        # Return just the draws
        return [draw for _, draw in dated_draws]
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string with multiple format support"""
        if not date_str:
            return None
            
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
    
    def _extract_numbers(self, draw: Dict) -> List[int]:
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
    
    def _random_strategy(self, draws: List[Dict], pick_count: int = 6) -> List[int]:
        """
        Random number selection strategy (baseline)
        
        Args:
            draws: List of draw dictionaries (unused)
            pick_count: Number of numbers to pick
            
        Returns:
            List of random numbers
        """
        # Determine game type from first draw
        game_type = '649'  # Default
        
        if draws:
            if 'game' in draws[0]:
                game = draws[0]['game'].lower()
                if 'max' in game:
                    game_type = 'max'
            else:
                # Try to infer from number count in first draw with numbers
                for draw in draws:
                    numbers = self._extract_numbers(draw)
                    if numbers:
                        if len(numbers) == 7:
                            game_type = 'max'
                        break
        
        # Get valid number range for the game
        if game_type == 'max':
            number_range = list(range(1, 51))  # 1-50 for Lotto Max
            pick_count = 7 if pick_count < 7 else pick_count  # Ensure at least 7 numbers for Max
        else:
            number_range = list(range(1, 50))  # 1-49 for Lotto 649
            pick_count = 6 if pick_count < 6 else pick_count  # Ensure at least 6 numbers for 649
        
        # Randomly select numbers
        return random.sample(number_range, pick_count)
    
    def get_strategy_name(self, strategy_key: str) -> str:
        """Get the display name for a strategy"""
        return self.strategy_names.get(strategy_key, strategy_key.title())
    
    def get_all_strategies(self) -> Dict[str, str]:
        """Get all available strategies with their display names"""
        return {key: self.get_strategy_name(key) for key in self.strategies.keys()}
    
    def save_performance_history(self, filename: str = "strategy_performance.json") -> bool:
        """Save performance history to a file"""
        try:
            with open(filename, 'w') as f:
                json.dump(self.performance_history, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving performance history: {e}")
            return False
    
    def load_performance_history(self, filename: str = "strategy_performance.json") -> bool:
        """Load performance history from a file"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    self.performance_history = json.load(f)
                return True
            return False
        except Exception as e:
            logger.error(f"Error loading performance history: {e}")
            return False
    
    def get_performance_summary(self, game: str = None) -> Dict[str, Any]:
        """
        Get a summary of strategy performance
        
        Args:
            game: Optional game code to filter by
            
        Returns:
            Dictionary with performance summary
        """
        if not self.performance_history:
            return {'error': 'No performance history available'}
        
        # Filter by game if specified
        history = self.performance_history.get(game, {}) if game else self.performance_history
        
        if not history:
            return {'error': f'No performance history for game: {game}'}
        
        # Count strategy wins
        strategy_wins = {}
        strategy_scores = {}
        
        for game_code, game_history in history.items():
            for timestamp, result in game_history.items():
                best_strategy = result.get('best_strategy')
                if best_strategy:
                    strategy_wins[best_strategy] = strategy_wins.get(best_strategy, 0) + 1
                
                scores = result.get('scores', {})
                for strategy, score in scores.items():
                    if strategy not in strategy_scores:
                        strategy_scores[strategy] = []
                    strategy_scores[strategy].append(score)
        
        # Calculate average scores
        avg_scores = {}
        for strategy, scores in strategy_scores.items():
            if scores:
                avg_scores[strategy] = sum(scores) / len(scores)
        
        # Sort strategies by average score
        sorted_strategies = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'strategy_wins': strategy_wins,
            'avg_scores': avg_scores,
            'best_strategy': sorted_strategies[0][0] if sorted_strategies else None,
            'strategy_ranking': [s[0] for s in sorted_strategies]
        }