"""
Main GUI Window for Saskatoon Lotto Predictor
Sister-friendly lottery prediction interface
"""

import sys
import os
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QTabWidget, QLabel, QPushButton, QTableWidget,
                            QTableWidgetItem, QComboBox, QTextEdit, QGroupBox,
                            QGridLayout, QProgressBar, QStatusBar, QSplitter,
                            QScrollArea, QFrame, QMessageBox, QInputDialog)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QRunnable, QThreadPool, QObject
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor, QPixmap
from datetime import datetime

# For matplotlib integration
import matplotlib
matplotlib.use('Qt5Agg')  # Set backend before importing pyplot
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import logging

# Suppress matplotlib font warnings
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)

# Import embedded chart widgets
from gui.chart_widgets import EmbeddedChartWidget

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logging_config import get_logger
from analytics import get_analytics_engine
from wclc_scraper import WCLCScraper
from config import AppConfig
from tracking.prediction_logger import PredictionLogger

# Import new modules
from core.data_manager import get_data_manager
from core.predictor import LottoPredictor
from strategies.adaptive_selector import AdaptiveStrategySelector
from gui.strategy_dashboard import StrategyDashboard
import json

logger = get_logger(__name__)

class PredictionWorker(QThread):
    """Worker thread for prediction generation to prevent GUI freezing"""

    prediction_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, predictor, game, strategy):
        super().__init__()
        self.predictor = predictor
        self.game = game
        self.strategy = strategy

    def run(self):
        try:
            # Use the new predictor's predict_numbers method
            prediction = self.predictor.predict_numbers(self.game, self.strategy)
            self.prediction_ready.emit(prediction)
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            self.error_occurred.emit(str(e))

# Worker thread for scraping
class ScraperSignals(QObject):
    """Signals for scraper worker thread"""
    started = pyqtSignal()
    finished = pyqtSignal(bool, str)  # Success flag, result message
    progress = pyqtSignal(int, str)   # Progress value, status message
    error = pyqtSignal(str)           # Error message

class ScraperWorker(QRunnable):
    """Worker thread for running the scraper"""

    def __init__(self, game, batch=False, max_months=None, output_format='csv'):
        """Initialize the worker thread"""
        super().__init__()
        self.game = game
        self.batch = batch
        self.max_months = max_months
        self.output_format = output_format
        self.signals = ScraperSignals()

    def run(self):
        """Run the scraper in a background thread"""
        try:
            self.signals.started.emit()
            self.signals.progress.emit(0, f"Starting scraper for {self.game}...")

            # Initialize scraper
            scraper = WCLCScraper(max_retries=3, timeout=15)

            # Get URL for the game
            url = scraper.get_game_url(self.game)
            self.signals.progress.emit(10, f"Got URL for {self.game}: {url}")

            # Scrape data
            if self.batch:
                self.signals.progress.emit(20, f"Starting batch scrape for {self.game} ({self.max_months} months)...")
                data = scraper.scrape_batch_history(url, self.game, self.max_months)
            else:
                self.signals.progress.emit(20, f"Scraping current page for {self.game}...")
                html = scraper.fetch_html_with_retry(url)
                data = scraper._parse_draws_by_game(html, self.game)

            if not data:
                self.signals.error.emit(f"No data found for {self.game}")
                self.signals.finished.emit(False, f"No data found for {self.game}")
                return

            self.signals.progress.emit(70, f"Scraped {len(data)} draws for {self.game}")

            # Generate output filename
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            batch_suffix = "_batch" if self.batch else ""

            if self.output_format == 'csv':
                output_file = f"wclc_{self.game}_results{batch_suffix}_{timestamp}.csv"
                scraper.save_to_csv(data, output_file)
                self.signals.progress.emit(90, f"Saved data to {output_file}")
                result_message = f"Successfully scraped {len(data)} draws for {self.game} and saved to {output_file}"
            elif self.output_format == 'sqlite':
                output_file = f"wclc_{self.game}_results{batch_suffix}_{timestamp}.db"
                scraper.save_to_sqlite(data, output_file)
                self.signals.progress.emit(90, f"Saved data to {output_file}")
                result_message = f"Successfully scraped {len(data)} draws for {self.game} and saved to {output_file}"
            elif self.output_format == 'both':
                csv_file = f"wclc_{self.game}_results{batch_suffix}_{timestamp}.csv"
                db_file = f"wclc_{self.game}_results{batch_suffix}_{timestamp}.db"
                scraper.save_to_csv(data, csv_file)
                scraper.save_to_sqlite(data, db_file)
                self.signals.progress.emit(90, f"Saved data to {csv_file} and {db_file}")
                result_message = f"Successfully scraped {len(data)} draws for {self.game} and saved to {csv_file} and {db_file}"

            self.signals.progress.emit(100, "Done!")
            self.signals.finished.emit(True, result_message)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.signals.error.emit(str(e))
            self.signals.finished.emit(False, f"Error: {str(e)}")

