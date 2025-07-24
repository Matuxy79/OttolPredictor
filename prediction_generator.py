


def batch_generate_predictions_for_date_range(game: str, start_date: str, end_date: str):
    """
    For a given game, generate and log predictions for all draws in a date range.
    Returns a list of dicts with prediction, actual, and metadata for each draw.
    Dates should be in 'YYYY-MM-DD' format.
    """
    from core.data_manager import get_data_manager
    from strategies.adaptive_selector import AdaptiveStrategySelector
    from tracking.prediction_logger import PredictionLogger
    import pandas as pd
    from datetime import datetime

    results = []
    data_manager = get_data_manager()
    selector = AdaptiveStrategySelector()
    logger = PredictionLogger()

    # Load all data for the game
    df = data_manager.load_game_data(game)
    if df.empty or 'numbers_list' not in df.columns or 'date' not in df.columns:
        return []
    df['date_temp'] = pd.to_datetime(df['date'], errors='coerce')
    mask = (df['date_temp'] >= pd.to_datetime(start_date)) & (df['date_temp'] <= pd.to_datetime(end_date))
    draws_in_range = df[mask].sort_values('date_temp')
    if draws_in_range.empty:
        return []
    draws_list = df.to_dict(orient='records')

    for _, draw in draws_in_range.iterrows():
        # Only use data up to (but not including) this draw for prediction
        draw_date = draw['date_temp']
        historical_draws = df[df['date_temp'] < draw_date].to_dict(orient='records')
        if not historical_draws:
            continue
        strategy_name, strategy_func = selector.select_best_strategy(historical_draws, game)
        pick_count = len(draw['numbers_list'])
        predicted_numbers = strategy_func(historical_draws, pick_count)
        log_time = logger.log_prediction(strategy_name, game, predicted_numbers)
        results.append({
            'game': game,
            'strategy': strategy_name,
            'prediction': predicted_numbers,
            'actual': draw['numbers_list'],
            'draw_date': draw['date'],
            'timestamp': log_time
        })
    return results

# Example usage:
# batch_generate_predictions_for_date_range('649', '2024-01-01', '2024-06-30')
