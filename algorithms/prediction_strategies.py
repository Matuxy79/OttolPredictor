from abc import ABC, abstractmethod
from typing import List, Dict, Any
import random
import numpy as np
from collections import Counter
import logging

logger = logging.getLogger(__name__)

class PredictionStrategy(ABC):
    """Base class for all prediction strategies"""
    
    @abstractmethod
    def predict(self, historical_data: Dict, count: int) -> List[int]:
        """Generate prediction numbers"""
        pass
    
    @abstractmethod
    def calculate_confidence(self, historical_data: Dict, numbers: List[int]) -> float:
        """Calculate confidence score 0-1"""
        pass
    
    def get_strategy_name(self) -> str:
        """Return human-readable strategy name"""
        return self.__class__.__name__

class RandomStrategy(PredictionStrategy):
    """Baseline random number generator"""
    
    def predict(self, historical_data: Dict, count: int) -> List[int]:
        """Generate random numbers within valid range"""
        max_number = 49 if count == 6 else 50  # 6/49 vs Lotto Max
        return random.sample(range(1, max_number + 1), count)
    
    def calculate_confidence(self, historical_data: Dict, numbers: List[int]) -> float:
        """Random strategy always has low confidence"""
        return 0.1

class HotColdStrategy(PredictionStrategy):
    """Strategy based on recent number frequency"""
    
    def __init__(self, lookback_draws: int = 50, hot_ratio: float = 0.6):
        self.lookback_draws = lookback_draws
        self.hot_ratio = hot_ratio
    
    def predict(self, historical_data: Dict, count: int) -> List[int]:
        """Pick mix of hot (frequent) and cold (overdue) numbers"""
        try:
            numbers_list = historical_data.get('numbers_list', [])
            recent_draws = numbers_list[-self.lookback_draws:]
            
            # Count frequency of each number
            frequency = Counter()
            for draw in recent_draws:
                frequency.update(draw)
            
            max_number = 49 if count == 6 else 50
            all_numbers = set(range(1, max_number + 1))
            
            # Separate hot and cold numbers
            hot_numbers = [num for num, freq in frequency.most_common(25)]
            cold_numbers = list(all_numbers - set(hot_numbers))
            
            # Mix hot and cold
            hot_count = int(count * self.hot_ratio)
            cold_count = count - hot_count
            
            picked = []
            picked.extend(random.sample(hot_numbers[:15], min(hot_count, len(hot_numbers[:15]))))
            picked.extend(random.sample(cold_numbers, min(cold_count, len(cold_numbers))))
            
            # Fill remaining with random if needed
            while len(picked) < count:
                remaining = list(all_numbers - set(picked))
                if remaining:
                    picked.append(random.choice(remaining))
                else:
                    break
            
            return sorted(picked[:count])
            
        except Exception as e:
            logger.error(f"HotCold strategy failed: {e}")
            return RandomStrategy().predict(historical_data, count)
    
    def calculate_confidence(self, historical_data: Dict, numbers: List[int]) -> float:
        """Higher confidence if we have good historical data"""
        numbers_list = historical_data.get('numbers_list', [])
        data_quality = min(len(numbers_list) / 100.0, 1.0)  # More data = higher confidence
        return 0.3 + (data_quality * 0.4)  # 0.3 to 0.7 range

class FrequencyStrategy(PredictionStrategy):
    """Strategy based on overall historical frequency"""
    
    def predict(self, historical_data: Dict, count: int) -> List[int]:
        """Pick numbers weighted by historical frequency"""
        try:
            numbers_list = historical_data.get('numbers_list', [])
            
            # Count overall frequency
            frequency = Counter()
            for draw in numbers_list:
                frequency.update(draw)
            
            if not frequency:
                return RandomStrategy().predict(historical_data, count)
            
            # Create weighted list
            weighted_numbers = []
            for number, freq in frequency.items():
                weighted_numbers.extend([number] * freq)
            
            # Pick with replacement, then deduplicate
            picked = set()
            attempts = 0
            while len(picked) < count and attempts < count * 10:
                if weighted_numbers:
                    picked.add(random.choice(weighted_numbers))
                attempts += 1
            
            # Fill remaining with random if needed
            max_number = 49 if count == 6 else 50
            all_numbers = set(range(1, max_number + 1))
            while len(picked) < count:
                remaining = list(all_numbers - picked)
                if remaining:
                    picked.add(random.choice(remaining))
                else:
                    break
            
            return sorted(list(picked))
            
        except Exception as e:
            logger.error(f"Frequency strategy failed: {e}")
            return RandomStrategy().predict(historical_data, count)
    
    def calculate_confidence(self, historical_data: Dict, numbers: List[int]) -> float:
        """Confidence based on data volume and distribution"""
        numbers_list = historical_data.get('numbers_list', [])
        draws_count = len(numbers_list)
        
        if draws_count > 200:
            return 0.7
        elif draws_count > 100:
            return 0.5
        elif draws_count > 50:
            return 0.3
        else:
            return 0.2

class BalancedStrategy(PredictionStrategy):
    """Balanced approach combining multiple factors"""
    
    def predict(self, historical_data: Dict, count: int) -> List[int]:
        """Combine hot/cold with frequency and add randomness"""
        try:
            # Get predictions from other strategies
            hot_cold = HotColdStrategy()
            frequency = FrequencyStrategy()
            
            hot_cold_picks = hot_cold.predict(historical_data, count)
            frequency_picks = frequency.predict(historical_data, count)
            
            # Combine strategies (50% hot/cold, 30% frequency, 20% random)
            combined = []
            combined.extend(hot_cold_picks[:int(count * 0.5)])
            combined.extend(frequency_picks[:int(count * 0.3)])
            
            # Add some randomness
            max_number = 49 if count == 6 else 50
            all_numbers = set(range(1, max_number + 1))
            remaining = list(all_numbers - set(combined))
            random_count = count - len(combined)
            
            if remaining and random_count > 0:
                combined.extend(random.sample(remaining, min(random_count, len(remaining))))
            
            # Deduplicate and fill to required count
            unique_picks = list(set(combined))
            while len(unique_picks) < count:
                remaining = list(all_numbers - set(unique_picks))
                if remaining:
                    unique_picks.append(random.choice(remaining))
                else:
                    break
            
            return sorted(unique_picks[:count])
            
        except Exception as e:
            logger.error(f"Balanced strategy failed: {e}")
            return RandomStrategy().predict(historical_data, count)
    
    def calculate_confidence(self, historical_data: Dict, numbers: List[int]) -> float:
        """Medium confidence as balanced approach"""
        hot_cold_conf = HotColdStrategy().calculate_confidence(historical_data, numbers)
        freq_conf = FrequencyStrategy().calculate_confidence(historical_data, numbers)
        return (hot_cold_conf + freq_conf) / 2.0