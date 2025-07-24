from datetime import datetime
from core.data_manager import get_data_manager
from tracking.prediction_logger import PredictionLogger

def generate_predictions_for_year(year: int, game: str = '649'):
    """Generate predictions for a specific year and log them."""
    data_manager = get_data_manager()
    prediction_logger = PredictionLogger()

    # Load data for the year
    data = data_manager.load_game_data(game)
    data['date'] = pd.to_datetime(data['date'], errors='coerce')
    data_year = data[data['date'].dt.year == year]

    # Apply prediction strategy (example: frequency-based)
    # Replace with your actual strategy
    from strategies.frequency_strategy import FrequencyStrategy
    strategy = FrequencyStrategy()

    predicted_numbers = strategy.predict(data_year)

    # Log prediction
    prediction_logger.log_prediction(
        game=game,
        strategy=strategy.name,
        predicted_numbers=predicted_numbers,
        timestamp=datetime.now().isoformat()
    )

    # Optionally evaluate prediction success if actual data available
    results = []
    data_manager = get_data_manager()
    selector = AdaptiveStrategySelector()
    logger = PredictionLogger()

    # Load all data for the game
    df = data_manager.load_game_data(game)
    if df.empty or 'date' not in df.columns:
        return []

    # Validate and normalize all draw records to canonical schema
    from utils.data_validation import validate_draw_record
    df = df.apply(lambda row: validate_draw_record(row.to_dict()), axis=1)
    import pandas as pd
    df = pd.DataFrame(list(df))  # Ensure DataFrame after apply

    df['date_temp'] = pd.to_datetime(df['date'], errors='coerce')
    mask = (df['date_temp'] >= pd.to_datetime(start_date)) & (df['date_temp'] <= pd.to_datetime(end_date))
    draws_in_range = df[mask].sort_values('date_temp')
    if draws_in_range.empty:
        return []

    for _, draw in draws_in_range.iterrows():
        # Only use data up to (but not including) this draw for prediction
        draw_date = draw['date_temp']
        historical_draws = df[df['date_temp'] < draw_date].to_dict(orient='records')
        historical_draws = [validate_draw_record(d) for d in historical_draws]
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
