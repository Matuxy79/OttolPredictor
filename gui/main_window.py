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
                            QScrollArea)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QRunnable, QThreadPool, QObject
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor

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

logger = get_logger(__name__)

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
        self.data_manager = get_data_manager()
        self.analytics_engine = get_analytics_engine()
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
        """Create analytics and charts tab"""
        analytics_widget = QWidget()
        layout = QVBoxLayout(analytics_widget)

        # Create a scroll area for the charts
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # Add title
        title_label = QLabel("📈 Lottery Data Analytics")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        scroll_layout.addWidget(title_label)

        # Add description
        desc_label = QLabel("Visual analysis of lottery draw patterns and trends")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #666; margin-bottom: 20px;")
        scroll_layout.addWidget(desc_label)

        # Create containers for charts
        self.freq_chart_container = QWidget()
        self.freq_chart_layout = QVBoxLayout(self.freq_chart_container)
        self.freq_chart_label = QLabel("Number Frequency Analysis")
        self.freq_chart_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.freq_chart_layout.addWidget(self.freq_chart_label)

        self.trend_chart_container = QWidget()
        self.trend_chart_layout = QVBoxLayout(self.trend_chart_container)
        self.trend_chart_label = QLabel("Draw Trend Analysis")
        self.trend_chart_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.trend_chart_layout.addWidget(self.trend_chart_label)

        # Add chart containers to scroll layout
        scroll_layout.addWidget(self.freq_chart_container)
        scroll_layout.addWidget(self.trend_chart_container)

        # Add some spacing
        scroll_layout.addSpacing(20)

        # Add a note about data
        note_label = QLabel("Note: Charts update automatically when you change the selected game")
        note_label.setStyleSheet("color: #666; font-style: italic;")
        note_label.setAlignment(Qt.AlignCenter)
        scroll_layout.addWidget(note_label)

        # Add stretch to push everything to the top
        scroll_layout.addStretch()

        # Set the scroll content
        scroll_area.setWidget(scroll_content)

        # Add scroll area to main layout
        layout.addWidget(scroll_area)

        self.tab_widget.addTab(analytics_widget, "📈 Analytics")

        # Initialize charts
        self.update_analytics_charts()

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
        """Update analytics charts with current game data"""
        try:
            current_game = getattr(self, 'current_game', '649')

            # Clear existing charts
            for i in reversed(range(self.freq_chart_layout.count())):
                if i > 0:  # Keep the label
                    widget = self.freq_chart_layout.itemAt(i).widget()
                    if widget:
                        widget.setParent(None)

            for i in reversed(range(self.trend_chart_layout.count())):
                if i > 0:  # Keep the label
                    widget = self.trend_chart_layout.itemAt(i).widget()
                    if widget:
                        widget.setParent(None)

            # Create frequency chart
            try:
                freq_fig = self.analytics_engine.plot_number_frequency(current_game)
                freq_canvas = FigureCanvas(freq_fig)
                freq_canvas.setMinimumHeight(400)
                self.freq_chart_layout.addWidget(freq_canvas)
            except Exception as e:
                logger.error(f"Error creating frequency chart: {e}")
                error_label = QLabel(f"Error creating frequency chart: {str(e)}")
                error_label.setStyleSheet("color: red;")
                self.freq_chart_layout.addWidget(error_label)

            # Create trend chart
            try:
                trend_fig = self.analytics_engine.plot_trend_analysis(current_game)
                trend_canvas = FigureCanvas(trend_fig)
                trend_canvas.setMinimumHeight(400)
                self.trend_chart_layout.addWidget(trend_canvas)
            except Exception as e:
                logger.error(f"Error creating trend chart: {e}")
                error_label = QLabel(f"Error creating trend chart: {str(e)}")
                error_label.setStyleSheet("color: red;")
                self.trend_chart_layout.addWidget(error_label)

            # Add a note about the data
            summary = self.data_manager.get_game_summary(current_game)
            data_note = QLabel(f"Analysis based on {summary['total_draws']} draws from {summary['date_range']}")
            data_note.setStyleSheet("color: #666; font-style: italic;")
            data_note.setAlignment(Qt.AlignCenter)
            self.trend_chart_layout.addWidget(data_note)

        except Exception as e:
            logger.error(f"Error updating analytics charts: {e}")
            self.status_bar.showMessage(f"Error updating charts: {e}")

    def generate_quick_pick(self):
        """Generate random number picks"""
        import random
        from config import AppConfig

        current_game = getattr(self, 'current_game', '649')
        num_sets = int(self.sets_combo.currentText())

        # Get game configuration from centralized AppConfig
        game_config = AppConfig.get_game_config(current_game)

        # Create config dictionary for the algorithm
        config = {
            'count': game_config.number_count,
            'max': game_config.number_max,
            'bonus_max': game_config.bonus_max or game_config.number_max
        }

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
            # Check if we have data for this game
            game_data = self.data_manager.load_game_data(current_game)

            if game_data.empty:
                self.predictions_text.clear()
                self.predictions_text.append(f"❌ No data available for {current_game.upper()}.")
                self.predictions_text.append("Please try refreshing data or selecting a different game.")
                self.predictions_text.append("")
                self.predictions_text.append("💡 Tip: You can use Quick Pick for random selections.")
                self.status_bar.showMessage(f"No data available for {current_game}")
                return

            # Get frequency data
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

            # Provide fallback message
            self.predictions_text.clear()
            self.predictions_text.append("⚠️ Error generating smart predictions.")
            self.predictions_text.append("Please try Quick Pick instead or select a different game.")

    def _generate_smart_predictions(self, frequency_data, strategy, game):
        """Generate smart predictions based on frequency data"""
        import random
        from config import AppConfig

        # Get sorted numbers by frequency
        sorted_numbers = sorted(frequency_data.items(), key=lambda x: x[1], reverse=True)

        # Get game configuration from centralized AppConfig
        game_config = AppConfig.get_game_config(game)

        # Create config dictionary for the algorithm
        config = {
            'count': game_config.number_count,
            'max': game_config.number_max
        }
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
