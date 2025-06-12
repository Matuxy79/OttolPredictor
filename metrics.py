"""
Prediction Metrics Engine for Saskatoon Lotto Predictor
======================================================

Statistical evaluation of prediction performance with Wilson score confidence intervals.
Determines if smart predictions beat random guessing in a statistically meaningful way.

Features:
- Pure Python implementation of statistical functions (no SciPy dependency)
- Wilson score confidence intervals (robust for small samples)
- JSON-serializable results for GUI integration
- Support for Lotto 6/49 and Lotto Max

Author: Saskatoon Lotto Predictor Team
Version: 1.1.0
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass, asdict
from enum import Enum
from functools import lru_cache
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# Pure Python Implementation of Statistical Functions
# ─────────────────────────────────────────────────────────────────

def norm_ppf(p: float) -> float:
    """
    Pure Python implementation of the percent point function (inverse of CDF)
    for the standard normal distribution.

    This is equivalent to scipy.stats.norm.ppf() but doesn't require SciPy.

    Args:
        p: Probability (0 < p < 1)

    Returns:
        Corresponding z-score

    Implementation based on Abramowitz and Stegun approximation 26.2.23.
    Accuracy: |error| < 4.5e-4
    """
    if p <= 0 or p >= 1:
        raise ValueError("Probability must be between 0 and 1")

    # Handle special case for p = 0.5
    if p == 0.5:
        return 0.0

    # For numerical stability, handle extreme values
    if p < 1e-10:
        return -8.0  # Approximate for very small p
    if p > 1 - 1e-10:
        return 8.0   # Approximate for p very close to 1

    # Coefficients for the approximation
    c0 = 2.515517
    c1 = 0.802853
    c2 = 0.010328
    d1 = 1.432788
    d2 = 0.189269
    d3 = 0.001308

    # Determine if we're in the lower or upper tail
    if p <= 0.5:
        q = p
        sign = -1.0
    else:
        q = 1.0 - p
        sign = 1.0

    # Calculate intermediate value
    t = math.sqrt(-2.0 * math.log(q))

    # Apply approximation formula
    z = t - (c0 + c1 * t + c2 * t**2) / (1.0 + d1 * t + d2 * t**2 + d3 * t**3)

    return sign * z

# Pre-computed z-scores for common confidence levels
Z_SCORE_TABLE = {
    0.50: 0.000,
    0.75: 1.150,
    0.80: 1.282,
    0.85: 1.440,
    0.90: 1.645,
    0.95: 1.960,
    0.96: 2.054,
    0.97: 2.170,
    0.98: 2.326,
    0.99: 2.576,
    0.995: 2.807,
    0.998: 3.090,
    0.999: 3.291,
    0.9995: 3.481,
    0.9999: 3.891
}

class GameType(str, Enum):
    """Supported lottery game types"""
    LOTTO_649 = "649"
    LOTTO_MAX = "max"

@dataclass(frozen=True)
class GameConfig:
    """Configuration for lottery games"""
    name: str
    main_numbers: int
    number_range: Tuple[int, int]

GAME_CONFIGS = {
    GameType.LOTTO_649: GameConfig("Lotto 6/49", 6, (1, 49)),
    GameType.LOTTO_MAX: GameConfig("Lotto Max", 7, (1, 50))
}

@dataclass(frozen=True)
class TierResult:
    """Statistical results for a specific match tier"""
    tier: int
    smart_hits: int
    random_hits: int
    total_trials: int
    smart_hit_rate: float
    random_hit_rate: float
    uplift_percent: float
    ci_lower: float
    ci_upper: float
    is_significant: bool
    confidence_level: float

    def as_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return asdict(self)

    def summary_text(self) -> str:
        """Human-readable summary for GUI display"""
        significance = "✅" if self.is_significant else "⚪"
        return f"Tier {self.tier}: {self.uplift_percent:+.1f}% {significance}"

@dataclass(frozen=True) 
class UpliftReport:
    """Complete uplift analysis across all tiers"""
    game_type: GameType
    tier_results: Dict[int, TierResult]
    total_predictions: int
    total_draws: int
    analysis_timestamp: str
    overall_significant: bool

    def as_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            "game_type": self.game_type.value,
            "tier_results": {str(k): v.as_dict() for k, v in self.tier_results.items()},
            "total_predictions": self.total_predictions,
            "total_draws": self.total_draws,
            "analysis_timestamp": self.analysis_timestamp,
            "overall_significant": self.overall_significant
        }

    def best_tier_headline(self) -> str:
        """Get headline for best performing significant tier"""
        # Find best significant tier
        best_tier = None
        best_uplift = -float('inf')

        for tier, result in self.tier_results.items():
            if result.is_significant and result.uplift_percent > best_uplift:
                best_tier = tier
                best_uplift = result.uplift_percent

        if best_tier is None:
            # No significant tiers, show tier 2 as default
            tier_2 = self.tier_results.get(2)
            if tier_2:
                return f"{tier_2.uplift_percent:+.1f}% (tier 2)"
            else:
                return "No data"

        return f"{best_uplift:+.1f}% ★ (tier {best_tier})"

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
        """
        Get z-score for confidence level using pure Python implementation.

        This method uses two approaches in order:
        1. Look up the exact confidence level in Z_SCORE_TABLE (fastest)
        2. Calculate using pure Python norm_ppf implementation (accurate)

        No external dependencies required.
        """
        # Try lookup table first (fastest)
        if confidence_level in Z_SCORE_TABLE:
            return Z_SCORE_TABLE[confidence_level]

        # Calculate using pure Python implementation
        try:
            # Convert confidence level to two-tailed probability
            p = (1 + confidence_level) / 2
            return float(norm_ppf(p))
        except Exception as e:
            logger.warning(f"Z-score calculation failed: {e}")

            # Fall back to closest lookup value if calculation fails
            closest_level = min(Z_SCORE_TABLE.keys(), key=lambda x: abs(x - confidence_level))
            closest_z = Z_SCORE_TABLE[closest_level]
            logger.warning(f"Using closest z-score {closest_z} (for {closest_level}) instead of exact value for {confidence_level}")
            return closest_z

    @lru_cache(maxsize=128)
    def count_matches(self, predicted_tuple: Tuple[int, ...], actual_tuple: Tuple[int, ...]) -> int:
        """
        Count matching numbers between prediction and actual draw

        Args:
            predicted_tuple: Tuple of predicted numbers (for caching)
            actual_tuple: Tuple of actual drawn numbers

        Returns:
            Number of matches
        """
        predicted_set = set(predicted_tuple)
        actual_set = set(actual_tuple)
        return len(predicted_set.intersection(actual_set))

    def calculate_hit_rate(self, 
                          predictions: List[List[int]], 
                          actual_draws: List[List[int]], 
                          tier: int) -> Tuple[int, int]:
        """
        Calculate hits and total for a specific tier

        Args:
            predictions: List of prediction number sets
            actual_draws: List of actual draw number sets
            tier: Minimum matches required for a "hit"

        Returns:
            Tuple of (hits, total_trials)
        """
        if not predictions or not actual_draws:
            logger.warning("Empty predictions or draws provided")
            return 0, 0

        if len(predictions) != len(actual_draws):
            logger.error(f"Length mismatch: {len(predictions)} predictions vs {len(actual_draws)} draws")
            return 0, 0

        hits = 0
        total = len(predictions)

        for pred, actual in zip(predictions, actual_draws):
            try:
                # Convert to tuples for caching
                pred_tuple = tuple(sorted(pred))
                actual_tuple = tuple(sorted(actual))

                matches = self.count_matches(pred_tuple, actual_tuple)
                if matches >= tier:
                    hits += 1

            except Exception as e:
                logger.error(f"Error calculating matches for {pred} vs {actual}: {e}")
                continue

        logger.debug(f"Tier {tier}: {hits}/{total} hits = {hits/total:.4f}")
        return hits, total

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

    def intervals_overlap(self, 
                                   ci1: Tuple[float, float], 
                                   ci2: Tuple[float, float]) -> bool:
        """Check if two confidence intervals overlap"""
        return not (ci1[1] < ci2[0] or ci2[1] < ci1[0])

    def calculate_tier_uplift(self,
                            smart_predictions: List[List[int]],
                            random_predictions: List[List[int]], 
                            actual_draws: List[List[int]],
                            tier: int) -> TierResult:
        """
        Calculate uplift statistics with enhanced sample size protection

        Args:
            smart_predictions: Algorithm-generated predictions
            random_predictions: Random baseline predictions
            actual_draws: Actual lottery draws
            tier: Minimum matches for this tier

        Returns:
            TierResult with detailed statistics
        """
        # Calculate hit rates
        smart_hits, smart_total = self.calculate_hit_rate(smart_predictions, actual_draws, tier)
        random_hits, random_total = self.calculate_hit_rate(random_predictions, actual_draws, tier)

        if smart_total == 0 or random_total == 0:
            return self._empty_tier_result(tier)

        smart_rate = smart_hits / smart_total
        random_rate = random_hits / random_total

        # Enhanced uplift calculation with GUI-safe bounds
        if random_rate > 0:
            uplift_percent = ((smart_rate - random_rate) / random_rate) * 100
            # Cap extreme values for display stability
            uplift_percent = max(-99.9, min(999.9, uplift_percent))
        else:
            # Handle division by zero gracefully
            uplift_percent = 999.9 if smart_rate > 0 else 0.0

        # Calculate confidence intervals
        smart_ci = self.wilson_confidence_interval(smart_rate, smart_total)
        random_ci = self.wilson_confidence_interval(random_rate, random_total)

        # Enhanced significance determination with multiple guards
        intervals_dont_overlap = not self.intervals_overlap(smart_ci, random_ci)
        sufficient_sample_size = (smart_total >= self.min_sample_size and 
                                 random_total >= self.min_sample_size)
        meets_absolute_threshold = smart_total >= 30 and random_total >= 30  # ✨ Critical addition

        is_significant = (intervals_dont_overlap and 
                         sufficient_sample_size and 
                         meets_absolute_threshold)

        # Calculate confidence interval for the uplift difference
        rate_diff = smart_rate - random_rate
        se_diff = math.sqrt(
            (smart_rate * (1 - smart_rate) / smart_total) +
            (random_rate * (1 - random_rate) / random_total)
        )

        ci_lower = (rate_diff - self.z_score * se_diff) * 100
        ci_upper = (rate_diff + self.z_score * se_diff) * 100

        logger.info(f"Tier {tier}: Smart={smart_rate:.4f}, Random={random_rate:.4f}, "
                   f"Uplift={uplift_percent:.2f}%, Significant={is_significant}, "
                   f"Sample={smart_total}")

        return TierResult(
            tier=tier,
            smart_hits=smart_hits,
            random_hits=random_hits,
            total_trials=smart_total,
            smart_hit_rate=smart_rate,
            random_hit_rate=random_rate,
            uplift_percent=round(uplift_percent, 1),  # Reduced precision for display
            ci_lower=round(ci_lower, 1),
            ci_upper=round(ci_upper, 1),
            is_significant=is_significant,
            confidence_level=self.confidence_level
        )

    def _empty_tier_result(self, tier: int) -> TierResult:
        """Return empty tier result for error cases"""
        return TierResult(
            tier=tier,
            smart_hits=0,
            random_hits=0,
            total_trials=0,
            smart_hit_rate=0.0,
            random_hit_rate=0.0,
            uplift_percent=0.0,
            ci_lower=0.0,
            ci_upper=0.0,
            is_significant=False,
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
            smart_predictions: Algorithm-generated predictions
            random_predictions: Random baseline predictions
            actual_draws: Actual lottery draws
            game_type: Type of lottery game
            max_tier: Maximum tier to analyze (defaults to game's main numbers)

        Returns:
            Complete UpliftReport
        """
        game_config = GAME_CONFIGS[game_type]

        if max_tier is None:
            max_tier = game_config.main_numbers

        # Validate inputs
        if not (smart_predictions and random_predictions and actual_draws):
            logger.error("Empty input data provided")
            return self._empty_uplift_report(game_type)

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
            tier_results=tier_results,
            total_predictions=len(smart_predictions),
            total_draws=len(actual_draws),
            analysis_timestamp=datetime.now().isoformat(),
            overall_significant=any_significant
        )

    def _empty_uplift_report(self, game_type: GameType) -> UpliftReport:
        """Return empty uplift report for error cases"""
        return UpliftReport(
            game_type=game_type,
            tier_results={},
            total_predictions=0,
            total_draws=0,
            analysis_timestamp=datetime.now().isoformat(),
            overall_significant=False
        )

    def format_uplift_summary(self, report: UpliftReport) -> str:
        """
        Format uplift report for display

        Args:
            report: UpliftReport to format

        Returns:
            Human-readable summary string
        """
        if not report.tier_results:
            return "📊 No data available for analysis"

        game_config = GAME_CONFIGS[report.game_type]
        lines = [
            f"📊 {game_config.name} Prediction Analysis",
            f"Sample Size: {report.total_draws} draws",
            f"Confidence Level: {self.confidence_level*100:.0f}%",
            ""
        ]

        for tier, result in report.tier_results.items():
            if result.total_trials < self.min_sample_size:
                status = "⚠️ Small Sample"
            elif result.is_significant:
                status = "✅ Significant"
            else:
                status = "⚪ Not Significant"

            lines.append(
                f"Tier {tier} ({tier}+ matches): "
                f"{result.uplift_percent:+.1f}% uplift | {status}"
            )

        if report.overall_significant:
            lines.append("\n🎯 Overall: Statistically significant improvement detected")
        else:
            lines.append("\n📊 Overall: No statistically significant improvement")

        return "\n".join(lines)

