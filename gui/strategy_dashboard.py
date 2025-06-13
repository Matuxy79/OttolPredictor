"""
Strategy performance dashboard showing strategy performance metrics
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QTableWidget, QTableWidgetItem, QGroupBox,
                            QPushButton, QComboBox, QFrame, QHeaderView)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor

import logging
from typing import Dict, List, Any
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

from strategies.adaptive_selector import AdaptiveStrategySelector
from core.predictor import LottoPredictor

logger = logging.getLogger(__name__)

class StrategyDashboard(QWidget):
    """Dashboard showing strategy performance metrics"""
    
    strategy_selected = pyqtSignal(str)  # Signal emitted when user selects a strategy
    
    def __init__(self, parent_window=None):
        super().__init__(parent_window)
        self.parent = parent_window
        self.strategy_selector = AdaptiveStrategySelector()
        self.predictor = LottoPredictor()
        self.current_game = "649"  # Default game
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dashboard UI"""
        main_layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Strategy Performance Dashboard")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Game selector
        game_layout = QHBoxLayout()
        game_layout.addWidget(QLabel("Game:"))
        self.game_combo = QComboBox()
        self.game_combo.addItems(["Lotto 6/49", "Lotto Max"])
        self.game_combo.currentTextChanged.connect(self.on_game_changed)
        game_layout.addWidget(self.game_combo)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        game_layout.addWidget(refresh_btn)
        
        game_layout.addStretch()
        main_layout.addLayout(game_layout)
        
        # Strategy summary section
        summary_group = QGroupBox("Strategy Performance Summary")
        summary_layout = QVBoxLayout(summary_group)
        
        # Best strategy display
        self.best_strategy_frame = QFrame()
        self.best_strategy_frame.setFrameStyle(QFrame.StyledPanel)
        self.best_strategy_frame.setStyleSheet("""
            QFrame {
                background-color: #e8f5e9;
                border: 1px solid #81c784;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        
        best_strategy_layout = QVBoxLayout(self.best_strategy_frame)
        self.best_strategy_label = QLabel("🏆 Best Strategy: Analyzing...")
        self.best_strategy_label.setFont(QFont("Arial", 12, QFont.Bold))
        best_strategy_layout.addWidget(self.best_strategy_label)
        
        self.best_strategy_score = QLabel("Score: Calculating...")
        best_strategy_layout.addWidget(self.best_strategy_score)
        
        self.best_strategy_desc = QLabel("Description: Waiting for data...")
        self.best_strategy_desc.setWordWrap(True)
        best_strategy_layout.addWidget(self.best_strategy_desc)
        
        summary_layout.addWidget(self.best_strategy_frame)
        
        # Strategy comparison table
        self.strategy_table = QTableWidget()
        self.strategy_table.setColumnCount(4)
        self.strategy_table.setHorizontalHeaderLabels([
            "Strategy", "Score", "Win Rate", "Use Strategy"
        ])
        self.strategy_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.strategy_table.setAlternatingRowColors(True)
        
        summary_layout.addWidget(self.strategy_table)
        
        main_layout.addWidget(summary_group)
        
        # Performance chart
        chart_group = QGroupBox("Strategy Comparison Chart")
        chart_layout = QVBoxLayout(chart_group)
        
        # Create matplotlib figure for the chart
        self.figure = Figure(figsize=(8, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        chart_layout.addWidget(self.canvas)
        
        main_layout.addWidget(chart_group)
        
        # Set initial data
        self.refresh_data()
        
    def on_game_changed(self, game_text):
        """Handle game selection change"""
        if "6/49" in game_text:
            self.current_game = "649"
        elif "Max" in game_text:
            self.current_game = "max"
        else:
            self.current_game = "649"  # Default
            
        self.refresh_data()
        
    def refresh_data(self):
        """Refresh all dashboard data"""
        try:
            # Get performance data from the strategy selector
            performance = self.strategy_selector.get_performance_summary(self.current_game)
            
            if not performance or 'error' in performance:
                self.show_no_data_message()
                return
                
            # Update best strategy display
            best_strategy = performance.get('best_strategy')
            if best_strategy:
                strategy_name = self.strategy_selector.get_strategy_name(best_strategy)
                self.best_strategy_label.setText(f"🏆 Best Strategy: {strategy_name}")
                
                avg_score = performance.get('avg_scores', {}).get(best_strategy, 0.0)
                self.best_strategy_score.setText(f"Score: {avg_score:.4f}")
                
                self.best_strategy_desc.setText(self._get_strategy_description(best_strategy))
            
            # Update strategy table
            self._update_strategy_table(performance)
            
            # Update performance chart
            self._update_performance_chart(performance)
            
        except Exception as e:
            logger.error(f"Error refreshing strategy dashboard: {e}")
            self.show_error_message(str(e))
            
    def _update_strategy_table(self, performance: Dict):
        """Update the strategy comparison table"""
        try:
            # Get strategy ranking and scores
            strategy_ranking = performance.get('strategy_ranking', [])
            avg_scores = performance.get('avg_scores', {})
            strategy_wins = performance.get('strategy_wins', {})
            
            # Clear table
            self.strategy_table.setRowCount(0)
            
            # Add rows for each strategy
            for i, strategy in enumerate(strategy_ranking):
                self.strategy_table.insertRow(i)
                
                # Strategy name
                name_item = QTableWidgetItem(self.strategy_selector.get_strategy_name(strategy))
                self.strategy_table.setItem(i, 0, name_item)
                
                # Score
                score = avg_scores.get(strategy, 0.0)
                score_item = QTableWidgetItem(f"{score:.4f}")
                self.strategy_table.setItem(i, 1, score_item)
                
                # Win rate (from strategy wins)
                wins = strategy_wins.get(strategy, 0)
                total = sum(strategy_wins.values())
                win_rate = (wins / total * 100) if total > 0 else 0
                win_rate_item = QTableWidgetItem(f"{win_rate:.1f}%")
                self.strategy_table.setItem(i, 2, win_rate_item)
                
                # Use strategy button
                use_btn = QPushButton("Use")
                use_btn.setProperty("strategy", strategy)
                use_btn.clicked.connect(self._on_use_strategy_clicked)
                self.strategy_table.setCellWidget(i, 3, use_btn)
                
                # Color best strategy row
                if strategy == performance.get('best_strategy'):
                    for col in range(3):
                        self.strategy_table.item(i, col).setBackground(QColor("#e8f5e9"))
                
        except Exception as e:
            logger.error(f"Error updating strategy table: {e}")
            
    def _update_performance_chart(self, performance: Dict):
        """Update the performance comparison chart"""
        try:
            # Clear the figure
            self.figure.clear()
            
            # Get data for the chart
            strategy_names = []
            scores = []
            
            # Sort strategies by score
            avg_scores = performance.get('avg_scores', {})
            sorted_strategies = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)
            
            for strategy, score in sorted_strategies:
                strategy_names.append(self.strategy_selector.get_strategy_name(strategy))
                scores.append(score)
                
            # Create subplot
            ax = self.figure.add_subplot(111)
            
            # Create bar chart
            bars = ax.bar(strategy_names, scores, color='#4CAF50')
            
            # Add value labels on top of bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                        f'{height:.3f}', ha='center', va='bottom')
            
            # Set labels and title
            ax.set_xlabel('Strategy')
            ax.set_ylabel('Performance Score')
            ax.set_title(f'Strategy Performance Comparison - {self.current_game.upper()}')
            
            # Rotate x-axis labels for better readability
            ax.set_xticklabels(strategy_names, rotation=45, ha='right')
            
            # Adjust layout and redraw
            self.figure.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error updating performance chart: {e}")
            
    def _on_use_strategy_clicked(self):
        """Handle click on 'Use Strategy' button"""
        # Get the strategy from the button's property
        button = self.sender()
        strategy = button.property("strategy")
        
        # Emit signal with selected strategy
        self.strategy_selected.emit(strategy)
        
    def _get_strategy_description(self, strategy: str) -> str:
        """Get a human-readable description of a strategy"""
        descriptions = {
            'uniform': "Uses the overall frequency of numbers across all historical draws, giving equal weight to all draws regardless of when they occurred.",
            'recency_light': "Emphasizes recent draws with a light weighting, giving slightly more importance to recent results while still considering historical patterns.",
            'recency_medium': "Applies medium weighting to recent draws, creating a balance between recent trends and historical patterns.",
            'recency_heavy': "Heavily weights recent draws, focusing primarily on the most recent lottery results and trends.",
            'era_based': "Analyzes different lottery eras separately, accounting for rule changes and different periods in the game's history.",
            'random': "Generates completely random selections without any analysis of historical data."
        }
        
        return descriptions.get(strategy, "No description available")
        
    def show_no_data_message(self):
        """Display a message when no data is available"""
        self.best_strategy_label.setText("🏆 Best Strategy: No data available")
        self.best_strategy_score.setText("Score: N/A")
        self.best_strategy_desc.setText("Run some strategy backtests first to see performance data.")
        
        # Clear table
        self.strategy_table.setRowCount(0)
        
        # Clear chart
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.text(0.5, 0.5, "No performance data available yet", 
                horizontalalignment='center', verticalalignment='center',
                transform=ax.transAxes)
        self.canvas.draw()
        
    def show_error_message(self, error_msg: str):
        """Display an error message"""
        self.best_strategy_label.setText("❌ Error loading strategy data")
        self.best_strategy_score.setText("Score: N/A")
        self.best_strategy_desc.setText(f"Error: {error_msg}")