class SaskatoonLottoPredictor(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()

        # Initialize logger
        import logging
        self.logger = logging.getLogger(__name__)

        # Initialize prediction components
        self.data_manager = get_data_manager()
        self.analytics_engine = get_analytics_engine()
        self.predictor = LottoPredictor()  # Use new predictor
        self.strategy_selector = AdaptiveStrategySelector()  # Add strategy selector
        self.prediction_logger = PredictionLogger()
        self.current_prediction = None
        self.current_strategy = 'auto'  # Default to auto strategy selection

        self.thread_pool = QThreadPool()
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

    def setup_embedded_charts(self):
        """Setup embedded chart widgets instead of layout"""
        # Create embedded chart widgets for analytics tab
        self.frequency_chart_widget = EmbeddedChartWidget()
        self.trend_chart_widget = EmbeddedChartWidget()

        # Add to your existing analytics layout
        # (Replace wherever you had self.charts_layout)
        if hasattr(self, 'charts_layout'):
            self.charts_layout.addWidget(self.frequency_chart_widget)
            self.charts_layout.addWidget(self.trend_chart_widget)

    def create_toolbar(self, parent_layout):
        """Create top toolbar with main actions"""
        toolbar_widget = QWidget()
        toolbar_layout = QHBoxLayout(toolbar_widget)

        # Game selection
        from config import AppConfig
        game_label = QLabel("Game:")
        game_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.game_combo = QComboBox()

        # Use centralized game configuration
        game_display_names = [AppConfig.get_game_display_name(game) for game in AppConfig.get_supported_games()]
        self.game_combo.addItems(game_display_names)
        self.game_combo.currentTextChanged.connect(self.on_game_changed)

        # Quick action buttons
        self.refresh_btn = QPushButton("🔄 Smart Refresh")
        self.refresh_btn.setToolTip("Quickly refresh recent data only")
        self.refresh_btn.clicked.connect(lambda: self.refresh_data(full_refresh=False))

        # Add full refresh button
        self.full_refresh_btn = QPushButton("🔄 Full Refresh")
        self.full_refresh_btn.setToolTip("Perform complete refresh of all data (slower)")
        self.full_refresh_btn.clicked.connect(lambda: self.refresh_data(full_refresh=True))

        self.quick_pick_btn = QPushButton("🎲 Quick Pick")
        self.quick_pick_btn.clicked.connect(self.generate_quick_pick)

        self.smart_pick_btn = QPushButton("🧠 Smart Pick")
        self.smart_pick_btn.clicked.connect(self.generate_prediction)

        # Add widgets to toolbar
        toolbar_layout.addWidget(game_label)
        toolbar_layout.addWidget(self.game_combo)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.refresh_btn)
        toolbar_layout.addWidget(self.full_refresh_btn)
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

        # Strategy Dashboard tab (new)
        self.create_strategy_dashboard_tab()

        # Scraping tab
        self.create_scraping_tab()

        parent_layout.addWidget(self.tab_widget)

    def create_dashboard_tab(self):
        """Create dashboard overview tab"""
        dashboard_widget = QWidget()
        layout = QVBoxLayout(dashboard_widget)

        # Data status section
        data_status_group = QGroupBox("📈 Data Status")
        data_status_layout = QVBoxLayout(data_status_group)

        self.data_649_status = QLabel("❓ Lotto 6/49: Checking data...")
        self.data_max_status = QLabel("❓ Lotto Max: Checking data...")

        data_status_layout.addWidget(self.data_649_status)
        data_status_layout.addWidget(self.data_max_status)

        layout.addWidget(data_status_group)

        # Recent draws section
        recent_draws_group = QGroupBox("🎯 Recent Draws")
        recent_draws_layout = QVBoxLayout(recent_draws_group)

        self.recent_649_display = QLabel("Loading recent Lotto 6/49 draws...")
        self.recent_max_display = QLabel("Loading recent Lotto Max draws...")

        recent_draws_layout.addWidget(self.recent_649_display)
        recent_draws_layout.addWidget(self.recent_max_display)

        layout.addWidget(recent_draws_group)

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

        # Quick stats section with dynamic title
        self.stats_group = QGroupBox("🔥 Quick Stats")
        stats_layout = QGridLayout(self.stats_group)

        self.hot_numbers_label = QLabel("Hot Numbers: Loading...")
        self.cold_numbers_label = QLabel("Cold Numbers: Loading...")

        stats_layout.addWidget(QLabel("Most Frequent:"), 0, 0)
        stats_layout.addWidget(self.hot_numbers_label, 0, 1)
        stats_layout.addWidget(QLabel("Least Frequent:"), 1, 0)
        stats_layout.addWidget(self.cold_numbers_label, 1, 1)

        layout.addWidget(self.stats_group)

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

        # Controls for the draws table
        controls_layout = QHBoxLayout()

        # Game selector for draws table
        controls_layout.addWidget(QLabel("Game:"))
        self.draws_game_combo = QComboBox()

        # Add game options with data
        self.draws_game_combo.addItem("Lotto 6/49", "649")
        self.draws_game_combo.addItem("Lotto Max", "max")

        # Connect signal to update table when game changes
        self.draws_game_combo.currentIndexChanged.connect(self.update_draws_table)
        controls_layout.addWidget(self.draws_game_combo)

        # Add refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.update_draws_table)
        controls_layout.addWidget(refresh_btn)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

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
        """Create comprehensive analytics tab with prediction performance"""
        analytics_widget = QWidget()
        layout = QVBoxLayout(analytics_widget)

        # Analytics controls
        controls_layout = QHBoxLayout()

        # Game selector for analytics
        controls_layout.addWidget(QLabel("Analyze:"))
        self.analytics_game_selector = QComboBox()
        self.analytics_game_selector.addItems(["Lotto 6/49", "Lotto Max"])
        self.analytics_game_selector.currentTextChanged.connect(self.update_analytics_charts)
        controls_layout.addWidget(self.analytics_game_selector)

        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh Charts")
        refresh_btn.clicked.connect(self.update_analytics_charts)
        controls_layout.addWidget(refresh_btn)

        # Export button
        export_btn = QPushButton("📊 Export Analytics")
        export_btn.clicked.connect(self.export_analytics_data)
        controls_layout.addWidget(export_btn)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Analytics insights summary
        self.insights_frame = QFrame()
        self.insights_frame.setFrameStyle(QFrame.Box)
        self.insights_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 10px;
                margin: 5px;
            }
        """)

        insights_layout = QHBoxLayout(self.insights_frame)

        self.total_predictions_label = QLabel("📈 Total Predictions: Loading...")
        insights_layout.addWidget(self.total_predictions_label)

        self.best_strategy_label = QLabel("🏆 Best Strategy: Loading...")
        insights_layout.addWidget(self.best_strategy_label)

        self.win_rate_label = QLabel("🎯 Win Rate: Loading...")
        insights_layout.addWidget(self.win_rate_label)

        layout.addWidget(self.insights_frame)

        # Create tab widget for different chart types
        self.analytics_tabs = QTabWidget()

        # Historical Data Tab
        self.historical_tab = QWidget()
        historical_layout = QVBoxLayout(self.historical_tab)

        # Create embedded chart widgets for frequency and trend charts
        self.frequency_chart_widget = EmbeddedChartWidget()
        self.frequency_chart_widget.setMinimumHeight(300)
        historical_layout.addWidget(self.frequency_chart_widget)

        self.trend_chart_widget = EmbeddedChartWidget()
        self.trend_chart_widget.setMinimumHeight(300)
        historical_layout.addWidget(self.trend_chart_widget)

        self.analytics_tabs.addTab(self.historical_tab, "📊 Historical Data")

        # Prediction Performance Tab
        self.performance_tab = QWidget()
        performance_layout = QVBoxLayout(self.performance_tab)

        # Create embedded chart widgets for performance charts
        self.performance_chart_widget = EmbeddedChartWidget()
        self.performance_chart_widget.setMinimumHeight(300)
        performance_layout.addWidget(self.performance_chart_widget)

        self.strategy_chart_widget = EmbeddedChartWidget()
        self.strategy_chart_widget.setMinimumHeight(300)
        performance_layout.addWidget(self.strategy_chart_widget)

        self.analytics_tabs.addTab(self.performance_tab, "🎯 Prediction Performance")

        layout.addWidget(self.analytics_tabs)

        # Update charts on initial load
        QTimer.singleShot(500, self.update_analytics_charts)

        self.tab_widget.addTab(analytics_widget, "📈 Analytics")

    def create_predictions_tab(self):
        """Create enhanced predictions tab with strategy selection"""
        predictions_widget = QWidget()
        layout = QVBoxLayout(predictions_widget)

        # Game and Strategy Selection
        controls_layout = QHBoxLayout()

        # Game selector (existing)
        controls_layout.addWidget(QLabel("Game:"))
        controls_layout.addWidget(self.game_combo)

        # Strategy selector (enhanced with new strategies)
        controls_layout.addWidget(QLabel("Strategy:"))
        self.strategy_selector_combo = QComboBox()

        # Add strategies from the strategy selector
        strategies = self.strategy_selector.get_all_strategies()
        for strategy_key, strategy_name in strategies.items():
            self.strategy_selector_combo.addItem(strategy_name, strategy_key)

        # Add "Auto" option at the top
        self.strategy_selector_combo.insertItem(0, "Auto (Recommended)", "auto")
        self.strategy_selector_combo.setCurrentIndex(0)

        # Connect to handler
        self.strategy_selector_combo.currentIndexChanged.connect(self.on_prediction_strategy_changed)

        controls_layout.addWidget(self.strategy_selector_combo)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Prediction Display Area
        prediction_frame = QFrame()
        prediction_frame.setFrameStyle(QFrame.Box)
        prediction_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                padding: 20px;
                margin: 10px;
            }
        """)

        prediction_layout = QVBoxLayout(prediction_frame)

        # Confidence display
        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(QLabel("Confidence:"))

        self.confidence_stars = QLabel("⭐⭐⭐⭐⭐")
        self.confidence_stars.setStyleSheet("font-size: 18px; color: #ffc107;")
        confidence_layout.addWidget(self.confidence_stars)

        self.confidence_text = QLabel("Excellent (87%)")
        self.confidence_text.setStyleSheet("font-weight: bold; color: #28a745;")
        confidence_layout.addWidget(self.confidence_text)

        confidence_layout.addStretch()
        prediction_layout.addLayout(confidence_layout)

        # Numbers display
        self.numbers_layout = QHBoxLayout()
        self.number_labels = []

        for i in range(7):  # Max 7 numbers for Lotto Max
            label = QLabel("?")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("""
                QLabel {
                    background-color: #6c757d;
                    color: white;
                    border-radius: 25px;
                    font-size: 18px;
                    font-weight: bold;
                    min-width: 50px;
                    max-width: 50px;
                    min-height: 50px;
                    max-height: 50px;
                }
            """)
            self.number_labels.append(label)
            self.numbers_layout.addWidget(label)

        self.numbers_layout.addStretch()
        prediction_layout.addLayout(self.numbers_layout)

        # Strategy info
        self.strategy_info = QLabel("Select a strategy and click 'Generate Smart Pick' to begin!")
        self.strategy_info.setStyleSheet("color: #6c757d; font-style: italic; margin: 10px;")
        self.strategy_info.setWordWrap(True)
        prediction_layout.addWidget(self.strategy_info)

        layout.addWidget(prediction_frame)

        # Action buttons
        buttons_layout = QHBoxLayout()

        self.smart_pick_btn = QPushButton("🧠 Generate Smart Pick")
        self.smart_pick_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 12px 24px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.smart_pick_btn.clicked.connect(self.generate_prediction)
        buttons_layout.addWidget(self.smart_pick_btn)

        self.quick_pick_btn = QPushButton("🎲 Quick Pick")
        self.quick_pick_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 12px 24px;
                font-size: 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #1e7e34;
            }
        """)
        self.quick_pick_btn.clicked.connect(self.generate_quick_pick)
        buttons_layout.addWidget(self.quick_pick_btn)

        buttons_layout.addStretch()

        # Export buttons
        self.copy_btn = QPushButton("📋 Copy Numbers")
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self.copy_numbers_to_clipboard)
        buttons_layout.addWidget(self.copy_btn)

        self.save_btn = QPushButton("💾 Save Prediction")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_prediction_with_notes)
        buttons_layout.addWidget(self.save_btn)

        layout.addLayout(buttons_layout)

        # Performance display
        self.performance_label = QLabel("📈 Performance: Loading...")
        self.performance_label.setStyleSheet("margin: 10px; font-weight: bold;")
        layout.addWidget(self.performance_label)

        # Update performance on startup
        self.update_performance_display()

        self.tab_widget.addTab(predictions_widget, "🎯 Predictions")

    def create_strategy_dashboard_tab(self):
        """Create strategy dashboard tab"""
        # Create the strategy dashboard widget
        self.strategy_dashboard = StrategyDashboard(self)

        # Connect the strategy_selected signal to handle strategy selection
        self.strategy_dashboard.strategy_selected.connect(self.on_strategy_selected)

        # Add the dashboard to the tab widget
        self.tab_widget.addTab(self.strategy_dashboard, "🧠 Strategy Dashboard")

    def on_strategy_selected(self, strategy):
        """Handle strategy selection from the dashboard"""
        self.current_strategy = strategy
        strategy_name = self.strategy_selector.get_strategy_name(strategy)
        self.status_bar.showMessage(f"Selected strategy: {strategy_name}")

        # Update the strategy selector in the predictions tab if it exists
        if hasattr(self, 'strategy_selector_combo'):
            # Find the index of the strategy in the combo box
            for i in range(self.strategy_selector_combo.count()):
                if self.strategy_selector_combo.itemData(i) == strategy:
                    self.strategy_selector_combo.setCurrentIndex(i)
                    break

    def create_scraping_tab(self):
        """Create data scraping interface tab"""
        scraping_widget = QWidget()
        layout = QVBoxLayout(scraping_widget)

        # Title and description
        title_label = QLabel("🔄 Lottery Data Scraper")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title_label)

        desc_label = QLabel("Scrape lottery data from the WCLC website")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #666; margin-bottom: 20px;")
        layout.addWidget(desc_label)

        # Configuration options
        config_group = QGroupBox("⚙️ Scraper Configuration")
        config_layout = QGridLayout(config_group)

        # Game selection
        game_label = QLabel("Game:")
        self.scraper_game_combo = QComboBox()

        # Add all supported games with their display names
        for game_code in AppConfig.get_supported_games():
            display_name = AppConfig.get_game_display_name(game_code)
            self.scraper_game_combo.addItem(display_name, game_code)

        config_layout.addWidget(game_label, 0, 0)
        config_layout.addWidget(self.scraper_game_combo, 0, 1)

        # Batch mode
        self.batch_checkbox = QPushButton("Batch Mode (Historical Data)")
        self.batch_checkbox.setCheckable(True)
        self.batch_checkbox.setChecked(True)
        self.batch_checkbox.clicked.connect(self.toggle_batch_mode)
        config_layout.addWidget(self.batch_checkbox, 1, 0, 1, 2)

        # Months selection (only visible in batch mode)
        months_label = QLabel("Months to Scrape:")
        self.months_combo = QComboBox()
        self.months_combo.addItems(["1", "3", "6", "12", "All Available"])
        self.months_combo.setCurrentText("6")

        config_layout.addWidget(months_label, 2, 0)
        config_layout.addWidget(self.months_combo, 2, 1)

        # Output format
        format_label = QLabel("Output Format:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["CSV", "SQLite Database", "Both"])

        config_layout.addWidget(format_label, 3, 0)
        config_layout.addWidget(self.format_combo, 3, 1)

        layout.addWidget(config_group)

        # Progress section
        progress_group = QGroupBox("📊 Scraping Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.scraper_progress_bar = QProgressBar()
        self.scraper_progress_bar.setRange(0, 100)
        self.scraper_progress_bar.setValue(0)
        progress_layout.addWidget(self.scraper_progress_bar)

        self.scraper_status_label = QLabel("Ready to scrape")
        self.scraper_status_label.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self.scraper_status_label)

        layout.addWidget(progress_group)

        # Results section
        results_group = QGroupBox("📋 Results")
        results_layout = QVBoxLayout(results_group)

        self.scraper_results_text = QTextEdit()
        self.scraper_results_text.setReadOnly(True)
        self.scraper_results_text.setPlaceholderText("Scraping results will appear here...")
        results_layout.addWidget(self.scraper_results_text)

        layout.addWidget(results_group)

        # Action buttons
        buttons_layout = QHBoxLayout()

        self.start_scraper_btn = QPushButton("Start Scraping")
        self.start_scraper_btn.clicked.connect(self.run_scraper)
        buttons_layout.addWidget(self.start_scraper_btn)

        self.refresh_after_scrape_btn = QPushButton("Refresh Data After Scraping")
        self.refresh_after_scrape_btn.setCheckable(True)
        self.refresh_after_scrape_btn.setChecked(True)
        buttons_layout.addWidget(self.refresh_after_scrape_btn)

        layout.addLayout(buttons_layout)

        # Add the tab
        self.tab_widget.addTab(scraping_widget, "🔄 Data Scraper")

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
        # Convert display name to internal game code using centralized configuration
        from config import AppConfig

        # Find the game code that matches the display name
        self.current_game = "649"  # Default fallback
        for game_code in AppConfig.get_supported_games():
            if AppConfig.get_game_display_name(game_code) == game_text:
                self.current_game = game_code
                break
        self.status_bar.showMessage(f"Switched to {game_text}")

        # Update all displays
        self.update_dashboard()
        self.update_recent_draws_table()
        self.update_analytics_charts()

        # Update strategy dashboard if it exists
        if hasattr(self, 'strategy_dashboard'):
            self.strategy_dashboard.current_game = self.current_game
            self.strategy_dashboard.refresh_data()

    def on_prediction_strategy_changed(self, index):
        """Handle strategy selection change in the prediction tab"""
        # Get the strategy key from the combo box
        strategy = self.strategy_selector_combo.itemData(index)
        self.current_strategy = strategy

        # Get the strategy display name
        strategy_name = self.strategy_selector_combo.itemText(index)

        # Update status bar
        self.status_bar.showMessage(f"Selected strategy: {strategy_name}")

        # Update strategy info in the prediction tab
        if hasattr(self, 'strategy_info'):
            if strategy == 'auto':
                self.strategy_info.setText("Using automatic strategy selection based on historical performance")
            else:
                self.strategy_info.setText(f"Using {strategy_name} strategy")

        # Log the strategy change
        logger.info(f"Strategy changed to {strategy_name} ({strategy})")

    def update_data_status(self):
        """Update data status with detailed user feedback"""
        try:
            # Check 649 data
            data_649 = self.data_manager.load_game_data('649', full_refresh=False)
            count_649 = len(data_649) if not data_649.empty else 0

            if count_649 > 500:  # Good historical coverage
                self.data_649_status.setText(f"✅ Lotto 6/49: {count_649} draws loaded")
                self.data_649_status.setStyleSheet("color: green; font-weight: bold;")
            elif count_649 > 50:  # Some data but limited
                self.data_649_status.setText(f"⚠️ Lotto 6/49: {count_649} draws (limited data)")
                self.data_649_status.setStyleSheet("color: orange; font-weight: bold;")
            elif count_649 > 0:  # Very limited data
                self.data_649_status.setText(f"🔶 Lotto 6/49: {count_649} draws (very limited)")
                self.data_649_status.setStyleSheet("color: #FF6600; font-weight: bold;")
            else:
                self.data_649_status.setText("❌ Lotto 6/49: No data available")
                self.data_649_status.setStyleSheet("color: red; font-weight: bold;")

            # Check Max data  
            data_max = self.data_manager.load_game_data('max', full_refresh=False)
            count_max = len(data_max) if not data_max.empty else 0

            if count_max > 500:
                self.data_max_status.setText(f"✅ Lotto Max: {count_max} draws loaded")
                self.data_max_status.setStyleSheet("color: green; font-weight: bold;")
            elif count_max > 50:
                self.data_max_status.setText(f"⚠️ Lotto Max: {count_max} draws (limited data)")
                self.data_max_status.setStyleSheet("color: orange; font-weight: bold;")
            elif count_max > 0:
                self.data_max_status.setText(f"🔶 Lotto Max: {count_max} draws (very limited)")
                self.data_max_status.setStyleSheet("color: #FF6600; font-weight: bold;")
            else:
                self.data_max_status.setText("❌ Lotto Max: No data available")
                self.data_max_status.setStyleSheet("color: red; font-weight: bold;")

            # Add date range info if data exists
            if count_649 > 0 and not data_649.empty:
                try:
                    min_date = str(data_649['date'].min())
                    max_date = str(data_649['date'].max())
                    current_text = self.data_649_status.text()
                    self.data_649_status.setText(f"{current_text}\n({min_date} to {max_date})")
                except Exception:
                    pass  # Skip date range if there's an issue

            if count_max > 0 and not data_max.empty:
                try:
                    min_date = str(data_max['date'].min())
                    max_date = str(data_max['date'].max())
                    current_text = self.data_max_status.text()
                    self.data_max_status.setText(f"{current_text}\n({min_date} to {max_date})")
                except Exception:
                    pass

            # Update status bar with overall system status
            total_draws = count_649 + count_max
            if total_draws > 1000:
                self.status_bar.showMessage(f"✅ System Ready - {total_draws} total draws loaded", 5000)
            elif total_draws > 100:
                self.status_bar.showMessage(f"⚠️ Limited Data - {total_draws} total draws loaded", 5000)
            else:
                self.status_bar.showMessage(f"❌ Minimal Data - Only {total_draws} draws available", 10000)

        except Exception as e:
            self.logger.error(f"Error updating data status: {e}")
            self.data_649_status.setText("❌ Error loading 6/49 data")
            self.data_649_status.setStyleSheet("color: red;")
            self.data_max_status.setText("❌ Error loading Max data")
            self.data_max_status.setStyleSheet("color: red;")
            self.status_bar.showMessage(f"❌ System Error: {str(e)}", 10000)

    def update_draws_table(self):
        """Update the draws table with proper type handling"""
        try:
            current_game = self.get_current_game_code()
            draws = self.data_manager.load_game_data(current_game, full_refresh=False)

            # Convert to list of dicts if it's a DataFrame
            if hasattr(draws, 'to_dict'):
                draws = draws.to_dict('records')

            self.draws_table.setRowCount(len(draws))

            for row, draw in enumerate(draws):
                # CRITICAL: Ensure all values are strings with proper null handling

                # Handle date field safely
                date_value = draw.get('date', 'Unknown')
                if date_value is None or pd.isna(date_value) or str(date_value).lower() in ['nan', 'nat', 'none']:
                    date_str = 'Unknown'
                else:
                    date_str = str(date_value)

                # Handle numbers field safely
                numbers_value = draw.get('numbers', [])
                if isinstance(numbers_value, list):
                    # It's already a list - join with commas
                    numbers_str = ', '.join(str(num) for num in numbers_value if num is not None)
                elif isinstance(numbers_value, str):
                    # It's a string - clean it up and display
                    numbers_clean = numbers_value.strip('[]').replace("'", "").replace('"', '')
                    numbers_str = numbers_clean
                else:
                    # Fallback for any other type
                    numbers_str = str(numbers_value) if numbers_value is not None else ''

                # Handle bonus field safely
                bonus_value = draw.get('bonus', None)
                if bonus_value is None or pd.isna(bonus_value) or str(bonus_value).lower() in ['nan', 'none', '']:
                    bonus_str = ''
                else:
                    bonus_str = str(bonus_value)

                # Handle gold ball (649 specific)
                gold_ball_value = draw.get('gold_ball', None)
                if gold_ball_value is None or pd.isna(gold_ball_value) or str(gold_ball_value).lower() in ['nan', 'none', '']:
                    gold_ball_str = ''
                else:
                    gold_ball_str = str(gold_ball_value)

                # Create table items with guaranteed string values
                date_item = QTableWidgetItem(date_str)
                numbers_item = QTableWidgetItem(numbers_str)
                bonus_item = QTableWidgetItem(bonus_str)
                gold_ball_item = QTableWidgetItem(gold_ball_str)
                day_item = QTableWidgetItem('')  # Placeholder
                notes_item = QTableWidgetItem('')  # Placeholder

                # Set items in table
                self.draws_table.setItem(row, 0, date_item)
                self.draws_table.setItem(row, 1, numbers_item)
                self.draws_table.setItem(row, 2, bonus_item)
                self.draws_table.setItem(row, 3, gold_ball_item)
                self.draws_table.setItem(row, 4, day_item)
                self.draws_table.setItem(row, 5, notes_item)

            self.draws_table.resizeColumnsToContents()
            self.logger.info(f"Updated draws table with {len(draws)} records")

        except Exception as e:
            self.logger.error(f"Error updating draws table: {e}")
            # Show error in GUI instead of crashing
            self.draws_table.setRowCount(1)
            error_item = QTableWidgetItem(f"Error loading data: {str(e)}")
            error_item.setBackground(QColor(255, 200, 200))  # Light red background
            self.draws_table.setItem(0, 0, error_item)

            # Clear other columns
            for col in range(1, 6):
                self.draws_table.setItem(0, col, QTableWidgetItem(''))

    def update_recent_draws(self):
        """Update recent draws display with latest results"""
        try:
            # Fix: Use 'count' instead of 'days'
            recent_649 = self.data_manager.get_recent_draws('649', count=1)
            if recent_649:
                draw = recent_649[0]
                numbers = draw.get('numbers', [])
                date = draw.get('date', 'Unknown date')
                bonus = draw.get('bonus', '')

                numbers_str = ' '.join(f"[{n:02d}]" for n in numbers)
                bonus_str = f" + Bonus: {bonus}" if bonus else ""
                self.recent_649_display.setText(f"🎯 Lotto 6/49 - {date}\n{numbers_str}{bonus_str}")
            else:
                self.recent_649_display.setText("❌ No recent 6/49 draws available")

            # Fix: Same for Lotto Max
            recent_max = self.data_manager.get_recent_draws('max', count=1)
            if recent_max:
                draw = recent_max[0]
                numbers = draw.get('numbers', [])
                date = draw.get('date', 'Unknown date')

                numbers_str = ' '.join(f"[{n:02d}]" for n in numbers)
                self.recent_max_display.setText(f"🎯 Lotto Max - {date}\n{numbers_str}")
            else:
                self.recent_max_display.setText("❌ No recent Lotto Max draws available")

        except Exception as e:
            logger.error(f"Failed to update recent draws: {e}")
            import traceback
            traceback.print_exc()
            self.recent_649_display.setText("❌ Error loading recent draws")
            self.recent_max_display.setText("❌ Error loading recent draws")

    def get_game_display_name(self, game_code):
        """Get a user-friendly display name for a game code"""
        # Use the centralized configuration for consistency
        from config import AppConfig
        return AppConfig.get_game_display_name(game_code)

    def process_game_stats(self, game_code):
        """Process game statistics and return formatted data for display

        This separates data processing logic from UI display logic
        """
        try:
            # Get raw data from data manager
            summary = self.data_manager.get_game_summary(game_code)
            game_display_name = self.get_game_display_name(game_code)

            # Process hot/cold numbers
            hot_nums = "No data"
            cold_nums = "No data"

            if 'most_frequent_numbers' in summary and summary['most_frequent_numbers']:
                hot_nums = ", ".join(map(str, summary['most_frequent_numbers'][:6]))

            if 'least_frequent_numbers' in summary and summary['least_frequent_numbers']:
                cold_nums = ", ".join(map(str, summary['least_frequent_numbers'][:6]))

            # Format activity messages
            activity_messages = []
            activity_messages.append(f"📊 Statistics for {game_display_name}")
            activity_messages.append(f"📈 Based on all {summary['total_draws']:,} draws ({summary['date_range']})")

            if summary['total_draws'] > 0:
                activity_messages.append(f"🔥 Hot numbers for {game_display_name}: {hot_nums}")
                activity_messages.append(f"❄️ Cold numbers for {game_display_name}: {cold_nums}")
                activity_messages.append(f"📅 Draws in last 30 days: {summary.get('recent_draws', 0)}")
            else:
                activity_messages.append("⚠️ No data available for this game.")
                activity_messages.append("Try refreshing data or selecting a different game.")

            # Return processed data
            return {
                'game_display_name': game_display_name,
                'total_draws': summary['total_draws'],
                'date_range': summary['date_range'],
                'last_updated': summary['last_updated'],
                'hot_numbers': hot_nums,
                'cold_numbers': cold_nums,
                'activity_messages': activity_messages
            }

        except Exception as e:
            logger.error(f"Error processing game stats: {e}")
            return {
                'game_display_name': self.get_game_display_name(game_code),
                'total_draws': 0,
                'date_range': 'Error',
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'hot_numbers': 'No data',
                'cold_numbers': 'No data',
                'activity_messages': ["⚠️ Error loading data. Please try refreshing."]
            }

    def update_dashboard(self):
        """Update dashboard with current game statistics"""
        try:
            # Update data status first
            self.update_data_status()

            # Update recent draws
            self.update_recent_draws()

            # Get current game and process stats
            current_game = getattr(self, 'current_game', '649')
            stats = self.process_game_stats(current_game)

            # Debug output
            print(f"SUMMARY DEBUG for {current_game}:", stats)

            # Update Quick Stats box title to show which game
            self.stats_group.setTitle(f"🔥 Quick Stats for {stats['game_display_name']}")

            # Update basic stats
            self.total_draws_label.setText(f"Total Draws: {stats['total_draws']:,}")
            self.date_range_label.setText(f"Date Range: {stats['date_range']}")
            self.last_updated_label.setText(f"Last Updated: {stats['last_updated']}")

            # Hot/Cold numbers with fallbacks
            hot_numbers = stats.get('hot_numbers', '')
            cold_numbers = stats.get('cold_numbers', '')

            if hot_numbers and hot_numbers != 'No data':
                self.hot_numbers_label.setText(f"Hot: {hot_numbers}")
            else:
                self.hot_numbers_label.setText("Hot: (No data)")

            if cold_numbers and cold_numbers != 'No data':
                self.cold_numbers_label.setText(f"Cold: {cold_numbers}")
            else:
                self.cold_numbers_label.setText("Cold: (No data)")

            # Recent draws count
            recent_count = stats.get('recent_draws', 0)
            if 'recent_draws' in stats:
                self.recent_draws_label.setText(f"Recent: {recent_count}")

            # Update recent activity
            self.recent_activity_text.clear()
            for message in stats['activity_messages']:
                self.recent_activity_text.append(message)

        except Exception as e:
            logger.error(f"Error updating dashboard: {e}")
            self.status_bar.showMessage(f"Error loading data: {e}")

            # Set fallback values
            self.hot_numbers_label.setText("Hot: (Error)")
            self.cold_numbers_label.setText("Cold: (Error)")
            self.recent_activity_text.clear()
            self.recent_activity_text.append("⚠️ Error loading data. Please try refreshing.")

    def update_recent_draws_table(self):
        """Update the recent draws table (legacy method, now calls update_draws_table)"""
        # Set the combo box to the current game
        current_game = getattr(self, 'current_game', '649')

        # Find the index of the current game in the combo box
        for i in range(self.draws_game_combo.count()):
            if self.draws_game_combo.itemData(i) == current_game:
                self.draws_game_combo.setCurrentIndex(i)
                break

        # Call the new method
        self.update_draws_table()

    def refresh_data(self, full_refresh=False):
        """
        Refresh data from files and/or scraping

        Args:
            full_refresh: If True, refresh all data; if False, only refresh recent data
        """
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.status_bar.showMessage("Refreshing data...")

        try:
            if full_refresh:
                # Full refresh of all data (slower but comprehensive)
                self.status_bar.showMessage("Performing full data refresh (this may take a while)...")
                self.data_manager.refresh_all_data()
                self.status_bar.showMessage("Full data refresh completed successfully")
            else:
                # Smart refresh - only get recent data (faster)
                self.status_bar.showMessage("Performing smart refresh of recent data...")
                game = self.get_current_game_code()

                # Use the new refresh_recent_data_only method
                self.data_manager.refresh_recent_data_only(game)
                self.status_bar.showMessage("Smart refresh completed successfully")

            # Update all displays
            self.update_dashboard()
            self.update_recent_draws_table()
            self.update_analytics_charts()

            # Update strategy dashboard if it exists
            if hasattr(self, 'strategy_dashboard'):
                self.strategy_dashboard.refresh_data()

        except Exception as e:
            logger.error(f"Error refreshing data: {e}")
            self.status_bar.showMessage(f"Error refreshing data: {e}")
        finally:
            self.progress_bar.setVisible(False)

    def toggle_batch_mode(self, checked):
        """Toggle visibility of batch mode options"""
        # Show/hide months selection based on batch mode
        self.months_combo.setEnabled(checked)

    def run_scraper(self):
        """Run the scraper in a background thread"""
        # Get configuration from UI
        game_index = self.scraper_game_combo.currentIndex()
        game_code = self.scraper_game_combo.itemData(game_index)
        game_name = self.scraper_game_combo.currentText()

        batch_mode = self.batch_checkbox.isChecked()

        # Get months to scrape (if in batch mode)
        max_months = None
        if batch_mode:
            months_text = self.months_combo.currentText()
            if months_text != "All Available":
                max_months = int(months_text)

        # Get output format
        format_text = self.format_combo.currentText()
        if format_text == "CSV":
            output_format = "csv"
        elif format_text == "SQLite Database":
            output_format = "sqlite"
        else:  # Both
            output_format = "both"

        # Disable UI elements during scraping
        self.start_scraper_btn.setEnabled(False)
        self.scraper_game_combo.setEnabled(False)
        self.batch_checkbox.setEnabled(False)
        self.months_combo.setEnabled(False)
        self.format_combo.setEnabled(False)

        # Reset progress and status
        self.scraper_progress_bar.setValue(0)
        self.scraper_status_label.setText("Starting scraper...")
        self.scraper_results_text.clear()
        self.scraper_results_text.append(f"Starting scraper for {game_name}...")
        if batch_mode:
            months_desc = f"{max_months} months" if max_months else "all available months"
            self.scraper_results_text.append(f"Batch mode enabled, scraping {months_desc}")
        else:
            self.scraper_results_text.append("Scraping current month only")
        self.scraper_results_text.append(f"Output format: {format_text}")
        self.scraper_results_text.append("-----------------------------------")

        # Create and run worker thread
        worker = ScraperWorker(game_code, batch_mode, max_months, output_format)

        # Connect signals
        worker.signals.started.connect(self.on_scraper_started)
        worker.signals.progress.connect(self.on_scraper_progress)
        worker.signals.finished.connect(self.on_scraper_finished)
        worker.signals.error.connect(self.on_scraper_error)

        # Start the worker thread
        self.thread_pool.start(worker)

    def on_scraper_started(self):
        """Handle scraper started signal"""
        self.status_bar.showMessage("Scraper started")

    def on_scraper_progress(self, value, message):
        """Handle scraper progress signal"""
        self.scraper_progress_bar.setValue(value)
        self.scraper_status_label.setText(message)
        self.scraper_results_text.append(message)

    def on_scraper_finished(self, success, message):
        """Handle scraper finished signal"""
        # Re-enable UI elements
        self.start_scraper_btn.setEnabled(True)
        self.scraper_game_combo.setEnabled(True)
        self.batch_checkbox.setEnabled(True)
        self.months_combo.setEnabled(self.batch_checkbox.isChecked())
        self.format_combo.setEnabled(True)

        # Update status
        if success:
            self.scraper_status_label.setText("Scraping completed successfully")
            self.scraper_results_text.append("-----------------------------------")
            self.scraper_results_text.append("✅ " + message)
            self.status_bar.showMessage("Scraping completed successfully")

            # Refresh data if requested
            if self.refresh_after_scrape_btn.isChecked():
                self.scraper_results_text.append("Refreshing data...")
                self.refresh_data()
                self.scraper_results_text.append("Data refreshed successfully")
        else:
            self.scraper_status_label.setText("Scraping failed")
            self.scraper_results_text.append("-----------------------------------")
            self.scraper_results_text.append("❌ " + message)
            self.status_bar.showMessage("Scraping failed: " + message)

    def on_scraper_error(self, error_message):
        """Handle scraper error signal"""
        self.scraper_results_text.append(f"Error: {error_message}")

    def update_analytics_charts(self):
        """Update all analytics charts with current data"""
        try:
            game_text = self.analytics_game_selector.currentText()
            game = "649" if "6/49" in game_text else "max"

            # Update insights summary
            self.update_analytics_insights(game)

            # Update historical charts
            self.update_historical_charts(game)

            # Update prediction performance charts  
            self.update_performance_charts(game)

        except Exception as e:
            logger.error(f"Failed to update analytics charts: {e}")

    def update_analytics_insights(self, game: str):
        """Update the insights summary bar"""
        try:
            # Get basic game summary
            summary = self.data_manager.get_game_summary(game)

            # Update prediction performance first
            self.update_prediction_performance()

            # Build insights text
            insights = f"📊 ANALYTICS INSIGHTS - {game.upper()}\n\n"

            # Basic stats
            insights += f"📈 DATA OVERVIEW:\n"
            insights += f"• Total Draws: {summary.get('total_draws', 0):,}\n"
            insights += f"• Date Range: {summary.get('date_range', 'Unknown')}\n"
            insights += f"• Last Updated: {summary.get('last_updated', 'Never')}\n\n"

            # Hot/Cold analysis
            hot_numbers = summary.get('most_frequent_numbers', [])
            cold_numbers = summary.get('least_frequent_numbers', [])

            if hot_numbers:
                insights += f"🔥 HOT NUMBERS (Most Frequent):\n"
                insights += f"• {', '.join(map(str, hot_numbers[:6]))}\n\n"

            if cold_numbers:
                insights += f"🧊 COLD NUMBERS (Least Frequent):\n" 
                insights += f"• {', '.join(map(str, cold_numbers[:6]))}\n\n"

            # Set the insights text (prediction performance will be added by update_prediction_performance)
            if hasattr(self, 'analytics_insights_text'):
                self.analytics_insights_text.setPlainText(insights)

        except Exception as e:
            logger.error(f"Failed to update analytics insights: {e}")

    def update_historical_charts(self, game: str):
        """Update historical charts with bulletproof embedded display"""
        try:
            logger.info(f"Updating historical charts for {game}")

            # Get analytics instance
            analytics = get_analytics_engine()

            # Update frequency chart
            try:
                frequency_fig = analytics.plot_number_frequency(game)
                self.frequency_chart_widget.display_figure(frequency_fig)

                # CRITICAL: Close the figure to prevent memory leaks and popup windows
                plt.close(frequency_fig)

            except Exception as e:
                logger.error(f"Failed to create frequency chart: {e}")
                self.frequency_chart_widget.display_error(f"Frequency Chart Error: {e}")

            # Update trend chart
            try:
                trend_fig = analytics.plot_trend_analysis(game)
                self.trend_chart_widget.display_figure(trend_fig)

                # CRITICAL: Close the figure to prevent memory leaks and popup windows
                plt.close(trend_fig)

            except Exception as e:
                logger.error(f"Failed to create trend chart: {e}")
                self.trend_chart_widget.display_error(f"Trend Chart Error: {e}")

            logger.info("Historical charts updated successfully")

        except Exception as e:
            logger.error(f"Failed to update historical charts: {e}")
            # Show error in both widgets
            error_msg = f"Chart Update Error: {e}"
            if hasattr(self, 'frequency_chart_widget'):
                self.frequency_chart_widget.display_error(error_msg)
            if hasattr(self, 'trend_chart_widget'):
                self.trend_chart_widget.display_error(error_msg)

    def update_performance_charts(self, game: str):
        """Update prediction performance charts with embedded display"""
        try:
            logger.info(f"Updating performance charts for {game}")

            # Get analytics instance
            analytics = get_analytics_engine()

            # Update prediction performance chart
            try:
                performance_fig = analytics.plot_prediction_performance(game)
                self.performance_chart_widget.display_figure(performance_fig)

                # CRITICAL: Close the figure to prevent memory leaks and popup windows
                plt.close(performance_fig)

            except Exception as e:
                logger.error(f"Failed to create performance chart: {e}")
                self.performance_chart_widget.display_error(f"Performance Chart Error: {e}")

            # Update strategy comparison chart
            try:
                strategy_fig = analytics.plot_strategy_comparison()
                self.strategy_chart_widget.display_figure(strategy_fig)

                # CRITICAL: Close the figure to prevent memory leaks and popup windows
                plt.close(strategy_fig)

            except Exception as e:
                logger.error(f"Failed to create strategy chart: {e}")
                self.strategy_chart_widget.display_error(f"Strategy Chart Error: {e}")

            logger.info("Performance charts updated successfully")

        except Exception as e:
            logger.error(f"Failed to update performance charts: {e}")
            # Show error in both widgets
            error_msg = f"Chart Update Error: {e}"
            if hasattr(self, 'performance_chart_widget'):
                self.performance_chart_widget.display_error(error_msg)
            if hasattr(self, 'strategy_chart_widget'):
                self.strategy_chart_widget.display_error(error_msg)

    def export_analytics_data(self):
        """Export analytics data to CSV"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            from tracking.prediction_logger import PredictionLogger

            filename, _ = QFileDialog.getSaveFileName(
                self, 
                "Export Analytics Data", 
                f"analytics_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "CSV Files (*.csv)"
            )

            if filename:
                logger_instance = PredictionLogger()
                success = logger_instance.export_predictions_csv(filename)

                if success:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.information(self, "Export Complete", f"Analytics data exported to:\n{filename}")
                else:
                    QMessageBox.warning(self, "Export Failed", "Failed to export analytics data")

        except Exception as e:
            logger.error(f"Failed to export analytics: {e}")

    def generate_prediction(self):
        """Generate smart prediction using selected strategy"""
        try:
            # Get current selections
            game = self.get_current_game_code()

            # Use the current_strategy attribute (set by strategy selector)
            strategy = self.current_strategy

            # Show loading state
            self.smart_pick_btn.setText("🔄 Generating...")
            self.smart_pick_btn.setEnabled(False)

            if strategy == 'auto':
                self.strategy_info.setText("Analyzing patterns and selecting the best strategy...")
            else:
                strategy_name = self.strategy_selector.get_strategy_name(strategy)
                self.strategy_info.setText(f"Generating prediction using {strategy_name} strategy...")

            # Start prediction in worker thread
            self.prediction_worker = PredictionWorker(self.predictor, game, strategy)
            self.prediction_worker.prediction_ready.connect(self.on_prediction_ready)
            self.prediction_worker.error_occurred.connect(self.on_prediction_error)
            self.prediction_worker.start()

        except Exception as e:
            self.on_prediction_error(str(e))

    def on_prediction_ready(self, prediction):
        """Handle prediction result and log it"""
        try:
            self.current_prediction = prediction

            # Update numbers display
            numbers = prediction.get('predicted_numbers', [])
            game = prediction.get('game', self.get_current_game_code())

            # Hide extra number labels for 6/49
            show_count = len(numbers)
            for i, label in enumerate(self.number_labels):
                if i < show_count:
                    label.setText(str(numbers[i]))
                    label.setStyleSheet("""
                        QLabel {
                            background-color: #007bff;
                            color: white;
                            border-radius: 25px;
                            font-size: 18px;
                            font-weight: bold;
                            min-width: 50px;
                            max-width: 50px;
                            min-height: 50px;
                            max-height: 50px;
                        }
                    """)
                    label.show()
                else:
                    label.hide()

            # Update confidence display
            confidence_level = prediction.get('confidence', 'medium')

            # Map confidence level to stars
            stars_map = {'high': 5, 'medium': 3, 'low': 1}
            stars_count = stars_map.get(confidence_level, 3)
            stars = "⭐" * stars_count
            self.confidence_stars.setText(stars)

            # Get confidence percentage from metadata if available
            metadata = prediction.get('metadata', {})
            confidence_pct = metadata.get('strategy_backtest_score', 0.5) * 100
            confidence_label = self.get_confidence_label(confidence_pct / 100)
            self.confidence_text.setText(f"{confidence_label} ({confidence_pct:.0f}%)")

            # Update strategy info
            strategy_name = prediction.get('strategy_display_name', 'Unknown')
            data_count = metadata.get('total_draws_analyzed', 0)
            explanation = prediction.get('explanation', '')

            self.strategy_info.setText(
                f"Strategy: {strategy_name} | Based on {data_count} historical draws | "
                f"Generated at {datetime.now().strftime('%H:%M:%S')}\n"
                f"{explanation}"
            )

            # Enable action buttons
            self.copy_btn.setEnabled(True)
            self.save_btn.setEnabled(True)

            # LOG THE PREDICTION for tracking
            game = self.get_current_game_code()
            strategy = prediction.get('strategy', 'unknown')
            timestamp = self.prediction_logger.log_prediction(strategy, game, numbers)

            # Add to activity log
            self.add_activity_message(
                f"📊 Prediction logged: {strategy} strategy → {numbers} (ID: {timestamp[-8:]})"
            )

            # Update performance display
            self.update_performance_display()

            # Update prediction performance
            self.update_prediction_performance()

            # Update strategy dashboard if it exists
            if hasattr(self, 'strategy_dashboard'):
                self.strategy_dashboard.refresh_data()

        except Exception as e:
            self.on_prediction_error(f"Failed to display prediction: {e}")
        finally:
            # Reset button state
            self.smart_pick_btn.setText("🧠 Generate Smart Pick")
            self.smart_pick_btn.setEnabled(True)

    def on_prediction_error(self, error_msg):
        """Handle prediction generation error"""
        self.strategy_info.setText(f"❌ Error: {error_msg}")
        self.smart_pick_btn.setText("🧠 Generate Smart Pick")
        self.smart_pick_btn.setEnabled(True)

        # Show error dialog
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.warning(self, "Prediction Error", f"Failed to generate prediction:\n{error_msg}")

    def generate_quick_pick(self):
        """Generate random quick pick"""
        game = self.get_current_game_code()
        self.prediction_worker = PredictionWorker(self.predictor, game, "random")
        self.prediction_worker.prediction_ready.connect(self.on_prediction_ready)
        self.prediction_worker.error_occurred.connect(self.on_prediction_error)
        self.prediction_worker.start()

    def get_current_game_code(self):
        """Convert GUI game selection to internal game code"""
        game_text = self.game_combo.currentText()
        if "6/49" in game_text:
            return "649"
        elif "Max" in game_text:
            return "max"
        else:
            return "649"  # default

    def get_confidence_label(self, confidence):
        """Convert confidence score to human-readable label"""
        if confidence >= 0.8:
            return "Excellent"
        elif confidence >= 0.6:
            return "Good"
        elif confidence >= 0.4:
            return "Fair"
        elif confidence >= 0.2:
            return "Low"
        else:
            return "Minimal"

    def copy_numbers_to_clipboard(self):
        """Copy current prediction numbers to clipboard"""
        if self.current_prediction:
            numbers = self.current_prediction['numbers']
            numbers_text = " - ".join(map(str, numbers))

            from PyQt5.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(numbers_text)

            # Show feedback
            self.strategy_info.setText(f"📋 Numbers copied to clipboard: {numbers_text}")

    def save_prediction_with_notes(self):
        """Save prediction with optional user notes"""
        if not self.current_prediction:
            return

        from PyQt5.QtWidgets import QInputDialog

        notes, ok = QInputDialog.getText(
            self, 
            "Save Prediction", 
            "Add notes (optional):",
            text=f"Smart pick for {self.current_prediction['game'].upper()}"
        )

        if ok:
            # Get prediction details
            game = self.current_prediction.get('game', self.get_current_game_code())
            strategy = self.current_prediction.get('strategy', 'unknown')
            numbers = self.current_prediction.get('predicted_numbers', [])

            # Log with new method signature
            timestamp = self.prediction_logger.log_prediction(strategy, game, numbers)

            # Add to activity log with notes
            self.add_activity_message(
                f"💾 Prediction saved: {strategy} for {game} - {numbers} - Notes: {notes}"
            )

            self.strategy_info.setText("💾 Prediction saved with notes!")

    def update_prediction_performance(self):
        """Update prediction performance display in analytics tab"""
        try:
            # First, evaluate any pending predictions
            self.prediction_logger.evaluate_predictions(self.data_manager)

            # Get performance data
            game = self.get_current_game_code()
            recent_predictions = self.prediction_logger.get_recent_predictions(game, days=30)
            performance_summary = self.prediction_logger.get_performance_summary()

            # Update analytics insights to include prediction performance
            if hasattr(self, 'analytics_insights_text'):
                insights_text = self.analytics_insights_text.toPlainText()

                # Add prediction performance section
                perf_text = f"\n\n🎯 PREDICTION PERFORMANCE:\n"
                perf_text += f"• Total Predictions: {performance_summary['total_predictions']}\n"
                perf_text += f"• Evaluated: {performance_summary['evaluated_predictions']}\n"
                perf_text += f"• Wins: {performance_summary['total_wins']}\n"
                perf_text += f"• Win Rate: {performance_summary['overall_win_rate']:.1f}%\n"

                if performance_summary['best_strategy']:
                    best = performance_summary['best_strategy']
                    perf_text += f"• Best Strategy: {best['name']} ({best['win_rate']:.1f}% win rate)\n"

                # Show recent predictions
                if recent_predictions:
                    perf_text += f"\n📋 RECENT PREDICTIONS ({len(recent_predictions)} last 30 days):\n"
                    for i, pred in enumerate(recent_predictions[:5]):  # Show last 5
                        status = "✅ WIN" if pred.get('did_win') else "❌ MISS"
                        matches = pred.get('match_count', 0) if pred.get('evaluated') else "Pending"
                        date = pred['timestamp'][:10]
                        perf_text += f"• {date}: {pred['predicted_numbers']} - {status} ({matches} matches)\n"

                # Update the insights text
                if "🎯 PREDICTION PERFORMANCE:" in insights_text:
                    # Replace existing performance section
                    parts = insights_text.split("🎯 PREDICTION PERFORMANCE:")
                    insights_text = parts[0] + perf_text
                else:
                    # Add new performance section
                    insights_text += perf_text

                self.analytics_insights_text.setPlainText(insights_text)

        except Exception as e:
            logger.error(f"Error updating prediction performance: {e}")

    def add_activity_message(self, message):
        """Add a message to the recent activity log"""
        try:
            if hasattr(self, 'recent_activity_text'):
                # Add timestamp to message
                timestamp = datetime.now().strftime("%H:%M:%S")
                formatted_message = f"[{timestamp}] {message}"

                # Add to activity log
                self.recent_activity_text.append(formatted_message)

                # Scroll to bottom to show latest message
                self.recent_activity_text.verticalScrollBar().setValue(
                    self.recent_activity_text.verticalScrollBar().maximum()
                )

                # Also log to application log
                logger.info(f"Activity: {message}")
        except Exception as e:
            logger.error(f"Failed to add activity message: {e}")

    def update_performance_display(self):
        """Update the performance display with recent statistics"""
        try:
            performance = self.prediction_logger.get_strategy_performance(days=30)

            if performance:
                total_predictions = sum(p['total_predictions'] for p in performance.values())
                total_wins = sum(p['wins'] for p in performance.values())

                if total_predictions > 0:
                    overall_win_rate = (total_wins / total_predictions) * 100
                    self.performance_label.setText(
                        f"📈 Last 30 days: {total_predictions} predictions, "
                        f"{total_wins} wins ({overall_win_rate:.1f}% win rate)"
                    )
                else:
                    self.performance_label.setText("📈 No recent predictions to analyze")
            else:
                self.performance_label.setText("📈 Performance tracking will begin after first prediction")

        except Exception as e:
            logger.error(f"Failed to update performance display: {e}")
            self.performance_label.setText("📈 Performance: Unable to load")


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