# ─────────────────────────────────────────────────────────────────
# Convenience Functions for Quick Integration
# ─────────────────────────────────────────────────────────────────

def quick_uplift_check(
    smart_predictions: List[List[int]],
    random_predictions: List[List[int]], 
    actual_draws: List[List[int]],
    game_type: GameType = GameType.LOTTO_649
) -> Dict[str, Any]:
    """
    GUI-optimized uplift check with comprehensive error handling

    Returns:
        Dict with keys: uplift_percent, tier, is_significant, sample_size,
        headline, status, confidence_interval, display_class
    """

    try:
        if not all([smart_predictions, random_predictions, actual_draws]):
            return _create_error_result("insufficient_data", "📊 No data")

        metrics = PredictionMetrics()
        report = metrics.generate_uplift_report(
            smart_predictions, random_predictions, actual_draws, game_type
        )

        if not report.tier_results:
            return _create_error_result("no_results", "📊 No results")

        # Intelligent tier selection for display
        best_result = _select_best_tier_for_display(report.tier_results)

        if not best_result:
            return _create_error_result("calculation_error", "📊 Error")

        tier, result = best_result

        # Format for GUI display
        status, status_icon, display_class = _determine_display_status(result)

        # Handle extreme uplift values for display
        display_uplift = _format_uplift_for_display(result.uplift_percent)

        return {
            "uplift_percent": result.uplift_percent,
            "tier": tier,
            "is_significant": result.is_significant,
            "sample_size": report.total_draws,
            "headline": f"{display_uplift} {status_icon}",
            "status": status,
            "confidence_interval": (result.ci_lower, result.ci_upper),
            "display_class": display_class,  # For CSS styling
            "tooltip": _generate_tooltip(result, tier),
            "evaluation_timestamp": report.analysis_timestamp
        }

    except Exception as e:
        logger.error(f"Quick uplift check failed: {e}")
        return _create_error_result("error", "📊 Error")

