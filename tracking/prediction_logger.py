import csv
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class PredictionLogger:
    """Logs and tracks all predictions for performance analysis"""
    
    def __init__(self, log_file: str = "data/predictions.csv", db_file: str = "data/predictions.db"):
        self.log_file = Path(log_file)
        self.db_file = Path(db_file)
        
        # Ensure directories exist
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_csv()
        self._init_database()
    
    def _init_csv(self):
        """Initialize CSV file with headers if it doesn't exist"""
        if not self.log_file.exists():
            headers = [
                'timestamp', 'game', 'numbers', 'strategy', 'strategy_name',
                'confidence', 'confidence_stars', 'data_draws_count', 'version',
                'user_notes', 'is_winner', 'matches_count', 'tier_won'
            ]
            
            with open(self.log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
    
    def _init_database(self):
        """Initialize SQLite database with predictions table"""
        with sqlite3.connect(self.db_file) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    game TEXT NOT NULL,
                    numbers TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    strategy_name TEXT,
                    confidence REAL,
                    confidence_stars INTEGER,
                    data_draws_count INTEGER,
                    version TEXT,
                    user_notes TEXT,
                    is_winner BOOLEAN DEFAULT 0,
                    matches_count INTEGER DEFAULT 0,
                    tier_won TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create index for faster queries
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON predictions(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_game ON predictions(game)')
            conn.commit()
    
    def log_prediction(self, prediction: Dict, user_notes: str = ""):
        """Log a prediction to both CSV and database"""
        try:
            # Prepare data
            numbers_str = json.dumps(prediction['numbers'])
            timestamp = prediction['timestamp']
            
            # Log to CSV
            row = [
                timestamp,
                prediction['game'],
                numbers_str,
                prediction['strategy'],
                prediction.get('strategy_name', ''),
                prediction['confidence'],
                prediction['confidence_stars'],
                prediction.get('data_draws_count', 0),
                prediction.get('version', '1.0'),
                user_notes,
                '',  # is_winner - filled later
                '',  # matches_count - filled later
                ''   # tier_won - filled later
            ]
            
            with open(self.log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row)
            
            # Log to database
            with sqlite3.connect(self.db_file) as conn:
                conn.execute('''
                    INSERT INTO predictions 
                    (timestamp, game, numbers, strategy, strategy_name, confidence, 
                     confidence_stars, data_draws_count, version, user_notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    timestamp, prediction['game'], numbers_str, prediction['strategy'],
                    prediction.get('strategy_name', ''), prediction['confidence'],
                    prediction['confidence_stars'], prediction.get('data_draws_count', 0),
                    prediction.get('version', '1.0'), user_notes
                ))
                conn.commit()
            
            logger.info(f"Logged prediction: {prediction['game']} - {prediction['numbers']}")
            
        except Exception as e:
            logger.error(f"Failed to log prediction: {e}")
    
    def get_recent_predictions(self, game: str = None, days: int = 30) -> List[Dict]:
        """Get recent predictions for analysis"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                conn.row_factory = sqlite3.Row
                
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                
                if game:
                    cursor = conn.execute('''
                        SELECT * FROM predictions 
                        WHERE game = ? AND timestamp >= ? 
                        ORDER BY timestamp DESC
                    ''', (game, cutoff_date))
                else:
                    cursor = conn.execute('''
                        SELECT * FROM predictions 
                        WHERE timestamp >= ? 
                        ORDER BY timestamp DESC
                    ''', (cutoff_date,))
                
                predictions = []
                for row in cursor:
                    pred = dict(row)
                    pred['numbers'] = json.loads(pred['numbers'])
                    predictions.append(pred)
                
                return predictions
                
        except Exception as e:
            logger.error(f"Failed to get recent predictions: {e}")
            return []
    
    def update_prediction_outcome(self, prediction_id: int, actual_numbers: List[int]) -> Dict:
        """Update prediction with actual draw results"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get the prediction
                cursor = conn.execute('SELECT * FROM predictions WHERE id = ?', (prediction_id,))
                prediction = cursor.fetchone()
                
                if not prediction:
                    raise ValueError(f"Prediction {prediction_id} not found")
                
                predicted_numbers = set(json.loads(prediction['numbers']))
                actual_numbers_set = set(actual_numbers)
                
                # Calculate matches
                matches = predicted_numbers.intersection(actual_numbers_set)
                matches_count = len(matches)
                
                # Determine if winner and tier
                is_winner = matches_count >= 2  # Minimum for any prize
                tier_won = self._determine_tier(matches_count, prediction['game'])
                
                # Update database
                conn.execute('''
                    UPDATE predictions 
                    SET is_winner = ?, matches_count = ?, tier_won = ?
                    WHERE id = ?
                ''', (is_winner, matches_count, tier_won, prediction_id))
                conn.commit()
                
                result = {
                    'prediction_id': prediction_id,
                    'matches_count': matches_count,
                    'matches': list(matches),
                    'is_winner': is_winner,
                    'tier_won': tier_won
                }
                
                logger.info(f"Updated prediction {prediction_id}: {matches_count} matches, tier: {tier_won}")
                return result
                
        except Exception as e:
            logger.error(f"Failed to update prediction outcome: {e}")
            return {}
    
    def _determine_tier(self, matches_count: int, game: str) -> str:
        """Determine prize tier based on matches"""
        if game == '649':
            tiers = {
                6: "Jackpot",
                5: "Second Prize", 
                4: "Third Prize",
                3: "Fourth Prize",
                2: "Free Play"
            }
        else:  # Lotto Max
            tiers = {
                7: "Jackpot",
                6: "Second Prize",
                5: "Third Prize", 
                4: "Fourth Prize",
                3: "Fifth Prize"
            }
        
        return tiers.get(matches_count, "No Prize")
    
    def get_strategy_performance(self, days: int = 90) -> Dict:
        """Analyze performance by strategy"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                conn.row_factory = sqlite3.Row
                
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                
                cursor = conn.execute('''
                    SELECT strategy, COUNT(*) as total_predictions,
                           AVG(confidence) as avg_confidence,
                           SUM(CASE WHEN is_winner = 1 THEN 1 ELSE 0 END) as wins,
                           AVG(matches_count) as avg_matches
                    FROM predictions 
                    WHERE timestamp >= ?
                    GROUP BY strategy
                ''', (cutoff_date,))
                
                performance = {}
                for row in cursor:
                    strategy = row['strategy']
                    total = row['total_predictions']
                    
                    performance[strategy] = {
                        'total_predictions': total,
                        'avg_confidence': round(row['avg_confidence'] or 0, 3),
                        'wins': row['wins'] or 0,
                        'win_rate': round((row['wins'] or 0) / total * 100, 1) if total > 0 else 0,
                        'avg_matches': round(row['avg_matches'] or 0, 2)
                    }
                
                return performance
                
        except Exception as e:
            logger.error(f"Failed to get strategy performance: {e}")
            return {}
    
    def export_predictions_csv(self, output_file: str, game: str = None, days: int = None) -> bool:
        """Export predictions to CSV file"""
        try:
            predictions = self.get_recent_predictions(game, days or 365)
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                if not predictions:
                    return False
                
                # Write headers
                headers = list(predictions[0].keys())
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                
                # Write data
                for pred in predictions:
                    # Convert numbers list to string for CSV
                    pred_copy = pred.copy()
                    pred_copy['numbers'] = json.dumps(pred['numbers'])
                    writer.writerow(pred_copy)
            
            logger.info(f"Exported {len(predictions)} predictions to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export predictions: {e}")
            return False