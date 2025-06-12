import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch

from predictor import SmartPredictor
from algorithms.prediction_strategies import RandomStrategy, HotColdStrategy, FrequencyStrategy, BalancedStrategy
from tracking.prediction_logger import PredictionLogger

class TestPredictionStrategies(unittest.TestCase):
    """Test individual prediction strategies"""

    def setUp(self):
        self.sample_data = {
            'numbers_list': [
                [1, 5, 12, 23, 34, 45],
                [2, 8, 15, 22, 31, 44],
                [3, 7, 14, 25, 33, 42],
                [1, 9, 16, 24, 35, 43],
                [4, 6, 13, 26, 32, 41]
            ]
        }

    def test_random_strategy(self):
        """Test random strategy produces valid numbers"""
        strategy = RandomStrategy()
        numbers = strategy.predict(self.sample_data, count=6)

        self.assertEqual(len(numbers), 6)
        self.assertTrue(all(1 <= num <= 49 for num in numbers))
        self.assertEqual(len(set(numbers)), 6)  # All unique

        confidence = strategy.calculate_confidence(self.sample_data, numbers)
        self.assertLessEqual(confidence, 0.2)  # Low confidence for random

    def test_hot_cold_strategy(self):
        """Test hot/cold strategy with sample data"""
        strategy = HotColdStrategy()
        numbers = strategy.predict(self.sample_data, count=6)

        self.assertEqual(len(numbers), 6)
        self.assertTrue(all(1 <= num <= 49 for num in numbers))
        self.assertEqual(len(set(numbers)), 6)  # All unique

        confidence = strategy.calculate_confidence(self.sample_data, numbers)
        self.assertGreater(confidence, 0.2)  # Should have higher confidence than random

    def test_frequency_strategy(self):
        """Test frequency-based strategy"""
        strategy = FrequencyStrategy()
        numbers = strategy.predict(self.sample_data, count=6)

        self.assertEqual(len(numbers), 6)
        self.assertTrue(all(1 <= num <= 49 for num in numbers))
        self.assertEqual(len(set(numbers)), 6)  # All unique

    def test_balanced_strategy(self):
        """Test balanced strategy combines others"""
        strategy = BalancedStrategy()
        numbers = strategy.predict(self.sample_data, count=6)

        self.assertEqual(len(numbers), 6)
        self.assertTrue(all(1 <= num <= 49 for num in numbers))
        self.assertEqual(len(set(numbers)), 6)  # All unique

class TestSmartPredictor(unittest.TestCase):
    """Test main predictor class"""

    def setUp(self):
        self.mock_data_manager = Mock()
        self.mock_data_manager.load_game_data.return_value = {
            'numbers_list': [[1, 5, 12, 23, 34, 45], [2, 8, 15, 22, 31, 44]]
        }
        self.predictor = SmartPredictor(self.mock_data_manager)

    def test_generate_prediction_649(self):
        """Test prediction generation for Lotto 6/49"""
        prediction = self.predictor.generate_prediction('649', 'balanced')

        self.assertIn('numbers', prediction)
        self.assertIn('confidence', prediction)
        self.assertIn('strategy', prediction)
        self.assertIn('timestamp', prediction)

        self.assertEqual(len(prediction['numbers']), 6)
        self.assertTrue(all(1 <= num <= 49 for num in prediction['numbers']))
        self.assertEqual(prediction['game'], '649')

    def test_generate_prediction_max(self):
        """Test prediction generation for Lotto Max"""
        prediction = self.predictor.generate_prediction('max', 'frequency')

        self.assertEqual(len(prediction['numbers']), 7)
        self.assertTrue(all(1 <= num <= 50 for num in prediction['numbers']))
        self.assertEqual(prediction['game'], 'max')

    def test_fallback_on_error(self):
        """Test fallback when data loading fails"""
        self.mock_data_manager.load_game_data.side_effect = Exception("Data error")

        prediction = self.predictor.generate_prediction('649')

        self.assertIn('numbers', prediction)
        self.assertEqual(len(prediction['numbers']), 6)
        self.assertTrue(prediction.get('error', False))

    def test_validate_prediction(self):
        """Test prediction validation"""
        valid_prediction = {
            'numbers': [1, 5, 12, 23, 34, 45],
            'game': '649',
            'strategy': 'balanced',
            'confidence': 0.7,
            'timestamp': '2025-01-01T12:00:00'
        }

        self.assertTrue(self.predictor.validate_prediction(valid_prediction))

        # Test invalid cases
        invalid_prediction = valid_prediction.copy()
        invalid_prediction['numbers'] = [1, 2]  # Too few numbers
        self.assertFalse(self.predictor.validate_prediction(invalid_prediction))

class TestPredictionLogger(unittest.TestCase):
    """Test prediction logging system"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.csv_file = Path(self.temp_dir) / "test_predictions.csv"
        self.db_file = Path(self.temp_dir) / "test_predictions.db"

        self.logger = PredictionLogger(
            log_file=str(self.csv_file),
            db_file=str(self.db_file)
        )

        # Use current timestamp to ensure it's within the time range for get_recent_predictions
        from datetime import datetime
        current_time = datetime.now().isoformat()

        self.sample_prediction = {
            'numbers': [1, 5, 12, 23, 34, 45],
            'game': '649',
            'strategy': 'balanced',
            'strategy_name': 'Balanced Strategy',
            'confidence': 0.7,
            'confidence_stars': 4,
            'timestamp': current_time,
            'data_draws_count': 100,
            'version': '1.0'
        }

    def test_log_prediction(self):
        """Test logging prediction to both CSV and database"""
        self.logger.log_prediction(self.sample_prediction, "Test prediction")

        # Check CSV file exists and has content
        self.assertTrue(self.csv_file.exists())
        with open(self.csv_file, 'r') as f:
            content = f.read()
            self.assertIn('1,5,12,23,34,45', content.replace(' ', '').replace('[', '').replace(']', ''))

        # Check database has content
        predictions = self.logger.get_recent_predictions(days=1)
        self.assertEqual(len(predictions), 1)
        self.assertEqual(predictions[0]['game'], '649')

    def test_get_recent_predictions(self):
        """Test retrieving recent predictions"""
        self.logger.log_prediction(self.sample_prediction)

        predictions = self.logger.get_recent_predictions('649', days=1)
        self.assertEqual(len(predictions), 1)
        self.assertEqual(predictions[0]['numbers'], [1, 5, 12, 23, 34, 45])

    def test_strategy_performance(self):
        """Test strategy performance analysis"""
        # Log multiple predictions with current timestamps
        from datetime import datetime, timedelta

        for i in range(5):
            pred = self.sample_prediction.copy()
            # Use timestamps from the last few days
            timestamp = (datetime.now() - timedelta(days=i)).isoformat()
            pred['timestamp'] = timestamp
            self.logger.log_prediction(pred)

        performance = self.logger.get_strategy_performance(days=30)
        self.assertIn('balanced', performance)
        self.assertEqual(performance['balanced']['total_predictions'], 5)

if __name__ == '__main__':
    unittest.main()
