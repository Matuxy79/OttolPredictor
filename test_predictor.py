"""
Test script for the new SmartPredictor implementation.
This script tests the prediction strategies and ensures they work correctly.
"""

import logging
from data_manager import get_data_manager
from predictor import SmartPredictor, generate_lottery_prediction

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_smart_predictor():
    """Test the SmartPredictor class with different strategies"""
    
    # Initialize the predictor
    data_manager = get_data_manager()
    predictor = SmartPredictor(data_manager)
    
    # Test with different games and strategies
    games = ['649', 'max']
    strategies = ['random', 'hot_cold', 'frequency', 'balanced']
    
    for game in games:
        logger.info(f"Testing predictions for game: {game}")
        
        # Test each strategy
        for strategy in strategies:
            logger.info(f"Testing strategy: {strategy}")
            prediction = predictor.generate_prediction(game, strategy)
            
            # Validate the prediction
            is_valid = predictor.validate_prediction(prediction)
            logger.info(f"Prediction valid: {is_valid}")
            logger.info(f"Numbers: {prediction['numbers']}")
            logger.info(f"Confidence: {prediction['confidence']:.2f} ({prediction['confidence_stars']} stars)")
            logger.info(f"Strategy: {prediction['strategy_name']}")
            logger.info("-" * 50)
    
    # Test backward compatibility function
    logger.info("Testing backward compatibility function")
    numbers = generate_lottery_prediction('649')
    logger.info(f"Generated numbers: {numbers}")

if __name__ == "__main__":
    logger.info("Starting predictor tests")
    test_smart_predictor()
    logger.info("Predictor tests completed")