def _select_best_tier_for_display(tier_results: Dict[int, TierResult]) -> Optional[Tuple[int, TierResult]]:
    """Select the most informative tier for GUI display"""

    # Priority 1: Significant positive results (prefer higher tiers)
    significant_positive = [
        (tier, result) for tier, result in tier_results.items()
        if result.is_significant and result.uplift_percent > 0
    ]
    if significant_positive:
        return max(significant_positive, key=lambda x: (x[1].uplift_percent, x[0]))

    # Priority 2: Any significant results
    significant_any = [
        (tier, result) for tier, result in tier_results.items()
        if result.is_significant
    ]
    if significant_any:
        return max(significant_any, key=lambda x: x[1].uplift_percent)

    # Priority 3: Tier 2 as default (good balance of frequency and meaning)
    if 2 in tier_results:
        return (2, tier_results[2])

    # Priority 4: Any available tier
    if tier_results:
        return next(iter(tier_results.items()))

    return None

def _determine_display_status(result: TierResult) -> Tuple[str, str, str]:
    """Determine status, icon, and CSS class for display"""

    if result.total_trials < 30:
        return ("small_sample", "⚠️", "warning")
    elif result.is_significant and result.uplift_percent > 0:
        return ("significant_positive", "✅", "success")
    elif result.is_significant and result.uplift_percent < 0:
        return ("significant_negative", "❌", "danger")
    else:
        return ("not_significant", "⚪", "neutral")

