"""
Analytics Module for Saskatoon Lotto Predictor

This module provides statistical analysis and visualization functions
for lottery data. It works with the data_manager module to access
historical lottery draw data and generate insights.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend by default
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
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
        """BULLETPROOF frequency analysis that skips bad rows"""
        try:
            from utils.data_extraction import safe_data_extraction, validate_draw_numbers
            from collections import Counter

            if not draws_data or len(draws_data) == 0:
                self.logger.warning("No draws data provided for frequency analysis")
                return pd.DataFrame()

            # Extract all valid number lists using our universal extractor
            valid_draws = safe_data_extraction(draws_data, 'numbers_list')

            # Validate draws for the specific game
            validated_draws = []
            for numbers in valid_draws:
                if validate_draw_numbers(numbers, game):
                    validated_draws.append(numbers)

            if not validated_draws:
                self.logger.warning(f"No valid draws found for {game}")
                return pd.DataFrame()

            # Flatten ALL numbers from ALL valid draws
            all_numbers = []
            for draw_numbers in validated_draws:
                all_numbers.extend(draw_numbers)  # This is safe - extending with individual ints

            if not all_numbers:
                return pd.DataFrame()

            # Count frequencies using individual integers (never lists as keys!)
            frequency_counter = Counter(all_numbers)

            # Convert to DataFrame with safe data types
            frequency_data = []
            for number, count in frequency_counter.items():
                frequency_data.append({
                    'number': int(number),
                    'frequency': int(count),
                    'percentage': round((count / len(validated_draws)) * 100, 2)
                })

            # Sort by frequency (most frequent first)
            frequency_df = pd.DataFrame(frequency_data)
            if not frequency_df.empty:
                frequency_df = frequency_df.sort_values('frequency', ascending=False)

            self.logger.info(f"Analyzed {len(all_numbers)} numbers from {len(validated_draws)} valid draws")
            return frequency_df

        except Exception as e:
            self.logger.error(f"Error in analyze_number_frequency: {e}")
            return pd.DataFrame()

    def get_number_pairs(self, game: str) -> Dict[Tuple[int, int], int]:
        """
        Find frequently occurring number pairs with enhanced safety for list handling

        Args:
            game: Game type (649, max, etc.)

        Returns:
            Dictionary mapping number pairs to their frequency counts
        """
        data = self.data_manager.load_game_data(game)
        pairs = {}

        for idx, row in data.iterrows():
            try:
                numbers_list = row.get('numbers_list', [])

                # CRITICAL FIX: Handle different types safely
                if isinstance(numbers_list, np.ndarray):
                    numbers_list = numbers_list.tolist()

                # Skip if not a valid list or too short
                if not isinstance(numbers_list, list) or len(numbers_list) < 2:
                    continue

                # Ensure all elements are integers
                clean_numbers = []
                for n in numbers_list:
                    if isinstance(n, (int, float)) and not np.isnan(n):
                        clean_numbers.append(int(n))
                    elif isinstance(n, str) and n.isdigit():
                        clean_numbers.append(int(n))

                if len(clean_numbers) < 2:
                    continue

                # Generate all possible pairs from the draw
                for i in range(len(clean_numbers)):
                    for j in range(i+1, len(clean_numbers)):
                        # Ensure pair is always sorted for consistency
                        pair = tuple(sorted([clean_numbers[i], clean_numbers[j]]))
                        pairs[pair] = pairs.get(pair, 0) + 1

            except Exception as e:
                self.logger.warning(f"Error processing row {idx} for number pairs: {e}")
                continue

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

    def plot_number_frequency(self, game: str, save_path: Optional[str] = None) -> Figure:
        """BULLETPROOF frequency plotting with embedded chart support"""
        from gui.chart_widgets import render_text_figure

        self.logger.info(f"Plotting number frequency for {game}")

        try:
            # Get game data
            game_data = self.data_manager.load_game_data(game)

            if game_data.empty:
                return render_text_figure(f"No data available for {game}", 
                                         f"Number Frequency - {game.upper()}")

            # Get frequency data using bulletproof method
            frequency_df = self.analyze_number_frequency(game_data, game)

            if frequency_df.empty:
                return render_text_figure(f"No valid frequency data for {game}", 
                                         f"Number Frequency - {game.upper()}")

            # SAFE: Convert to native Python types (never pass pandas types to matplotlib)
            numbers = [int(x) for x in frequency_df['number'].tolist()]
            frequencies = [int(x) for x in frequency_df['frequency'].tolist()]

            if not numbers or not frequencies:
                return render_text_figure("No valid numbers to plot", 
                                         f"Number Frequency - {game.upper()}")

            # Create figure using matplotlib.figure.Figure (not pyplot!)
            fig = Figure(figsize=(12, 8))
            ax = fig.add_subplot(111)

            # Create bar chart with safe data
            bars = ax.bar(numbers, frequencies, color='skyblue', alpha=0.7)

            # Highlight top 6 most frequent numbers
            top_numbers = numbers[:6]  # frequency_df is already sorted
            for bar, num in zip(bars, numbers):
                if num in top_numbers:
                    bar.set_color('orange')

            # Formatting
            ax.set_xlabel('Number', fontsize=12)
            ax.set_ylabel('Frequency', fontsize=12)
            ax.set_title(f'Number Frequency Analysis - {game.upper()}', fontsize=14, pad=20)
            ax.grid(axis='y', linestyle='--', alpha=0.7)

            # Smart tick handling
            if len(numbers) > 20:
                step = max(len(numbers) // 20, 1)
                ax.set_xticks(numbers[::step])
            else:
                ax.set_xticks(numbers)

            # Add stats text
            total_draws = len(game_data)
            avg_freq = sum(frequencies) / len(frequencies) if frequencies else 0
            stats_text = f"Total Draws: {total_draws:,} | Avg Frequency: {avg_freq:.1f}"
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                    fontsize=10, verticalalignment='top',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

            fig.tight_layout()

            # Save if requested
            if save_path:
                fig.savefig(save_path, bbox_inches='tight', dpi=150)

            return fig

        except Exception as e:
            self.logger.error(f"Critical error in plot_number_frequency: {e}")
            return render_text_figure(f"Chart Error: {str(e)[:50]}...", 
                                     f"Number Frequency - {game.upper()}")

    def plot_trend_analysis(self, game: str, save_path: Optional[str] = None) -> Figure:
        """BULLETPROOF trend analysis that skips invalid rows"""
        from utils.data_extraction import safe_data_extraction, validate_draw_numbers
        from gui.chart_widgets import render_text_figure

        self.logger.info(f"Plotting trend analysis for {game}")

        try:
            # Get game data
            data = self.data_manager.load_game_data(game)

            if data.empty:
                return render_text_figure("No data available for trend analysis", 
                                         f"Trend Analysis - {game.upper()}")

            # Extract valid draws with skip-invalid-rows logic
            valid_draws = safe_data_extraction(data, 'numbers_list')

            # Validate and calculate sums, skipping bad rows
            valid_data = []
            for i, numbers in enumerate(valid_draws):
                if validate_draw_numbers(numbers, game):
                    try:
                        row_data = {
                            'sum': sum(numbers),
                            'index': len(valid_data),  # Sequential index for plotting
                            'date': data.iloc[i].get('date', 'Unknown') if i < len(data) else 'Unknown'
                        }
                        valid_data.append(row_data)
                    except Exception:
                        continue  # Skip this row

            if len(valid_data) < 5:
                return render_text_figure(f"Not enough valid data for trend analysis\n(Found {len(valid_data)} valid draws, need at least 5)", 
                                         f"Trend Analysis - {game.upper()}")

            # Extract data for plotting
            sums = [d['sum'] for d in valid_data]
            indices = [d['index'] for d in valid_data]

            # Create figure
            fig = Figure(figsize=(12, 8))
            ax = fig.add_subplot(111)

            # Plot trend line
            ax.plot(indices, sums, marker='o', linestyle='-', color='blue', alpha=0.7, markersize=3)

            # Add moving average if we have enough data
            if len(sums) >= 10:
                window = min(10, len(sums) // 3)
                moving_avg = []
                for i in range(len(sums)):
                    start_idx = max(0, i - window + 1)
                    end_idx = i + 1
                    avg = sum(sums[start_idx:end_idx]) / len(sums[start_idx:end_idx])
                    moving_avg.append(avg)

                ax.plot(indices, moving_avg, color='red', linewidth=2, 
                       label=f'{window}-draw Moving Average')
                ax.legend()

            # Formatting
            ax.set_xlabel('Draw Number', fontsize=12)
            ax.set_ylabel('Sum of Numbers', fontsize=12)
            ax.set_title(f'Number Sum Trend - {game.upper()}', fontsize=14, pad=20)
            ax.grid(linestyle='--', alpha=0.7)

            # Add statistics
            avg_sum = sum(sums) / len(sums)
            min_sum, max_sum = min(sums), max(sums)
            stats_text = f"Draws: {len(sums):,} | Avg: {avg_sum:.1f} | Range: {min_sum}-{max_sum}"
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                    fontsize=10, verticalalignment='top',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

            fig.tight_layout()

            if save_path:
                fig.savefig(save_path, bbox_inches='tight', dpi=150)

            return fig

        except Exception as e:
            self.logger.error(f"Error in plot_trend_analysis: {e}")
            return render_text_figure(f"Trend Analysis Error: {str(e)[:50]}...", 
                                     f"Trend Analysis - {game.upper()}")

    def plot_prediction_performance(self, game: str, save_path: Optional[str] = None) -> Figure:
        """Plot prediction accuracy over time"""
        try:
            from tracking.prediction_logger import PredictionLogger
            from gui.chart_widgets import render_text_figure

            logger_instance = PredictionLogger()
            predictions = logger_instance.get_recent_predictions(game, days=90)

            if not predictions:
                self.logger.info("No prediction data available for performance plot")
                return render_text_figure("No prediction data available", 
                                         f"Prediction Performance - {game.upper()}")

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
                return render_text_figure("No evaluated predictions available", 
                                         f"Prediction Performance - {game.upper()}")

            # Create figure using Figure instead of plt.figure
            fig = Figure(figsize=(12, 6))
            ax = fig.add_subplot(111)

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

                ax.scatter(strategy_dates, strategy_accuracies, 
                           label=strategy.title(), 
                           color=strategy_colors.get(strategy, '#000000'),
                           alpha=0.7, s=50)

            ax.set_title(f'{game.upper()} Prediction Performance Over Time')
            ax.set_xlabel('Date')
            ax.set_ylabel('Match Percentage (%)')
            ax.legend()
            ax.grid(True, alpha=0.3)

            # Handle x-axis tick rotation
            for label in ax.get_xticklabels():
                label.set_rotation(45)

            fig.tight_layout()

            if save_path:
                fig.savefig(save_path, dpi=300, bbox_inches='tight')

            return fig

        except Exception as e:
            self.logger.error(f"Failed to plot prediction performance: {e}")
            return render_text_figure(f"Failed to plot prediction performance: {e}", 
                                     f"Prediction Performance - {game.upper()}")

    def plot_strategy_comparison(self, save_path: Optional[str] = None) -> Figure:
        """Compare performance of different strategies"""
        try:
            from tracking.prediction_logger import PredictionLogger
            from gui.chart_widgets import render_text_figure

            logger_instance = PredictionLogger()
            performance = logger_instance.get_strategy_performance(days=90)

            if not performance:
                self.logger.info("No strategy performance data available")
                return render_text_figure("No strategy performance data available", 
                                         "Strategy Comparison")

            strategies = list(performance.keys())
            win_rates = [performance[s]['win_rate'] for s in strategies]
            avg_matches = [performance[s]['avg_matches'] for s in strategies]
            total_predictions = [performance[s]['total_predictions'] for s in strategies]

            # Create figure using Figure instead of plt.subplots
            fig = Figure(figsize=(15, 5))

            # Create three subplots
            ax1 = fig.add_subplot(131)  # 1 row, 3 cols, 1st subplot
            ax2 = fig.add_subplot(132)  # 1 row, 3 cols, 2nd subplot
            ax3 = fig.add_subplot(133)  # 1 row, 3 cols, 3rd subplot

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

            fig.tight_layout()

            if save_path:
                fig.savefig(save_path, dpi=300, bbox_inches='tight')

            return fig

        except Exception as e:
            self.logger.error(f"Failed to plot strategy comparison: {e}")
            return render_text_figure(f"Failed to plot strategy comparison: {e}", 
                                     "Strategy Comparison")

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
