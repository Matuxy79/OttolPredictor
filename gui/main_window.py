"""
Main GUI Window for Saskatoon Lotto Predictor
Sister-friendly lottery prediction interface
"""

import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QTabWidget, QLabel, QPushButton, QTableWidget,
                            QTableWidgetItem, QComboBox, QTextEdit, QGroupBox,
                            QGridLayout, QProgressBar, QStatusBar, QSplitter)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_manager import get_data_manager
import logging

logger = logging.getLogger(__name__)

class SaskatoonLottoPredictor(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.data_manager = get_data_manager()
        self.init_ui()
        self.load_initial_data()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("🎲 Saskatoon Lotto Predictor")
        self.setGeometry(100, 100, 1200, 800)
        
        # Set application style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #e1e1e1;
                border: 1px solid #cccccc;
                padding: 8px 16px;
                margin: 2px;
            }
            QTabBar::tab:selected {
                background-color: #4CAF50;
                color: white;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin: 5px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Create top toolbar
        self.create_toolbar(layout)
        
        # Create main content area with tabs
        self.create_main_tabs(layout)
        
        # Create status bar
        self.create_status_bar()
    
    def create_toolbar(self, parent_layout):
        """Create top toolbar with main actions"""
        toolbar_widget = QWidget()
        toolbar_layout = QHBoxLayout(toolbar_widget)
        
        # Game selection
        game_label = QLabel("Game:")
        game_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.game_combo = QComboBox()
        self.game_combo.addItems([
            "Lotto 6/49", "Lotto Max", "Western 649", 
            "Western Max", "Daily Grand"
        ])
        self.game_combo.currentTextChanged.connect(self.on_game_changed)
        
        # Quick action buttons
        self.refresh_btn = QPushButton("🔄 Refresh Data")
        self.refresh_btn.clicked.connect(self.refresh_data)
        
        self.quick_pick_btn = QPushButton("🎲 Quick Pick")
        self.quick_pick_btn.clicked.connect(self.generate_quick_pick)
        
        self.smart_pick_btn = QPushButton("🧠 Smart Pick")
        self.smart_pick_btn.clicked.connect(self.generate_smart_pick)
        
        # Add widgets to toolbar
        toolbar_layout.addWidget(game_label)
        toolbar_layout.addWidget(self.game_combo)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.refresh_btn)
        toolbar_layout.addWidget(self.quick_pick_btn)
        toolbar_layout.addWidget(self.smart_pick_btn)
        
        parent_layout.addWidget(toolbar_widget)
    
    def create_main_tabs(self, parent_layout):
        """Create main tabbed interface"""
        self.tab_widget = QTabWidget()
        
        # Dashboard tab
        self.create_dashboard_tab()
        
        # Recent Draws tab
        self.create_recent_draws_tab()
        
        # Analytics tab
        self.create_analytics_tab()
        
        # Predictions tab
        self.create_predictions_tab()
        
        parent_layout.addWidget(self.tab_widget)
    
    def create_dashboard_tab(self):
        """Create dashboard overview tab"""
        dashboard_widget = QWidget()
        layout = QVBoxLayout(dashboard_widget)
        
        # Game summary section
        summary_group = QGroupBox("📊 Game Summary")
        summary_layout = QGridLayout(summary_group)
        
        self.total_draws_label = QLabel("Total Draws: Loading...")
        self.date_range_label = QLabel("Date Range: Loading...")
        self.last_updated_label = QLabel("Last Updated: Loading...")
        
        summary_layout.addWidget(self.total_draws_label, 0, 0)
        summary_layout.addWidget(self.date_range_label, 0, 1)
        summary_layout.addWidget(self.last_updated_label, 1, 0, 1, 2)
        
        layout.addWidget(summary_group)
        
        # Quick stats section
        stats_group = QGroupBox("🔥 Quick Stats")
        stats_layout = QGridLayout(stats_group)
        
        self.hot_numbers_label = QLabel("Hot Numbers: Loading...")
        self.cold_numbers_label = QLabel("Cold Numbers: Loading...")
        
        stats_layout.addWidget(QLabel("Most Frequent:"), 0, 0)
        stats_layout.addWidget(self.hot_numbers_label, 0, 1)
        stats_layout.addWidget(QLabel("Least Frequent:"), 1, 0)
        stats_layout.addWidget(self.cold_numbers_label, 1, 1)
        
        layout.addWidget(stats_group)
        
        # Recent activity
        activity_group = QGroupBox("📅 Recent Activity")
        activity_layout = QVBoxLayout(activity_group)
        
        self.recent_activity_text = QTextEdit()
        self.recent_activity_text.setMaximumHeight(150)
        self.recent_activity_text.setReadOnly(True)
        
        activity_layout.addWidget(self.recent_activity_text)
        layout.addWidget(activity_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(dashboard_widget, "📊 Dashboard")
    
    def create_recent_draws_tab(self):
        """Create recent draws table tab"""
        draws_widget = QWidget()
        layout = QVBoxLayout(draws_widget)
        
        # Table for recent draws
        self.draws_table = QTableWidget()
        self.draws_table.setColumnCount(6)
        self.draws_table.setHorizontalHeaderLabels([
            "Date", "Numbers", "Bonus", "Gold Ball", "Day", "Notes"
        ])
        
        # Make table look nice
        self.draws_table.horizontalHeader().setStretchLastSection(True)
        self.draws_table.setAlternatingRowColors(True)
        self.draws_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        layout.addWidget(self.draws_table)
        
        self.tab_widget.addTab(draws_widget, "📅 Recent Draws")
    
    def create_analytics_tab(self):
        """Create analytics and charts tab"""
        analytics_widget = QWidget()
        layout = QVBoxLayout(analytics_widget)
        
        # Placeholder for future charts
        placeholder_label = QLabel("📈 Analytics Charts Coming Soon!")
        placeholder_label.setAlignment(Qt.AlignCenter)
        placeholder_label.setFont(QFont("Arial", 16))
        placeholder_label.setStyleSheet("color: #666; padding: 50px;")
        
        layout.addWidget(placeholder_label)
        
        self.tab_widget.addTab(analytics_widget, "📈 Analytics")
    
    def create_predictions_tab(self):
        """Create predictions interface tab"""
        predictions_widget = QWidget()
        layout = QVBoxLayout(predictions_widget)
        
        # Prediction results section
        results_group = QGroupBox("🎯 Your Predictions")
        results_layout = QVBoxLayout(results_group)
        
        self.predictions_text = QTextEdit()
        self.predictions_text.setMaximumHeight(200)
        self.predictions_text.setReadOnly(True)
        self.predictions_text.setPlaceholderText("Click 'Quick Pick' or 'Smart Pick' to generate predictions...")
        
        results_layout.addWidget(self.predictions_text)
        layout.addWidget(results_group)
        
        # Prediction options
        options_group = QGroupBox("⚙️ Prediction Options")
        options_layout = QGridLayout(options_group)
        
        # Strategy selection
        strategy_label = QLabel("Strategy:")
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            "Balanced (Recommended)",
            "Hot Numbers Focus",
            "Cold Numbers Focus", 
            "Random Selection"
        ])
        
        options_layout.addWidget(strategy_label, 0, 0)
        options_layout.addWidget(self.strategy_combo, 0, 1)
        
        # Number of sets
        sets_label = QLabel("Number of Sets:")
        self.sets_combo = QComboBox()
        self.sets_combo.addItems(["1", "2", "3", "5", "10"])
        self.sets_combo.setCurrentText("3")
        
        options_layout.addWidget(sets_label, 1, 0)
        options_layout.addWidget(self.sets_combo, 1, 1)
        
        layout.addWidget(options_group)
        layout.addStretch()
        
        self.tab_widget.addTab(predictions_widget, "🎯 Predictions")
    
    def create_status_bar(self):
        """Create status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Add progress bar for long operations
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        self.status_bar.showMessage("Ready")
    
    def load_initial_data(self):
        """Load initial data for the default game"""
        self.update_dashboard()
        self.update_recent_draws_table()
    
    def on_game_changed(self, game_text):
        """Handle game selection change"""
        # Convert display name to internal game code
        game_map = {
            "Lotto 6/49": "649",
            "Lotto Max": "max",
            "Western 649": "western649",
            "Western Max": "westernmax",
            "Daily Grand": "dailygrand"
        }
        
        self.current_game = game_map.get(game_text, "649")
        self.status_bar.showMessage(f"Switched to {game_text}")
        
        # Update all displays
        self.update_dashboard()
        self.update_recent_draws_table()
    
    def update_dashboard(self):
        """Update dashboard with current game data"""
        try:
            current_game = getattr(self, 'current_game', '649')
            summary = self.data_manager.get_game_summary(current_game)
            
            # Update summary labels
            self.total_draws_label.setText(f"Total Draws: {summary['total_draws']:,}")
            self.date_range_label.setText(f"Date Range: {summary['date_range']}")
            self.last_updated_label.setText(f"Last Updated: {summary['last_updated']}")
            
            # Update hot/cold numbers
            hot_nums = ", ".join(map(str, summary['most_frequent_numbers'][:6]))
            cold_nums = ", ".join(map(str, summary['least_frequent_numbers'][:6]))
            
            self.hot_numbers_label.setText(hot_nums or "No data")
            self.cold_numbers_label.setText(cold_nums or "No data")
            
            # Update recent activity
            self.recent_activity_text.clear()
            self.recent_activity_text.append(f"📊 Loaded {summary['total_draws']} draws for {current_game.upper()}")
            self.recent_activity_text.append(f"🔥 Hot numbers: {hot_nums}")
            self.recent_activity_text.append(f"❄️ Cold numbers: {cold_nums}")
            self.recent_activity_text.append(f"📅 Recent draws (30 days): {summary['recent_draws']}")
            
        except Exception as e:
            logger.error(f"Error updating dashboard: {e}")
            self.status_bar.showMessage(f"Error loading data: {e}")
    
    def update_recent_draws_table(self):
        """Update the recent draws table"""
        try:
            current_game = getattr(self, 'current_game', '649')
            data = self.data_manager.get_recent_draws(current_game, days=60)
            
            self.draws_table.setRowCount(min(len(data), 20))  # Show max 20 draws
            
            for row, (_, draw) in enumerate(data.head(20).iterrows()):
                # Date
                date_item = QTableWidgetItem(str(draw.get('date', 'Unknown')))
                self.draws_table.setItem(row, 0, date_item)
                
                # Numbers
                numbers_item = QTableWidgetItem(str(draw.get('numbers', '')))
                self.draws_table.setItem(row, 1, numbers_item)
                
                # Bonus
                bonus_item = QTableWidgetItem(str(draw.get('bonus', '')))
                self.draws_table.setItem(row, 2, bonus_item)
                
                # Gold Ball
                gold_ball_item = QTableWidgetItem(str(draw.get('gold_ball', '')))
                self.draws_table.setItem(row, 3, gold_ball_item)
                
                # Day of week
                day_item = QTableWidgetItem(str(draw.get('day_of_week', '')))
                self.draws_table.setItem(row, 4, day_item)
                
                # Notes (placeholder)
                notes_item = QTableWidgetItem("")
                self.draws_table.setItem(row, 5, notes_item)
            
            self.draws_table.resizeColumnsToContents()
            
        except Exception as e:
            logger.error(f"Error updating draws table: {e}")
    
    def refresh_data(self):
        """Refresh all data from files"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        try:
            self.data_manager.refresh_all_data()
            self.update_dashboard()
            self.update_recent_draws_table()
            self.status_bar.showMessage("Data refreshed successfully")
        except Exception as e:
            self.status_bar.showMessage(f"Error refreshing data: {e}")
        finally:
            self.progress_bar.setVisible(False)
    
    def generate_quick_pick(self):
        """Generate random number picks"""
        import random
        
        current_game = getattr(self, 'current_game', '649')
        num_sets = int(self.sets_combo.currentText())
        
        # Define number ranges for each game
        game_config = {
            '649': {'count': 6, 'max': 49, 'bonus_max': 49},
            'max': {'count': 7, 'max': 50, 'bonus_max': 50},
            'western649': {'count': 6, 'max': 49, 'bonus_max': 49},
            'westernmax': {'count': 7, 'max': 50, 'bonus_max': 50},
            'dailygrand': {'count': 5, 'max': 49, 'bonus_max': 7}
        }
        
        config = game_config.get(current_game, game_config['649'])
        
        self.predictions_text.clear()
        self.predictions_text.append(f"🎲 Quick Pick Results for {current_game.upper()}:")
        self.predictions_text.append("=" * 40)
        
        for i in range(num_sets):
            # Generate main numbers
            numbers = sorted(random.sample(range(1, config['max'] + 1), config['count']))
            
            # Generate bonus number
            bonus = random.randint(1, config['bonus_max'])
            
            numbers_str = " - ".join(f"{n:02d}" for n in numbers)
            self.predictions_text.append(f"Set {i+1}: {numbers_str}  +{bonus:02d}")
        
        self.predictions_text.append("")
        self.predictions_text.append("💡 These are random selections. Use Smart Pick for data-driven predictions!")
        
        self.status_bar.showMessage(f"Generated {num_sets} quick pick sets")
    
    def generate_smart_pick(self):
        """Generate data-driven number picks"""
        current_game = getattr(self, 'current_game', '649')
        strategy = self.strategy_combo.currentText()
        
        try:
            frequency_data = self.data_manager.get_number_frequency(current_game)
            
            if not frequency_data:
                self.predictions_text.clear()
                self.predictions_text.append("❌ No historical data available for smart predictions.")
                self.predictions_text.append("Try Quick Pick instead or update your data.")
                return
            
            self.predictions_text.clear()
            self.predictions_text.append(f"🧠 Smart Pick Results for {current_game.upper()}:")
            self.predictions_text.append(f"Strategy: {strategy}")
            self.predictions_text.append("=" * 40)
            
            # Generate predictions based on strategy
            predictions = self._generate_smart_predictions(frequency_data, strategy, current_game)
            
            for i, prediction in enumerate(predictions):
                numbers_str = " - ".join(f"{n:02d}" for n in prediction['numbers'])
                confidence = "⭐" * prediction['confidence']
                self.predictions_text.append(f"Set {i+1}: {numbers_str}  +{prediction['bonus']:02d}  {confidence}")
            
            self.predictions_text.append("")
            self.predictions_text.append(f"📊 Based on analysis of {len(frequency_data)} historical draws")
            
            self.status_bar.showMessage(f"Generated smart predictions using {strategy}")
            
        except Exception as e:
            logger.error(f"Error generating smart pick: {e}")
            self.status_bar.showMessage(f"Error generating predictions: {e}")
    
    def _generate_smart_predictions(self, frequency_data, strategy, game):
        """Generate smart predictions based on frequency data"""
        import random
        
        # Get sorted numbers by frequency
        sorted_numbers = sorted(frequency_data.items(), key=lambda x: x[1], reverse=True)
        
        # Game configuration
        game_config = {
            '649': {'count': 6, 'max': 49},
            'max': {'count': 7, 'max': 50},
            'western649': {'count': 6, 'max': 49},
            'westernmax': {'count': 7, 'max': 50},
            'dailygrand': {'count': 5, 'max': 49}
        }
        
        config = game_config.get(game, game_config['649'])
        num_sets = int(self.sets_combo.currentText())
        
        predictions = []
        
        for _ in range(num_sets):
            if "Hot Numbers" in strategy:
                # Focus on most frequent numbers
                hot_numbers = [num for num, freq in sorted_numbers[:15]]
                numbers = sorted(random.sample(hot_numbers, min(config['count'], len(hot_numbers))))
                confidence = 4
                
            elif "Cold Numbers" in strategy:
                # Focus on least frequent numbers
                cold_numbers = [num for num, freq in sorted_numbers[-15:]]
                numbers = sorted(random.sample(cold_numbers, min(config['count'], len(cold_numbers))))
                confidence = 2
                
            else:  # Balanced
                # Mix of hot, medium, and cold numbers
                hot_numbers = [num for num, freq in sorted_numbers[:10]]
                cold_numbers = [num for num, freq in sorted_numbers[-10:]]
                medium_numbers = [num for num, freq in sorted_numbers[10:-10]]
                
                # Select 2 hot, 2 cold, rest medium
                selected = []
                selected.extend(random.sample(hot_numbers, min(2, len(hot_numbers))))
                selected.extend(random.sample(cold_numbers, min(2, len(cold_numbers))))
                
                remaining = config['count'] - len(selected)
                if remaining > 0 and medium_numbers:
                    selected.extend(random.sample(medium_numbers, min(remaining, len(medium_numbers))))
                
                # Fill remaining with any available numbers if needed
                while len(selected) < config['count']:
                    available = [i for i in range(1, config['max'] + 1) if i not in selected]
                    if available:
                        selected.append(random.choice(available))
                    else:
                        break
                
                numbers = sorted(selected[:config['count']])
                confidence = 3
            
            # Ensure we have the right number of numbers
            while len(numbers) < config['count']:
                available = [i for i in range(1, config['max'] + 1) if i not in numbers]
                if available:
                    numbers.append(random.choice(available))
                    numbers.sort()
                else:
                    break
            
            # Generate bonus number
            bonus = random.randint(1, config['max'])
            
            predictions.append({
                'numbers': numbers,
                'bonus': bonus,
                'confidence': confidence
            })
        
        return predictions


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Saskatoon Lotto Predictor")
    
    # Set application icon (if available)
    # app.setWindowIcon(QIcon("icon.png"))
    
    window = SaskatoonLottoPredictor()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()