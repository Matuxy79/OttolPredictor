"""Integration tests for complete workflow"""

import unittest
import os
import sys
import pandas as pd
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_manager import LotteryDataManager, get_data_manager
from core.predictor import LottoPredictor
from strategies.adaptive_selector import AdaptiveStrategySelector
from strategies.uniform import uniform_frequency
from strategies.recency_weighted import recency_weighted_frequency
from strategies.era_based import era_weighted_frequency

class TestIntegration(unittest.TestCase):
    """Test complete workflow from data loading to prediction"""
    
    def setUp(self):
        """Set up test environment"""
        self.data_manager = get_data_manager()
        self.predictor = LottoPredictor()
        self.strategy_selector = AdaptiveStrategySelector()
    
    def test_pdf_to_prediction_workflow(self):
        """Test complete pipeline: PDF → Data Manager → Predictor → Results"""
        # Load data for 649
        draws = self.data_manager.load_game_data('649')
        
        # Verify data was loaded
        self.assertFalse(draws.empty, "No data loaded from PDF/CSV")
        
        # Generate prediction
        prediction = self.predictor.predict_numbers('649')
        
        # Verify prediction format
        self.assertIn('predicted_numbers', prediction, "Prediction missing 'predicted_numbers' field")
        self.assertIn('strategy_used', prediction, "Prediction missing 'strategy_used' field")
        self.assertIn('confidence', prediction, "Prediction missing 'confidence' field")
        self.assertIn('explanation', prediction, "Prediction missing 'explanation' field")
        self.assertIn('metadata', prediction, "Prediction missing 'metadata' field")
        
        # Verify prediction numbers
        numbers = prediction['predicted_numbers']
        self.assertEqual(len(numbers), 6, "Prediction should have 6 numbers for 649")
        self.assertTrue(all(1 <= n <= 49 for n in numbers), "Numbers should be in range 1-49 for 649")
        self.assertEqual(len(set(numbers)), 6, "Numbers should be unique")
    
    def test_data_consistency(self):
        """Verify PDF and live data don't conflict"""
        # Load data for 649
        data = self.data_manager.load_game_data('649')
        
        # Check for duplicate dates
        if 'date' in data.columns:
            # Convert to datetime for proper comparison
            data['date_parsed'] = pd.to_datetime(data['date'], errors='coerce')
            
            # Count occurrences of each date
            date_counts = data['date_parsed'].value_counts()
            
            # Find duplicates
            duplicates = date_counts[date_counts > 1]
            
            # There should be no duplicates
            self.assertEqual(len(duplicates), 0, f"Found {len(duplicates)} duplicate dates")
    
    def test_gui_integration(self):
        """Ensure GUI works with new backend"""
        # This is a basic smoke test to ensure the components can be imported
        # A full GUI test would require a QApplication instance
        
        try:
            from gui.main_window import SaskatoonLottoPredictor
            from gui.strategy_dashboard import StrategyDashboard
            
            # If we got here without errors, the imports work
            self.assertTrue(True, "GUI components imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import GUI components: {e}")
    
    def test_strategy_selection(self):
        """Test that strategy selection works"""
        # Load data for 649
        draws = self.data_manager.load_game_data('649')
        
        # Get best strategy
        best_strategy, _ = self.strategy_selector.select_best_strategy(draws, '649')
        
        # Generate prediction with best strategy
        prediction = self.predictor.predict_numbers('649', best_strategy)
        
        # Verify strategy used matches requested strategy
        self.assertEqual(prediction['strategy_used'], best_strategy, 
                         f"Prediction used {prediction['strategy_used']} instead of {best_strategy}")
    
    def test_all_strategies(self):
        """Test that all strategies produce valid predictions"""
        # Load data for 649
        draws = self.data_manager.load_game_data('649')
        
        # Test each strategy
        for strategy_name, strategy_func in self.strategy_selector.strategies.items():
            # Generate prediction with this strategy
            prediction = self.predictor.predict_numbers('649', strategy_name)
            
            # Verify prediction format
            self.assertIn('predicted_numbers', prediction, 
                          f"Strategy {strategy_name} missing 'predicted_numbers' field")
            
            # Verify prediction numbers
            numbers = prediction['predicted_numbers']
            self.assertEqual(len(numbers), 6, 
                             f"Strategy {strategy_name} should have 6 numbers for 649")
            self.assertTrue(all(1 <= n <= 49 for n in numbers), 
                            f"Strategy {strategy_name} numbers should be in range 1-49 for 649")
            self.assertEqual(len(set(numbers)), 6, 
                             f"Strategy {strategy_name} numbers should be unique")

if __name__ == '__main__':
    unittest.main()