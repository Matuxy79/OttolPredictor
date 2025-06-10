"""
Prediction Metrics Engine for Saskatoon Lotto Predictor

Calculates prediction uplift % with Wilson score confidence intervals to determine
if smart predictions beat random guessing in a statistically meaningful way.

Focused on Lotto 6/49 (6 numbers, 1-49) and Lotto Max (7 numbers, 1-50) only.

Author: Saskatoon Lotto Predictor Team
Date: 2024-12-22
"""

import math
import logging
from typing import List, Tuple, Dict, Optional, Union
from dataclasses import dataclass
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)

class GameType(Enum):
    """Supported lottery games"""
    LOTTO_649 = "649"
    LOTTO_MAX = "max"

@dataclass
class GameConfig:
    """Configuration for each lottery game"""
    name: str
    main_numbers: int  # How many main numbers
    number_range: Tuple[int, int]  # (min, max) for main numbers
    has_bonus: bool
    bonus_range: Optional[Tuple[int, int]] = None

# Game configurations
GAME_CONFIGS = {
    GameType.LOTTO_649: GameConfig(
        name="Lotto 6/49",
        main_numbers=6,
        number_range=(1, 49),
        has_bonus=True,
        bonus_range=(1, 49)
    ),
    GameType.LOTTO_MAX: GameConfig(
        name="Lotto Max", 
        main_numbers=7,
        number_range=(1, 50),
        has_bonus=True,
        bonus_range=(1, 50)
    )
}

@dataclass
class TierResult:
    """Results for a specific hit tier"""
    tier: int
    smart_hit_rate: float
    random_hit_rate: float
    uplift_percent: float
    smart_ci_lower: float
    smart_ci_upper: float
    random_ci_lower: float
    random_ci_upper: float
    is_significant: bool
    sample_size: int
    confidence_level: float

@dataclass
class UpliftReport:
    """Complete uplift analysis across all tiers"""
    game_type: GameType
    total_predictions: int
    total_draws: int
    tier_results: Dict[int, TierResult]
    overall_significant: bool
    data_completeness: float
    analysis_timestamp: str