def _format_uplift_for_display(uplift: float) -> str:
    """Format uplift percentage for GUI display"""

    if uplift >= 999:
        return "999%+"
    elif uplift <= -99:
        return "99%-"
    else:
        return f"{uplift:+.1f}%"

def _generate_tooltip(result: TierResult, tier: int) -> str:
    """Generate informative tooltip for GUI"""

    confidence_pct = int(result.confidence_level * 100)

    return (f"Tier {tier} (≥{tier} matches)\n"
           f"Smart: {result.smart_hits}/{result.total_trials} hits\n"
           f"Random: {result.random_hits}/{result.total_trials} hits\n"
           f"Uplift: {result.uplift_percent:+.1f}%\n"
           f"{confidence_pct}% CI: [{result.ci_lower:.1f}%, {result.ci_upper:.1f}%]")

def _create_error_result(status: str, headline: str) -> Dict[str, Any]:
    """Create standardized error result for GUI"""

    return {
        "uplift_percent": 0.0,
        "tier": 1,
        "is_significant": False,
        "sample_size": 0,
        "headline": headline,
        "status": status,
        "confidence_interval": (0.0, 0.0),
        "display_class": "error",
        "tooltip": "Insufficient data for analysis",
        "evaluation_timestamp": datetime.now().isoformat()
    }

def generate_random_baseline(count: int, game_type: GameType) -> List[List[int]]:
    """
    Generate random predictions for baseline comparison

    Args:
        count: Number of random predictions to generate
        game_type: Type of lottery game

    Returns:
        List of random number sets
    """
    import random

    game_config = GAME_CONFIGS[game_type]
    max_num = game_config.number_range[1]
    num_count = game_config.main_numbers

    baseline = []
    for _ in range(count):
        numbers = sorted(random.sample(range(1, max_num + 1), num_count))
        baseline.append(numbers)

    return baseline

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
