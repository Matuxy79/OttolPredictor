"""Tests for strategy performance and backtesting"""

import unittest
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_manager import LotteryDataManager, get_data_manager
from strategies.adaptive_selector import AdaptiveStrategySelector
from strategies.uniform import uniform_frequency
from strategies.recency_weighted import recency_weighted_frequency, get_optimal_lambda
from strategies.era_based import era_weighted_frequency

class TestStrategyPerformance(unittest.TestCase):
    """Test strategy performance and backtesting"""
    
    def setUp(self):
        """Set up test environment"""
        self.data_manager = get_data_manager()
        self.strategy_selector = AdaptiveStrategySelector()
        
        # Load test data
        self.data_649 = self.data_manager.load_game_data('649')
        self.data_max = self.data_manager.load_game_data('max')
        
        # Skip tests if no data
        if self.data_649.empty:
            self.skipTest("No 649 data available for testing")
        
    def test_strategy_backtesting(self):
        """Verify backtesting logic is sound"""
        # Get a sample of draws for testing
        draws = self.data_649.to_dict('records')
        
        if len(draws) < 50:
            self.skipTest("Not enough data for backtesting")
            
        # Run backtesting on each strategy
        for strategy_name, strategy_func in self.strategy_selector.strategies.items():
            score = self.strategy_selector._backtest_strategy(strategy_func, draws)
            
            # Score should be between 0 and 1
            self.assertGreaterEqual(score, 0.0, f"Strategy {strategy_name} has negative score")
            self.assertLessEqual(score, 1.0, f"Strategy {strategy_name} has score > 1.0")
            
            # Log the score for manual review
            print(f"Strategy {strategy_name} backtest score: {score:.4f}")
    
    def test_prediction_quality(self):
        """Check that predictions aren't random"""
        # Get a sample of draws for testing
        draws = self.data_649.to_dict('records')
        
        if len(draws) < 50:
            self.skipTest("Not enough data for quality testing")
        
        # Split data into training and testing sets
        split_idx = int(len(draws) * 0.8)
        train_draws = draws[:split_idx]
        test_draws = draws[split_idx:]
        
        # Track matches for each strategy
        strategy_matches = {}
        
        # Test each strategy
        for strategy_name, strategy_func in self.strategy_selector.strategies.items():
            total_matches = 0
            
            # For each test draw, predict using training data and compare
            for i, test_draw in enumerate(test_draws):
                # Get actual numbers
                actual_numbers = []
                if 'numbers' in test_draw:
                    numbers = test_draw['numbers']
                    if isinstance(numbers, str) and numbers.startswith('[') and numbers.endswith(']'):
                        # Parse string representation of list
                        nums_str = numbers.strip('[]')
                        actual_numbers = [int(n.strip()) for n in nums_str.split(',') if n.strip()]
                    elif isinstance(numbers, list):
                        actual_numbers = numbers
                
                if not actual_numbers:
                    continue
                
                # Predict using training data
                pick_count = len(actual_numbers)
                predicted = strategy_func(train_draws, pick_count)
                
                # Count matches
                matches = len(set(predicted) & set(actual_numbers))
                total_matches += matches
            
            # Calculate average matches per draw
            avg_matches = total_matches / len(test_draws) if test_draws else 0
            strategy_matches[strategy_name] = avg_matches
            
            # Should have at least some matches (better than random)
            self.assertGreater(avg_matches, 0.0, 
                              f"Strategy {strategy_name} has no matches")
            
            # Log for manual review
            print(f"Strategy {strategy_name} average matches: {avg_matches:.2f}")
        
        # Best strategy should have more matches than random
        best_strategy = max(strategy_matches.items(), key=lambda x: x[1])[0]
        random_matches = strategy_matches.get('random', 0)
        
        if 'random' in strategy_matches:
            self.assertGreater(strategy_matches[best_strategy], random_matches,
                              f"Best strategy {best_strategy} not better than random")
            
            print(f"Best strategy: {best_strategy} with {strategy_matches[best_strategy]:.2f} matches")
            print(f"Random strategy: {random_matches:.2f} matches")
    
    def test_optimal_lambda(self):
        """Test that optimal lambda selection works"""
        # Get a sample of draws for testing
        draws = self.data_649.to_dict('records')
        
        if len(draws) < 100:
            self.skipTest("Not enough data for lambda optimization")
        
        # Get optimal lambda
        best_lambda, results = get_optimal_lambda(draws)
        
        # Lambda should be in reasonable range
        self.assertGreaterEqual(best_lambda, 0.1, "Lambda too small")
        self.assertLessEqual(best_lambda, 1.0, "Lambda too large")
        
        # Results should contain accuracy data
        for lambda_val, metrics in results.items():
            self.assertIn('accuracy', metrics, f"Missing accuracy for lambda {lambda_val}")
            self.assertGreaterEqual(metrics['accuracy'], 0.0, f"Negative accuracy for lambda {lambda_val}")
            self.assertLessEqual(metrics['accuracy'], 1.0, f"Accuracy > 1.0 for lambda {lambda_val}")
        
        # Log for manual review
        print(f"Optimal lambda: {best_lambda}")
        for lambda_val, metrics in sorted(results.items()):
            print(f"Lambda {lambda_val}: accuracy {metrics['accuracy']:.4f}")
    
    def test_strategy_comparison(self):
        """Compare strategies and verify adaptive selection works"""
        # Get a sample of draws for testing
        draws = self.data_649.to_dict('records')
        
        if len(draws) < 50:
            self.skipTest("Not enough data for strategy comparison")
        
        # Get best strategy
        best_strategy, strategy_func = self.strategy_selector.select_best_strategy(draws, '649')
        
        # Should return a valid strategy
        self.assertIn(best_strategy, self.strategy_selector.strategies, 
                     f"Invalid strategy selected: {best_strategy}")
        
        # Get performance summary
        performance = self.strategy_selector.get_performance_summary('649')
        
        # Should have performance data
        self.assertIn('strategy_ranking', performance, "Missing strategy ranking")
        self.assertIn('avg_scores', performance, "Missing average scores")
        
        # Best strategy from summary should match selected strategy
        if 'best_strategy' in performance:
            self.assertEqual(performance['best_strategy'], best_strategy,
                            f"Best strategy mismatch: {performance['best_strategy']} vs {best_strategy}")
        
        # Log for manual review
        print(f"Best strategy: {best_strategy}")
        if 'avg_scores' in performance:
            for strategy, score in sorted(performance['avg_scores'].items(), key=lambda x: x[1], reverse=True):
                print(f"Strategy {strategy}: score {score:.4f}")

if __name__ == '__main__':
    unittest.main()