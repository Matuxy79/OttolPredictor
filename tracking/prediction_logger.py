import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import pandas as pd

logger = logging.getLogger(__name__)

class PredictionRecord:
    """Individual prediction record with outcome tracking"""

    def __init__(self, strategy: str, game: str, predicted_numbers: List[int], 
                 timestamp: str = None, actual_numbers: List[int] = None):
        self.strategy = strategy
        self.game = game
        self.predicted_numbers = predicted_numbers
        self.timestamp = timestamp or datetime.now().isoformat()
        self.actual_numbers = actual_numbers or []
        self.match_count = None
        self.did_win = False
        self.evaluated = False

        # Auto-evaluate if we have actual numbers
        if actual_numbers:
            self.evaluate_prediction(actual_numbers)

    def evaluate_prediction(self, actual_numbers: List[int]):
        """Evaluate prediction against actual draw results"""
        if not actual_numbers:
            return

        self.actual_numbers = actual_numbers
        self.match_count = len(set(self.predicted_numbers) & set(actual_numbers))
        self.did_win = self.match_count >= 3  # Adjust win criteria as needed
        self.evaluated = True

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON storage"""
        return {
            'strategy': self.strategy,
            'game': self.game,
            'predicted_numbers': self.predicted_numbers,
            'timestamp': self.timestamp,
            'actual_numbers': self.actual_numbers,
            'match_count': self.match_count,
            'did_win': self.did_win,
            'evaluated': self.evaluated
        }

    @classmethod
    def from_dict(cls, data: Dict):
        """Create from dictionary"""
        record = cls(
            strategy=data['strategy'],
            game=data['game'],
            predicted_numbers=data['predicted_numbers'],
            timestamp=data['timestamp'],
            actual_numbers=data.get('actual_numbers', [])
        )
        record.match_count = data.get('match_count')
        record.did_win = data.get('did_win', False)
        record.evaluated = data.get('evaluated', False)
        return record


class PredictionLogger:
    """Manages prediction history and performance tracking"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.predictions_file = os.path.join(data_dir, "prediction_history.json")
        self.logger = logging.getLogger(__name__)
        self.predictions: List[PredictionRecord] = []

        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)

        # Load existing predictions
        self.load_predictions()

    def log_prediction(self, strategy: str, game: str, predicted_numbers: List[int]) -> str:
        """Log a new prediction"""
        record = PredictionRecord(strategy, game, predicted_numbers)
        self.predictions.append(record)
        self.save_predictions()

        self.logger.info(f"Logged prediction: {strategy} for {game} - {predicted_numbers}")
        return record.timestamp

    def evaluate_predictions(self, data_manager):
        """Evaluate pending predictions against recent draws"""
        try:
            updated_count = 0

            for prediction in self.predictions:
                if prediction.evaluated:
                    continue

                # Check if we have draw results for this prediction date
                prediction_date = datetime.fromisoformat(prediction.timestamp.split('T')[0])

                # Get recent draws for this game
                game_data = data_manager.load_game_data(prediction.game)
                if game_data.empty:
                    continue

                # Look for draws after the prediction date using the 'date' field
                game_data['date_dt'] = pd.to_datetime(game_data['date'], errors='coerce')
                recent_draws = game_data[
                    game_data['date_dt'] > prediction_date
                ].sort_values('date_dt')

                if not recent_draws.empty:
                    # Use the first draw after prediction
                    latest_draw = recent_draws.iloc[0]
                    actual_numbers = latest_draw.get('numbers_list', [])

                    if actual_numbers:
                        prediction.evaluate_prediction(actual_numbers)
                        updated_count += 1

            if updated_count > 0:
                self.save_predictions()
                self.logger.info(f"Evaluated {updated_count} predictions")

        except Exception as e:
            self.logger.error(f"Error evaluating predictions: {e}")

    def get_recent_predictions(self, game: str = None, days: int = 30) -> List[Dict]:
        """Get recent predictions with optional game filter"""
        cutoff_date = datetime.now() - timedelta(days=days)

        recent = []
        for pred in self.predictions:
            pred_date = datetime.fromisoformat(pred.timestamp.split('T')[0])
            if pred_date >= cutoff_date:
                if game is None or pred.game == game:
                    recent.append(pred.to_dict())

        return sorted(recent, key=lambda x: x['timestamp'], reverse=True)

    def get_strategy_performance(self, days: int = 30) -> Dict:
        """Get performance statistics by strategy"""
        recent_predictions = self.get_recent_predictions(days=days)

        performance = {}
        for pred in recent_predictions:
            if not pred['evaluated']:
                continue

            strategy = pred['strategy']
            if strategy not in performance:
                performance[strategy] = {
                    'total_predictions': 0,
                    'wins': 0,
                    'total_matches': 0,
                    'win_rate': 0,
                    'avg_matches': 0
                }

            stats = performance[strategy]
            stats['total_predictions'] += 1
            stats['total_matches'] += pred.get('match_count', 0)
            if pred.get('did_win', False):
                stats['wins'] += 1

        # Calculate rates
        for strategy, stats in performance.items():
            if stats['total_predictions'] > 0:
                stats['win_rate'] = (stats['wins'] / stats['total_predictions']) * 100
                stats['avg_matches'] = stats['total_matches'] / stats['total_predictions']

        return performance

    def load_predictions(self):
        """Load predictions from JSON file"""
        if not os.path.exists(self.predictions_file):
            return

        try:
            with open(self.predictions_file, 'r') as f:
                data = json.load(f)
                self.predictions = [PredictionRecord.from_dict(item) for item in data]

            self.logger.info(f"Loaded {len(self.predictions)} prediction records")

        except Exception as e:
            self.logger.error(f"Error loading predictions: {e}")
            self.predictions = []

    def save_predictions(self):
        """Save predictions to JSON file"""
        try:
            data = [pred.to_dict() for pred in self.predictions]
            with open(self.predictions_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            self.logger.error(f"Error saving predictions: {e}")

    def get_performance_summary(self, game: str = None, days: int = None) -> Dict:
        """Get performance summary, optionally filtered by game and days (for future-proofing)."""
        # Filter predictions by game and days if provided
        filtered = self.predictions
        if game:
            filtered = [p for p in filtered if getattr(p, 'game', None) == game]
        if days is not None:
            cutoff = datetime.now() - timedelta(days=days)
            filtered = [p for p in filtered if datetime.fromisoformat(p.timestamp.split('T')[0]) >= cutoff]

        if not filtered:
            return {
                'total_predictions': 0,
                'evaluated_predictions': 0,
                'total_wins': 0,
                'overall_win_rate': 0.0,
                'best_strategy': None
            }

        evaluated = [p for p in filtered if getattr(p, 'evaluated', False)]
        wins = [p for p in evaluated if getattr(p, 'did_win', False)]

        summary = {
            'total_predictions': len(filtered),
            'evaluated_predictions': len(evaluated),
            'total_wins': len(wins),
            'overall_win_rate': (len(wins) / len(evaluated) * 100) if evaluated else 0.0,
            'best_strategy': None
        }

        # Find best strategy in filtered set
        strategy_performance = self.get_strategy_performance(days=days or 365)
        if game:
            # Only consider strategies for this game
            strategy_performance = {k: v for k, v in strategy_performance.items() if k}
        if strategy_performance:
            best_strategy = max(strategy_performance.items(), key=lambda x: x[1]['win_rate'])
            summary['best_strategy'] = {
                'name': best_strategy[0],
                'win_rate': best_strategy[1]['win_rate']
            }

        return summary
