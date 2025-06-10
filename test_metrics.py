"""
Test script for the metrics module

This script tests the functionality of the metrics module by generating
sample predictions and comparing them with actual draws to calculate
uplift percentages and statistical significance.
"""

import logging
from metrics import GameType, PredictionMetrics, quick_uplift_check, validate_predictions_format

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_metrics_basic():
    """Test basic metrics functionality"""
    logger.info("Testing basic metrics functionality")
    
    # Sample data
    smart_preds = [[1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12]]
    random_preds = [[13, 14, 15, 16, 17, 18], [19, 20, 21, 22, 23, 24]]
    actual_draws = [[1, 2, 25, 26, 27, 28], [7, 8, 29, 30, 31, 32]]
    
    # Create metrics calculator
    metrics = PredictionMetrics()
    
    # Test count_matches
    matches = metrics.count_matches(smart_preds[0], actual_draws[0])
    logger.info(f"Matches between {smart_preds[0]} and {actual_draws[0]}: {matches}")
    
    # Test calculate_hit_rate
    hit_rate = metrics.calculate_hit_rate(smart_preds, actual_draws, 2)
    logger.info(f"Hit rate for tier 2: {hit_rate:.4f}")
    
    # Test wilson_confidence_interval
    ci = metrics.wilson_confidence_interval(0.5, 100)
    logger.info(f"Wilson CI for p=0.5, n=100: {ci}")
    
    # Test calculate_tier_uplift
    result = metrics.calculate_tier_uplift(smart_preds, random_preds, actual_draws, 2)
    logger.info(f"Tier 2 uplift: {result.uplift_percent:.2f}%, Significant: {result.is_significant}")
    
    # Test quick_uplift_check
    quick_result = quick_uplift_check(smart_preds, random_preds, actual_draws)
    logger.info(f"Quick uplift check: {quick_result}")
    
    return True

def test_metrics_realistic():
    """Test metrics with more realistic data"""
    logger.info("Testing metrics with realistic data")
    
    # Generate more realistic sample data
    import random
    
    # Function to generate random lottery numbers
    def generate_numbers(count, max_num):
        return sorted(random.sample(range(1, max_num + 1), count))
    
    # Generate smart predictions (biased to include some actual numbers)
    smart_preds = []
    # Generate random predictions
    random_preds = []
    # Generate actual draws
    actual_draws = []
    
    # Generate 30 sets of data
    for _ in range(30):
        # Actual draw
        actual = generate_numbers(6, 49)
        actual_draws.append(actual)
        
        # Smart prediction (include 2 numbers from actual draw to simulate better performance)
        smart = actual[:2] + generate_numbers(4, 49)
        # Ensure no duplicates
        while len(set(smart)) < 6:
            smart = actual[:2] + generate_numbers(4, 49)
        smart_preds.append(sorted(smart))
        
        # Random prediction
        random_preds.append(generate_numbers(6, 49))
    
    # Test with realistic data
    metrics = PredictionMetrics()
    report = metrics.generate_uplift_report(
        smart_preds, random_preds, actual_draws, GameType.LOTTO_649
    )
    
    # Print summary
    logger.info("\nUplift Report:")
    logger.info(metrics.format_uplift_summary(report))
    
    # Test quick_uplift_check
    quick_result = quick_uplift_check(smart_preds, random_preds, actual_draws)
    logger.info(f"Quick uplift check: {quick_result}")
    
    return True

def test_validation():
    """Test prediction validation"""
    logger.info("Testing prediction validation")
    
    # Valid predictions
    valid_preds = [[1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12]]
    errors = validate_predictions_format(valid_preds, GameType.LOTTO_649)
    logger.info(f"Valid predictions errors: {errors}")
    
    # Invalid predictions
    invalid_preds = [
        [1, 2, 3, 4, 5],  # Too few numbers
        [1, 2, 3, 4, 5, 50],  # Number out of range
        [1, 2, 3, 4, 5, 5],  # Duplicate number
        "not a list"  # Not a list
    ]
    errors = validate_predictions_format(invalid_preds, GameType.LOTTO_649)
    logger.info(f"Invalid predictions errors: {errors}")
    
    return True

if __name__ == "__main__":
    logger.info("Starting metrics tests")
    
    test_metrics_basic()
    test_metrics_realistic()
    test_validation()
    
    logger.info("All tests completed")