"""
Analytics Module for Saskatoon Lotto Predictor

This module provides statistical analysis and visualization functions
for lottery data. It works with the data_manager module to access
historical lottery draw data and generate insights.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple, Optional
import logging

from data_manager import get_data_manager

logger = logging.getLogger(__name__)

class LotteryAnalytics:
    """
    Provides statistical analysis and visualization for lottery data
    """

    def __init__(self):
        """Initialize the analytics engine"""
        self.data_manager = get_data_manager()
        self.logger = logging.getLogger(__name__)

    def analyze_number_frequency(self, draws_data, game='649'):
        """Analyze number frequency with safe data handling"""
        try:
            if not draws_data or len(draws_data) == 0:
                self.logger.warning("No draws data provided for frequency analysis")
                return pd.DataFrame()

            # Handle both DataFrame and list formats
            if isinstance(draws_data, pd.DataFrame):
                if 'numbers_list' in draws_data.columns:
                    # Use the normalized numbers_list column
                    numbers_lists = draws_data['numbers_list'].tolist()
                else:
                    # Fall back to numbers column
                    numbers_lists = []
                    for _, row in draws_data.iterrows():
                        numbers = row.get('numbers', [])
                        if isinstance(numbers, list) and len(numbers) > 0:
                            numbers_lists.append(numbers)
                        elif isinstance(numbers, str):
                            try:
                                from schema import DataValidator
                                normalized = DataValidator.normalize_numbers_field(numbers)
                                numbers_lists.append(normalized)
                            except Exception:
                                continue
            else:
                # Handle list of dictionaries
                numbers_lists = []
                for draw in draws_data:
                    numbers = draw.get('numbers', [])
                    if isinstance(numbers, list) and len(numbers) > 0:
                        numbers_lists.append(numbers)
                    elif isinstance(numbers, str):
                        try:
                            from schema import DataValidator
                            normalized = DataValidator.normalize_numbers_field(numbers)
                            numbers_lists.append(normalized)
                        except Exception:
                            continue

            if not numbers_lists:
                self.logger.warning("No valid numbers found in draws data")
                return pd.DataFrame()

            # Flatten all numbers safely (avoiding unhashable list error)
            all_numbers = []
            for numbers in numbers_lists:
                if isinstance(numbers, list):
                    # Extend with individual integers (these are hashable)
                    all_numbers.extend([int(num) for num in numbers if num is not None])

            if not all_numbers:
                return pd.DataFrame()

            # Count frequencies using individual numbers (not lists)
            from collections import Counter
            frequency_counter = Counter(all_numbers)

            # Convert to DataFrame
            frequency_data = []
            for number, count in frequency_counter.items():
                frequency_data.append({
                    'number': int(number),
                    'frequency': int(count),
                    'percentage': round((count / len(numbers_lists)) * 100, 2)
                })

            # Sort by frequency (most frequent first)
            frequency_df = pd.DataFrame(frequency_data)
            frequency_df = frequency_df.sort_values('frequency', ascending=False)

            self.logger.info(f"Analyzed frequency for {len(all_numbers)} total numbers from {len(numbers_lists)} draws")
            return frequency_df

        except Exception as e:
            self.logger.error(f"Error analyzing number frequency: {e}")
            return pd.DataFrame()

    def get_number_pairs(self, game: str) -> Dict[Tuple[int, int], int]:
        """
        Find frequently occurring number pairs

        Args:
            game: Game type (649, max, etc.)

        Returns:
            Dictionary mapping number pairs to their frequency counts
        """
        data = self.data_manager.load_game_data(game)
        pairs = {}

        for numbers_list in data['numbers_list']:
            if len(numbers_list) < 2:
                continue

            # Generate all possible pairs from the draw
            for i in range(len(numbers_list)):
                for j in range(i+1, len(numbers_list)):
                    # Fix: Ensure pair is always sorted for consistency
                    pair = tuple(sorted([numbers_list[i], numbers_list[j]]))
                    pairs[pair] = pairs.get(pair, 0) + 1

        return pairs

    def analyze_draw_patterns(self, game: str) -> Dict:
        """
        Analyze patterns in draws (odd/even distribution, high/low, etc.)

        Args:
            game: Game type (649, max, etc.)

        Returns:
            Dictionary with pattern analysis results
        """
        data = self.data_manager.load_game_data(game)
        patterns = {
            'odd_even_distribution': [],
            'high_low_distribution': [],
            'sum_distribution': [],
            'range_distribution': []
        }

        # Placeholder for future implementation
        self.logger.info(f"Analyzing patterns for {game} with {len(data)} draws")

        return patterns

    def plot_number_frequency(self, game: str, save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot the frequency of each number in a game's history

        Args:
            game: Game type (649, max, etc.)
            save_path: Optional path to save the plot image

        Returns:
            matplotlib Figure object
        """
        self.logger.info(f"Plotting number frequency for {game}")

        # Get game data
        game_data = self.data_manager.load_game_data(game)

        # Get frequency data using the enhanced method
        frequency_df = self.analyze_number_frequency(game_data, game)

        if frequency_df.empty:
            # Create an empty figure with a message
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, f"No data available for {game}", 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes, fontsize=14)
            return fig

        # Sort by number for display
        frequency_df = frequency_df.sort_values('number')

        # Extract data for plotting
        numbers = frequency_df['number'].tolist()
        frequencies = frequency_df['frequency'].tolist()

        # Create figure and axis
        fig, ax = plt.subplots(figsize=(10, 6))

        # Create bar chart
        bars = ax.bar(numbers, frequencies, color='skyblue')

        # Highlight top 6 most frequent numbers
        top_df = frequency_df.sort_values('frequency', ascending=False).head(6)
        top_numbers = top_df['number'].tolist()

        for bar, num in zip(bars, numbers):
            if num in top_numbers:
                bar.set_color('orange')

        # Add labels and title
        ax.set_xlabel('Number')
        ax.set_ylabel('Frequency')
        ax.set_title(f'Number Frequency for {game.upper()}')

        # Add grid
        ax.grid(axis='y', linestyle='--', alpha=0.7)

        # Ensure x-axis shows all numbers
        ax.set_xticks(numbers)

        # Save if requested
        if save_path:
            plt.savefig(save_path)

        return fig

    def plot_trend_analysis(self, game: str, save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot trends in lottery draws over time

        Args:
            game: Game type (649, max, etc.)
            save_path: Optional path to save the plot image

        Returns:
            matplotlib Figure object
        """
        self.logger.info(f"Plotting trend analysis for {game}")

        # Get game data
        data = self.data_manager.load_game_data(game)

        if len(data) < 2:
            # Not enough data for trend analysis
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, "Not enough data for trend analysis", 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=14)
            return fig

        # Calculate sum of numbers for each draw
        data['sum'] = data['numbers_list'].apply(lambda x: sum(x) if x else 0)

        # Sort by date
        data = data.sort_values('date')

        # Create figure and axis
        fig, ax = plt.subplots(figsize=(10, 6))

        # Plot trend line
        ax.plot(range(len(data)), data['sum'], marker='o', linestyle='-', color='blue', alpha=0.7)

        # Add moving average
        window = min(10, len(data) // 2) if len(data) > 5 else 2
        if window > 1:
            data['moving_avg'] = data['sum'].rolling(window=window).mean()
            ax.plot(range(len(data)), data['moving_avg'], color='red', linewidth=2, 
                   label=f'{window}-draw Moving Average')
            ax.legend()

        # Add labels and title
        ax.set_xlabel('Draw Number')
        ax.set_ylabel('Sum of Numbers')
        ax.set_title(f'Number Sum Trend for {game.upper()}')

        # Add grid
        ax.grid(linestyle='--', alpha=0.7)

        # Set x-ticks to show every 5th draw
        step = max(len(data) // 10, 1)
        ax.set_xticks(range(0, len(data), step))

        # If we have dates, use them for x-axis labels
        if 'date' in data.columns:
            date_labels = data.iloc[::step]['date'].tolist()
            ax.set_xticklabels(date_labels, rotation=45, ha='right')

        # Adjust layout
        plt.tight_layout()

        # Save if requested
        if save_path:
            plt.savefig(save_path)

        return fig

    def plot_prediction_performance(self, game: str, save_path: Optional[str] = None) -> None:
        """Plot prediction accuracy over time"""
        try:
            from tracking.prediction_logger import PredictionLogger

            logger_instance = PredictionLogger()
            predictions = logger_instance.get_recent_predictions(game, days=90)

            if not predictions:
                self.logger.info("No prediction data available for performance plot")
                return

            # Prepare data for plotting
            dates = []
            accuracies = []
            strategies = []

            for pred in predictions:
                if pred.get('matches_count') is not None:  # Only include evaluated predictions
                    dates.append(pred['timestamp'][:10])  # Date only
                    accuracy = pred.get('matches_count', 0) / len(pred['numbers']) * 100
                    accuracies.append(accuracy)
                    strategies.append(pred['strategy'])

            if not dates:
                self.logger.info("No evaluated predictions available for performance plot")
                return

            plt.figure(figsize=(12, 6))

            # Convert dates for plotting
            from datetime import datetime
            plot_dates = [datetime.fromisoformat(date) for date in dates]

            # Create scatter plot colored by strategy
            strategy_colors = {
                'balanced': '#007bff',
                'hot_cold': '#dc3545', 
                'frequency': '#28a745',
                'random': '#6c757d'
            }

            for strategy in set(strategies):
                strategy_dates = [plot_dates[i] for i, s in enumerate(strategies) if s == strategy]
                strategy_accuracies = [accuracies[i] for i, s in enumerate(strategies) if s == strategy]

                plt.scatter(strategy_dates, strategy_accuracies, 
                           label=strategy.title(), 
                           color=strategy_colors.get(strategy, '#000000'),
                           alpha=0.7, s=50)

            plt.title(f'{game.upper()} Prediction Performance Over Time')
            plt.xlabel('Date')
            plt.ylabel('Match Percentage (%)')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()

            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            else:
                plt.show()

        except Exception as e:
            self.logger.error(f"Failed to plot prediction performance: {e}")

    def plot_strategy_comparison(self, save_path: Optional[str] = None) -> None:
        """Compare performance of different strategies"""
        try:
            from tracking.prediction_logger import PredictionLogger

            logger_instance = PredictionLogger()
            performance = logger_instance.get_strategy_performance(days=90)

            if not performance:
                self.logger.info("No strategy performance data available")
                return

            strategies = list(performance.keys())
            win_rates = [performance[s]['win_rate'] for s in strategies]
            avg_matches = [performance[s]['avg_matches'] for s in strategies]
            total_predictions = [performance[s]['total_predictions'] for s in strategies]

            fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))

            # Win rates
            bars1 = ax1.bar(strategies, win_rates, color=['#007bff', '#dc3545', '#28a745', '#6c757d'])
            ax1.set_title('Win Rate by Strategy')
            ax1.set_ylabel('Win Rate (%)')
            ax1.set_ylim(0, max(win_rates) * 1.2 if win_rates else 100)

            # Add value labels on bars
            for bar, rate in zip(bars1, win_rates):
                ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                        f'{rate:.1f}%', ha='center', va='bottom')

            # Average matches
            bars2 = ax2.bar(strategies, avg_matches, color=['#007bff', '#dc3545', '#28a745', '#6c757d'])
            ax2.set_title('Average Matches per Prediction')
            ax2.set_ylabel('Average Matches')
            ax2.set_ylim(0, max(avg_matches) * 1.2 if avg_matches else 3)

            for bar, matches in zip(bars2, avg_matches):
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                        f'{matches:.2f}', ha='center', va='bottom')

            # Total predictions
            bars3 = ax3.bar(strategies, total_predictions, color=['#007bff', '#dc3545', '#28a745', '#6c757d'])
            ax3.set_title('Total Predictions Made')
            ax3.set_ylabel('Number of Predictions')

            for bar, total in zip(bars3, total_predictions):
                ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                        str(total), ha='center', va='bottom')

            plt.tight_layout()

            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            else:
                plt.show()

        except Exception as e:
            self.logger.error(f"Failed to plot strategy comparison: {e}")

    def get_prediction_insights(self, game: str) -> Dict:
        """Get insights about prediction performance"""
        try:
            from tracking.prediction_logger import PredictionLogger

            logger_instance = PredictionLogger()
            predictions = logger_instance.get_recent_predictions(game, days=30)
            performance = logger_instance.get_strategy_performance(days=30)

            insights = {
                'total_predictions': len(predictions),
                'strategies_used': len(performance),
                'best_strategy': None,
                'worst_strategy': None,
                'overall_win_rate': 0,
                'improvement_trend': 'stable'
            }

            if performance:
                # Find best and worst strategies
                best_strategy = max(performance.items(), key=lambda x: x[1]['win_rate'])
                worst_strategy = min(performance.items(), key=lambda x: x[1]['win_rate'])

                insights['best_strategy'] = {
                    'name': best_strategy[0],
                    'win_rate': best_strategy[1]['win_rate']
                }
                insights['worst_strategy'] = {
                    'name': worst_strategy[0], 
                    'win_rate': worst_strategy[1]['win_rate']
                }

                # Calculate overall win rate
                total_wins = sum(p['wins'] for p in performance.values())
                total_preds = sum(p['total_predictions'] for p in performance.values())
                insights['overall_win_rate'] = (total_wins / total_preds * 100) if total_preds > 0 else 0

            return insights

        except Exception as e:
            self.logger.error(f"Failed to get prediction insights: {e}")
            return {}


# Convenience function
def get_analytics_engine() -> LotteryAnalytics:
    """Get a shared instance of the analytics engine"""
    if not hasattr(get_analytics_engine, '_instance'):
        get_analytics_engine._instance = LotteryAnalytics()
    return get_analytics_engine._instance
