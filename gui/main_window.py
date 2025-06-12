"""
Main GUI Window for Saskatoon Lotto Predictor
Sister-friendly lottery prediction interface
"""

import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QTabWidget, QLabel, QPushButton, QTableWidget,
                            QTableWidgetItem, QComboBox, QTextEdit, QGroupBox,
                            QGridLayout, QProgressBar, QStatusBar, QSplitter,
                            QScrollArea, QFrame, QMessageBox, QInputDialog)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QRunnable, QThreadPool, QObject
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor
from datetime import datetime

# For matplotlib integration
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_manager import get_data_manager
from logging_config import get_logger
from analytics import get_analytics_engine
from wclc_scraper import WCLCScraper
from config import AppConfig
from predictor import SmartPredictor
from tracking.prediction_logger import PredictionLogger
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
            prediction = self.predictor.generate_prediction(self.game, self.strategy)
            self.prediction_ready.emit(prediction)
        except Exception as e:
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

        # Initialize prediction components
        self.data_manager = get_data_manager()
        self.analytics_engine = get_analytics_engine()
        self.predictor = SmartPredictor(self.data_manager)
        self.prediction_logger = PredictionLogger()
        self.current_prediction = None

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
        self.refresh_btn = QPushButton("🔄 Refresh Data")
        self.refresh_btn.clicked.connect(self.refresh_data)

        self.quick_pick_btn = QPushButton("🎲 Quick Pick")
        self.quick_pick_btn.clicked.connect(self.generate_quick_pick)

        self.smart_pick_btn = QPushButton("🧠 Smart Pick")
        self.smart_pick_btn.clicked.connect(self.generate_prediction)

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

        # Scraping tab
        self.create_scraping_tab()

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

        self.frequency_chart_label = QLabel("Loading number frequency chart...")
        self.frequency_chart_label.setAlignment(Qt.AlignCenter)
        self.frequency_chart_label.setMinimumHeight(300)
        historical_layout.addWidget(self.frequency_chart_label)

        self.trend_chart_label = QLabel("Loading trend analysis chart...")
        self.trend_chart_label.setAlignment(Qt.AlignCenter)
        self.trend_chart_label.setMinimumHeight(300)
        historical_layout.addWidget(self.trend_chart_label)

        self.analytics_tabs.addTab(self.historical_tab, "📊 Historical Data")

        # Prediction Performance Tab
        self.performance_tab = QWidget()
        performance_layout = QVBoxLayout(self.performance_tab)

        self.performance_chart_label = QLabel("Loading prediction performance chart...")
        self.performance_chart_label.setAlignment(Qt.AlignCenter)
        self.performance_chart_label.setMinimumHeight(300)
        performance_layout.addWidget(self.performance_chart_label)

        self.strategy_chart_label = QLabel("Loading strategy comparison chart...")
        self.strategy_chart_label.setAlignment(Qt.AlignCenter)
        self.strategy_chart_label.setMinimumHeight(300)
        performance_layout.addWidget(self.strategy_chart_label)

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

        # Strategy selector (new)
        controls_layout.addWidget(QLabel("Strategy:"))
        self.strategy_selector = QComboBox()
        self.strategy_selector.addItems([
            "Balanced (Recommended)",
            "Hot & Cold Numbers", 
            "Historical Frequency",
            "Random Baseline"
        ])
        self.strategy_selector.setCurrentText("Balanced (Recommended)")
        controls_layout.addWidget(self.strategy_selector)

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

    def update_dashboard(self):
        """Update dashboard with current game data"""
        try:
            current_game = getattr(self, 'current_game', '649')
            summary = self.data_manager.get_game_summary(current_game)

            # Update summary labels
            self.total_draws_label.setText(f"Total Draws: {summary['total_draws']:,}")
            self.date_range_label.setText(f"Date Range: {summary['date_range']}")
            self.last_updated_label.setText(f"Last Updated: {summary['last_updated']}")

            # Update hot/cold numbers with safe access
            hot_nums = "No data"
            cold_nums = "No data"

            if 'most_frequent_numbers' in summary and summary['most_frequent_numbers']:
                hot_nums = ", ".join(map(str, summary['most_frequent_numbers'][:6]))

            if 'least_frequent_numbers' in summary and summary['least_frequent_numbers']:
                cold_nums = ", ".join(map(str, summary['least_frequent_numbers'][:6]))

            self.hot_numbers_label.setText(hot_nums)
            self.cold_numbers_label.setText(cold_nums)

            # Update recent activity
            self.recent_activity_text.clear()
            self.recent_activity_text.append(f"📊 Loaded {summary['total_draws']} draws for {current_game.upper()}")

            if summary['total_draws'] > 0:
                self.recent_activity_text.append(f"🔥 Hot numbers: {hot_nums}")
                self.recent_activity_text.append(f"❄️ Cold numbers: {cold_nums}")
                self.recent_activity_text.append(f"📅 Recent draws (30 days): {summary.get('recent_draws', 0)}")
            else:
                self.recent_activity_text.append("⚠️ No data available for this game.")
                self.recent_activity_text.append("Try refreshing data or selecting a different game.")

        except Exception as e:
            logger.error(f"Error updating dashboard: {e}")
            self.status_bar.showMessage(f"Error loading data: {e}")

            # Set default values in case of error
            self.hot_numbers_label.setText("No data")
            self.cold_numbers_label.setText("No data")
            self.recent_activity_text.clear()
            self.recent_activity_text.append("⚠️ Error loading data. Please try refreshing.")

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
            self.update_analytics_charts()
            self.status_bar.showMessage("Data refreshed successfully")
        except Exception as e:
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
            insights = self.analytics_engine.get_prediction_insights(game)

            self.total_predictions_label.setText(
                f"📈 Total Predictions: {insights.get('total_predictions', 0)}"
            )

            best_strategy = insights.get('best_strategy')
            if best_strategy:
                self.best_strategy_label.setText(
                    f"🏆 Best Strategy: {best_strategy['name'].title()} "
                    f"({best_strategy['win_rate']:.1f}% win rate)"
                )
            else:
                self.best_strategy_label.setText("🏆 Best Strategy: No data yet")

            win_rate = insights.get('overall_win_rate', 0)
            self.win_rate_label.setText(f"🎯 Overall Win Rate: {win_rate:.1f}%")

        except Exception as e:
            logger.error(f"Failed to update insights: {e}")

    def update_historical_charts(self, game: str):
        """Update historical data analysis charts"""
        try:
            import io
            import base64
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            import matplotlib.pyplot as plt

            # Generate frequency chart
            plt.figure(figsize=(10, 6))
            self.analytics_engine.plot_number_frequency(game)

            # Convert to image for display
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)

            pixmap = QPixmap()
            pixmap.loadFromData(buf.getvalue())

            self.frequency_chart_label.setPixmap(
                pixmap.scaled(800, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            self.frequency_chart_label.setText("")

            plt.close()
            buf.close()

            # Generate trend chart
            plt.figure(figsize=(10, 6))
            self.analytics_engine.plot_trend_analysis(game)

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)

            pixmap = QPixmap()
            pixmap.loadFromData(buf.getvalue())

            self.trend_chart_label.setPixmap(
                pixmap.scaled(800, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            self.trend_chart_label.setText("")

            plt.close()
            buf.close()

        except Exception as e:
            logger.error(f"Failed to update historical charts: {e}")
            self.frequency_chart_label.setText(f"Error loading charts: {e}")

    def update_performance_charts(self, game: str):
        """Update prediction performance charts"""
        try:
            import io
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            import matplotlib.pyplot as plt

            # Generate prediction performance chart
            plt.figure(figsize=(10, 6))
            self.analytics_engine.plot_prediction_performance(game)

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)

            pixmap = QPixmap()
            pixmap.loadFromData(buf.getvalue())

            if not pixmap.isNull():
                self.performance_chart_label.setPixmap(
                    pixmap.scaled(800, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                self.performance_chart_label.setText("")
            else:
                self.performance_chart_label.setText("No prediction performance data available yet")

            plt.close()
            buf.close()

            # Generate strategy comparison chart
            plt.figure(figsize=(12, 4))
            self.analytics_engine.plot_strategy_comparison()

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)

            pixmap = QPixmap()
            pixmap.loadFromData(buf.getvalue())

            if not pixmap.isNull():
                self.strategy_chart_label.setPixmap(
                    pixmap.scaled(900, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                self.strategy_chart_label.setText("")
            else:
                self.strategy_chart_label.setText("No strategy comparison data available yet")

            plt.close()
            buf.close()

        except Exception as e:
            logger.error(f"Failed to update performance charts: {e}")
            self.performance_chart_label.setText("No prediction data available - make some predictions first!")

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
            strategy_text = self.strategy_selector.currentText()
            strategy_map = {
                "Balanced (Recommended)": "balanced",
                "Hot & Cold Numbers": "hot_cold", 
                "Historical Frequency": "frequency",
                "Random Baseline": "random"
            }
            strategy = strategy_map.get(strategy_text, "balanced")

            # Show loading state
            self.smart_pick_btn.setText("🔄 Generating...")
            self.smart_pick_btn.setEnabled(False)
            self.strategy_info.setText("Analyzing patterns and generating your smart pick...")

            # Start prediction in worker thread
            self.prediction_worker = PredictionWorker(self.predictor, game, strategy)
            self.prediction_worker.prediction_ready.connect(self.on_prediction_ready)
            self.prediction_worker.error_occurred.connect(self.on_prediction_error)
            self.prediction_worker.start()

        except Exception as e:
            self.on_prediction_error(str(e))

    def on_prediction_ready(self, prediction):
        """Handle successful prediction generation"""
        try:
            self.current_prediction = prediction

            # Update numbers display
            numbers = prediction['numbers']
            game = prediction['game']

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
            stars = "⭐" * prediction['confidence_stars']
            self.confidence_stars.setText(stars)

            confidence_pct = prediction['confidence'] * 100
            confidence_label = self.get_confidence_label(prediction['confidence'])
            self.confidence_text.setText(f"{confidence_label} ({confidence_pct:.0f}%)")

            # Update strategy info
            strategy_name = prediction['strategy_name']
            data_count = prediction.get('data_draws_count', 0)
            self.strategy_info.setText(
                f"Strategy: {strategy_name} | Based on {data_count} historical draws | "
                f"Generated at {datetime.now().strftime('%H:%M:%S')}"
            )

            # Enable action buttons
            self.copy_btn.setEnabled(True)
            self.save_btn.setEnabled(True)

            # Log prediction
            self.prediction_logger.log_prediction(prediction)

            # Update performance display
            self.update_performance_display()

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
            self.prediction_logger.log_prediction(self.current_prediction, notes)
            self.strategy_info.setText("💾 Prediction saved with notes!")

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