class PredictionMetrics:
    """Main metrics calculation engine"""
    
    def __init__(self, confidence_level: float = 0.95, min_sample_size: int = 30):
        """
        Initialize metrics calculator
        
        Args:
            confidence_level: Statistical confidence level (default 95%)
            min_sample_size: Minimum sample size for reliable statistics
        """
        self.confidence_level = confidence_level
        self.min_sample_size = min_sample_size
        self.z_score = self._get_z_score(confidence_level)
        
    def _get_z_score(self, confidence_level: float) -> float:
        """Get z-score for given confidence level"""
        if confidence_level == 0.95:
            return 1.96
        elif confidence_level == 0.99:
            return 2.576
        elif confidence_level == 0.90:
            return 1.645
        else:
            # Approximate for other confidence levels
            from scipy.stats import norm
            return norm.ppf((1 + confidence_level) / 2)
    
    def count_matches(self, predicted: List[int], actual: List[int]) -> int:
        """
        Count how many numbers match between prediction and actual draw
        
        Args:
            predicted: List of predicted numbers
            actual: List of actual drawn numbers
            
        Returns:
            Number of matching numbers
        """
        if not predicted or not actual:
            return 0
            
        predicted_set = set(predicted)
        actual_set = set(actual)
        
        return len(predicted_set.intersection(actual_set))
    
    def calculate_hit_rate(self, 
                          predictions: List[List[int]], 
                          actual_draws: List[List[int]], 
                          tier: int) -> float:
        """
        Calculate hit rate for a specific tier (minimum matches needed)
        
        Args:
            predictions: List of prediction number sets
            actual_draws: List of actual draw number sets  
            tier: Minimum number of matches required for a "hit"
            
        Returns:
            Hit rate as a fraction (0.0 to 1.0)
        """
        if not predictions or not actual_draws:
            logger.warning("Empty predictions or draws provided")
            return 0.0
            
        if len(predictions) != len(actual_draws):
            logger.error(f"Mismatch: {len(predictions)} predictions vs {len(actual_draws)} draws")
            return 0.0
        
        hits = 0
        total = len(predictions)
        
        for pred, actual in zip(predictions, actual_draws):
            try:
                matches = self.count_matches(pred, actual)
                if matches >= tier:
                    hits += 1
            except Exception as e:
                logger.error(f"Error calculating matches for {pred} vs {actual}: {e}")
                continue
                
        hit_rate = hits / total if total > 0 else 0.0
        
        logger.debug(f"Tier {tier}: {hits}/{total} hits = {hit_rate:.4f}")
        return hit_rate
    
    def wilson_confidence_interval(self, 
                                 hit_rate: float, 
                                 sample_size: int) -> Tuple[float, float]:
        """
        Calculate Wilson score confidence interval for hit rate
        
        More accurate than normal approximation for small samples and extreme proportions.
        
        Args:
            hit_rate: Observed hit rate (0.0 to 1.0)
            sample_size: Number of trials
            
        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        if sample_size == 0:
            return (0.0, 0.0)
            
        if hit_rate < 0 or hit_rate > 1:
            logger.warning(f"Invalid hit rate: {hit_rate}")
            return (0.0, 0.0)
        
        z = self.z_score
        z_squared = z * z
        
        # Wilson score interval formula
        denominator = 1 + (z_squared / sample_size)
        
        center_adjusted = hit_rate + (z_squared / (2 * sample_size))
        
        margin_of_error = z * math.sqrt(
            (hit_rate * (1 - hit_rate) / sample_size) + 
            (z_squared / (4 * sample_size * sample_size))
        )
        
        lower = (center_adjusted - margin_of_error) / denominator
        upper = (center_adjusted + margin_of_error) / denominator
        
        # Clamp to valid probability range
        lower = max(0.0, lower)
        upper = min(1.0, upper)
        
        return (lower, upper)
    
    def confidence_intervals_overlap(self, 
                                   ci1: Tuple[float, float], 
                                   ci2: Tuple[float, float]) -> bool:
        """
        Check if two confidence intervals overlap
        
        Args:
            ci1: First confidence interval (lower, upper)
            ci2: Second confidence interval (lower, upper)
            
        Returns:
            True if intervals overlap, False if they don't
        """
        return not (ci1[1] < ci2[0] or ci2[1] < ci1[0])
    
    def calculate_tier_uplift(self,
                            smart_predictions: List[List[int]],
                            random_predictions: List[List[int]], 
                            actual_draws: List[List[int]],
                            tier: int) -> TierResult:
        """
        Calculate uplift for a specific tier with statistical significance
        
        Args:
            smart_predictions: "Smart" algorithm predictions
            random_predictions: Random baseline predictions
            actual_draws: Actual lottery draws
            tier: Minimum matches for this tier
            
        Returns:
            TierResult with uplift and significance data
        """
        # Validate inputs
        sample_size = len(actual_draws)
        if sample_size == 0:
            logger.error("No actual draws provided")
            return self._empty_tier_result(tier)
            
        if (len(smart_predictions) != sample_size or 
            len(random_predictions) != sample_size):
            logger.error(f"Sample size mismatch: smart={len(smart_predictions)}, "
                        f"random={len(random_predictions)}, draws={sample_size}")
            return self._empty_tier_result(tier)
        
        # Calculate hit rates
        smart_hr = self.calculate_hit_rate(smart_predictions, actual_draws, tier)
        random_hr = self.calculate_hit_rate(random_predictions, actual_draws, tier)
        
        # Calculate confidence intervals
        smart_ci = self.wilson_confidence_interval(smart_hr, sample_size)
        random_ci = self.wilson_confidence_interval(random_hr, sample_size)
        
        # Calculate uplift percentage
        if random_hr > 0:
            uplift_percent = ((smart_hr - random_hr) / random_hr) * 100
        else:
            uplift_percent = 0.0 if smart_hr == 0 else float('inf')
        
        # Determine statistical significance
        # Non-overlapping confidence intervals suggest significance
        is_significant = (
            not self.confidence_intervals_overlap(smart_ci, random_ci) and
            sample_size >= self.min_sample_size
        )
        
        logger.info(f"Tier {tier}: Smart={smart_hr:.4f}, Random={random_hr:.4f}, "
                   f"Uplift={uplift_percent:.2f}%, Significant={is_significant}")
        
        return TierResult(
            tier=tier,
            smart_hit_rate=smart_hr,
            random_hit_rate=random_hr,
            uplift_percent=uplift_percent,
            smart_ci_lower=smart_ci[0],
            smart_ci_upper=smart_ci[1],
            random_ci_lower=random_ci[0],
            random_ci_upper=random_ci[1],
            is_significant=is_significant,
            sample_size=sample_size,
            confidence_level=self.confidence_level
        )
    
    def _empty_tier_result(self, tier: int) -> TierResult:
        """Return empty tier result for error cases"""
        return TierResult(
            tier=tier,
            smart_hit_rate=0.0,
            random_hit_rate=0.0,
            uplift_percent=0.0,
            smart_ci_lower=0.0,
            smart_ci_upper=0.0,
            random_ci_lower=0.0,
            random_ci_upper=0.0,
            is_significant=False,
            sample_size=0,
            confidence_level=self.confidence_level
        )
    
    def generate_uplift_report(self,
                             smart_predictions: List[List[int]],
                             random_predictions: List[List[int]], 
                             actual_draws: List[List[int]],
                             game_type: GameType,
                             max_tier: Optional[int] = None) -> UpliftReport:
        """
        Generate complete uplift report across all tiers
        
        Args:
            smart_predictions: "Smart" algorithm predictions
            random_predictions: Random baseline predictions  
            actual_draws: Actual lottery draws
            game_type: Type of lottery game
            max_tier: Maximum tier to analyze (defaults to game's main numbers)
            
        Returns:
            Complete UpliftReport with all tier analyses
        """
        from datetime import datetime
        
        game_config = GAME_CONFIGS[game_type]
        
        if max_tier is None:
            max_tier = game_config.main_numbers
            
        # Calculate data completeness (placeholder - would need expected draw count)
        data_completeness = 1.0  # Assume complete for now
        
        # Calculate results for each tier
        tier_results = {}
        any_significant = False
        
        for tier in range(1, max_tier + 1):
            result = self.calculate_tier_uplift(
                smart_predictions, random_predictions, actual_draws, tier
            )
            tier_results[tier] = result
            
            if result.is_significant and result.uplift_percent > 0:
                any_significant = True
        
        return UpliftReport(
            game_type=game_type,
            total_predictions=len(smart_predictions),
            total_draws=len(actual_draws),
            tier_results=tier_results,
            overall_significant=any_significant,
            data_completeness=data_completeness,
            analysis_timestamp=datetime.now().isoformat()
        )
    
    def format_uplift_summary(self, report: UpliftReport) -> str:
        """
        Format uplift report for display
        
        Args:
            report: UpliftReport to format
            
        Returns:
            Human-readable summary string
        """
        game_config = GAME_CONFIGS[report.game_type]
        lines = [
            f"📊 {game_config.name} Prediction Analysis",
            f"Sample Size: {report.total_draws} draws",
            f"Confidence Level: {report.tier_results[1].confidence_level*100:.0f}%",
            ""
        ]
        
        for tier, result in report.tier_results.items():
            status = "✅ Significant" if result.is_significant else "⚪ Not Significant"
            
            if result.sample_size < self.min_sample_size:
                status = "⚠️ Small Sample"
            
            lines.append(
                f"Tier {tier} ({tier}+ matches): "
                f"{result.uplift_percent:+.1f}% uplift | {status}"
            )
        
        if report.overall_significant:
            lines.append("\n🎯 Overall: Statistically significant improvement detected")
        else:
            lines.append("\n📊 Overall: No statistically significant improvement")
            
        return "\n".join(lines)

# Convenience functions for common use cases
def quick_uplift_check(smart_predictions: List[List[int]],
                      random_predictions: List[List[int]], 
                      actual_draws: List[List[int]],
                      game_type: GameType = GameType.LOTTO_649) -> Dict:
    """
    Quick uplift check for GUI display
    
    Returns simplified dict suitable for GUI badges
    """
    metrics = PredictionMetrics()
    report = metrics.generate_uplift_report(
        smart_predictions, random_predictions, actual_draws, game_type
    )
    
    # Find best performing tier
    best_tier = None
    best_uplift = -float('inf')
    
    for tier, result in report.tier_results.items():
        if result.is_significant and result.uplift_percent > best_uplift:
            best_tier = tier
            best_uplift = result.uplift_percent
    
    if best_tier is None:
        # No significant tiers, show tier 2 as default
        best_tier = 2
        best_result = report.tier_results.get(2)
        if best_result:
            best_uplift = best_result.uplift_percent
        else:
            best_uplift = 0.0
    
    return {
        "uplift_percent": best_uplift,
        "tier": best_tier,
        "is_significant": best_tier is not None and report.tier_results[best_tier].is_significant,
        "sample_size": report.total_draws,
        "summary": f"{best_uplift:+.1f}% at tier {best_tier}"
    }

def validate_predictions_format(predictions: List[List[int]], 
                               game_type: GameType) -> List[str]:
    """
    Validate prediction format for given game type
    
    Returns list of validation errors (empty if valid)
    """
    errors = []
    game_config = GAME_CONFIGS[game_type]
    
    for i, pred in enumerate(predictions):
        if not isinstance(pred, list):
            errors.append(f"Prediction {i}: Must be a list of integers")
            continue
            
        if len(pred) != game_config.main_numbers:
            errors.append(
                f"Prediction {i}: Expected {game_config.main_numbers} numbers, got {len(pred)}"
            )
            
        for num in pred:
            if not isinstance(num, int):
                errors.append(f"Prediction {i}: All numbers must be integers, got {type(num)}")
            elif num < game_config.number_range[0] or num > game_config.number_range[1]:
                errors.append(
                    f"Prediction {i}: Number {num} out of range "
                    f"{game_config.number_range[0]}-{game_config.number_range[1]}"
                )
        
        # Check for duplicates within prediction
        if len(set(pred)) != len(pred):
            errors.append(f"Prediction {i}: Contains duplicate numbers")
    
    return errors

# Example usage for testing
if __name__ == "__main__":
    # Sample data for testing
    smart_preds = [[1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12]]
    random_preds = [[13, 14, 15, 16, 17, 18], [19, 20, 21, 22, 23, 24]]
    actual_draws = [[1, 2, 25, 26, 27, 28], [7, 8, 29, 30, 31, 32]]
    
    # Quick test
    result = quick_uplift_check(smart_preds, random_preds, actual_draws)
    print("Quick Uplift Check:", result)
    
    # Full analysis
    metrics = PredictionMetrics()
    report = metrics.generate_uplift_report(
        smart_preds, random_preds, actual_draws, GameType.LOTTO_649
    )
    print("\nFull Report:")
    print(metrics.format_uplift_summary(report))