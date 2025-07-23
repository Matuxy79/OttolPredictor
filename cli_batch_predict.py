"""
CLI tool to batch-generate, log, and compare predictions for all strategies
"""
import os
import json
from datetime import datetime
from core.predictor import LottoPredictor
from tracking.prediction_logger import PredictionRecord

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def main(game='max', n_predictions=100):
    predictor = LottoPredictor()
    strategies = predictor.strategy_selector.strategies
    log_dir = os.path.join('data', 'prediction_logs')
    ensure_dir(log_dir)
    today = datetime.now().strftime('%Y-%m-%d')
    results = {}
    for strat_name, strat_func in strategies.items():
        strat_results = []
        for i in range(n_predictions):
            pred = predictor.predict_numbers(game, strategy=strat_name)
            record = PredictionRecord(
                strategy=strat_name,
                game=game,
                predicted_numbers=pred.get('numbers', pred.get('predicted_numbers', [])),
                timestamp=datetime.now().isoformat()
            )
            strat_results.append(record.to_dict())
        # Save predictions for this strategy
        log_file = os.path.join(log_dir, f'{game}_{strat_name}_{today}.json')
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(strat_results, f, indent=2)
        results[strat_name] = log_file
    print(f"Batch predictions saved for {game}:")
    for strat, file in results.items():
        print(f"  {strat}: {file}")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Batch generate and log predictions for all strategies.')
    parser.add_argument('--game', type=str, default='max', help='Game code (e.g., max, 649)')
    parser.add_argument('--n', type=int, default=100, help='Number of predictions per strategy')
    args = parser.parse_args()
    main(game=args.game, n_predictions=args.n)
