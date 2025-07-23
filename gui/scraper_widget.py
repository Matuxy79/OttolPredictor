"""
GUI component for managing WCLC lottery data and manual entry
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton, QLineEdit, QComboBox, QDateEdit,
                           QSpinBox, QMessageBox, QFormLayout, QGroupBox)
from PyQt5.QtCore import QDate, Qt
import os
from datetime import datetime
from typing import List, Dict
import pandas as pd

from wclc_scraper import WCLCScraper
from config import AppConfig
from logging_config import get_logger

logger = get_logger(__name__)

class WCLCDataEntryWidget(QWidget):
    """Widget for manual lottery data entry and management"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scraper = WCLCScraper()
        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout()

        # Game selection
        game_group = QGroupBox("Game Selection")
        game_layout = QHBoxLayout()
        self.game_combo = QComboBox()
        self.game_combo.addItems(AppConfig.get_supported_games())
        game_layout.addWidget(QLabel("Game:"))
        game_layout.addWidget(self.game_combo)
        game_group.setLayout(game_layout)
        layout.addWidget(game_group)

        # Date selection
        date_group = QGroupBox("Draw Date")
        date_layout = QHBoxLayout()
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        date_layout.addWidget(QLabel("Draw Date:"))
        date_layout.addWidget(self.date_edit)
        date_group.setLayout(date_layout)
        layout.addWidget(date_group)

        # Numbers entry
        numbers_group = QGroupBox("Winning Numbers")
        numbers_layout = QFormLayout()

        # Main numbers
        self.number_inputs: List[QSpinBox] = []
        numbers_row = QHBoxLayout()
        for i in range(7):  # Max 7 numbers (for Lotto Max)
            spin = QSpinBox()
            spin.setRange(1, 49)
            spin.setButtonSymbols(QSpinBox.NoButtons)
            self.number_inputs.append(spin)
            numbers_row.addWidget(spin)

        numbers_layout.addRow("Numbers:", numbers_row)

        # Bonus number
        self.bonus_spin = QSpinBox()
        self.bonus_spin.setRange(1, 49)
        self.bonus_spin.setButtonSymbols(QSpinBox.NoButtons)
        numbers_layout.addRow("Bonus:", self.bonus_spin)

        # Gold ball number (for Lotto 649)
        self.gold_ball_edit = QLineEdit()
        self.gold_ball_edit.setPlaceholderText("Optional - for 649 only")
        numbers_layout.addRow("Gold Ball:", self.gold_ball_edit)

        numbers_group.setLayout(numbers_layout)
        layout.addWidget(numbers_group)

        # Action buttons
        buttons_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Draw")
        self.add_button.clicked.connect(self.add_draw)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_form)
        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.clear_button)
        layout.addLayout(buttons_layout)

        # File management
        file_group = QGroupBox("Data File Management")
        file_layout = QVBoxLayout()

        # Show current data file
        self.file_label = QLabel()
        self.update_file_label()
        file_layout.addWidget(self.file_label)

        # Data file actions
        file_buttons = QHBoxLayout()
        self.load_button = QPushButton("Load Data")
        self.load_button.clicked.connect(self.load_data)
        self.verify_button = QPushButton("Verify Data")
        self.verify_button.clicked.connect(self.verify_data)
        file_buttons.addWidget(self.load_button)
        file_buttons.addWidget(self.verify_button)
        file_layout.addLayout(file_buttons)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        self.setLayout(layout)

        # Connect game selection to UI updates
        self.game_combo.currentTextChanged.connect(self.on_game_changed)
        self.on_game_changed(self.game_combo.currentText())

    def on_game_changed(self, game: str):
        """Update UI based on selected game"""
        # Update number of visible number inputs
        max_numbers = 7 if game == 'max' else 6
        for i, spin in enumerate(self.number_inputs):
            spin.setVisible(i < max_numbers)

        # Show/hide gold ball for 649
        self.gold_ball_edit.setVisible(game == '649')

        # Update file label
        self.update_file_label()

    def update_file_label(self):
        """Update the label showing current data file"""
        game = self.game_combo.currentText()
        file_path = self.get_data_file_path(game)
        if os.path.exists(file_path):
            self.file_label.setText(f"Data file: {os.path.basename(file_path)}")
        else:
            self.file_label.setText("No data file exists yet")

    def get_data_file_path(self, game: str) -> str:
        """Get the path to the data file for a game"""
        return os.path.join("data", "processed", f"wclc_{game}_data.csv")

    def add_draw(self):
        """Add a new draw to the data file"""
        try:
            game = self.game_combo.currentText()
            draw_date = self.date_edit.date().toPyDate()

            # Collect numbers
            max_nums = 7 if game == 'max' else 6
            numbers = [spin.value() for spin in self.number_inputs[:max_nums]]

            # Validate numbers are unique and non-zero
            if len(set(numbers)) != len(numbers) or 0 in numbers:
                QMessageBox.warning(self, "Invalid Numbers",
                                 "All numbers must be unique and non-zero")
                return

            draw_data = {
                'game': game,
                'date': draw_date.strftime('%Y-%m-%d'),
                'numbers': numbers,
                'bonus': self.bonus_spin.value(),
                'gold_ball': self.gold_ball_edit.text() if game == '649' else None,
                'scraped_at': datetime.now().isoformat(),
                'source_block_index': 0
            }

            # Validate data
            if not self.scraper._validate_draw_data(draw_data, game):
                QMessageBox.warning(self, "Validation Error",
                                 "The draw data is invalid. Please check the numbers.")
                return

            # Save to file
            file_path = self.get_data_file_path(game)
            df = pd.DataFrame([draw_data])

            if os.path.exists(file_path):
                # Append to existing file
                existing_df = pd.read_csv(file_path)
                df = pd.concat([existing_df, df], ignore_index=True)

            # Save and sort by date
            df.sort_values('date', ascending=False, inplace=True)
            df.to_csv(file_path, index=False)

            # --- NEW: Trigger prediction evaluation and analytics refresh ---
            try:
                from tracking.prediction_logger import PredictionLogger
                from core.data_manager import get_data_manager
                # Re-evaluate predictions
                prediction_logger = PredictionLogger()
                data_manager = get_data_manager()
                prediction_logger.evaluate_predictions(data_manager)
                # Optionally, show closest prediction for this draw
                recent_preds = prediction_logger.get_recent_predictions(game=game, days=7)
                closest = None
                best_match = -1
                for pred in recent_preds:
                    if pred.get('evaluated') and pred.get('match_count', 0) > best_match and pred.get('timestamp')[:10] <= draw_data['date']:
                        best_match = pred['match_count']
                        closest = pred
                if closest:
                    QMessageBox.information(self, "Closest Prediction",
                        f"Closest prediction for {draw_data['date']} ({game}):\n"
                        f"Numbers: {closest['predicted_numbers']}\n"
                        f"Matches: {closest['match_count']}\n"
                        f"Win: {'Yes' if closest['did_win'] else 'No'}")
            except Exception as eval_err:
                logger.error(f"Error evaluating predictions after draw entry: {eval_err}")

            QMessageBox.information(self, "Success",
                                 f"Added draw for {draw_date} to {game} data")
            self.clear_form()

        except Exception as e:
            logger.error(f"Error adding draw: {e}")
            QMessageBox.critical(self, "Error",
                              f"Failed to add draw: {str(e)}")

    def clear_form(self):
        """Clear all form inputs"""
        for spin in self.number_inputs:
            spin.setValue(0)
        self.bonus_spin.setValue(0)
        self.gold_ball_edit.clear()

    def load_data(self):
        """Load and display current data file"""
        game = self.game_combo.currentText()
        file_path = self.get_data_file_path(game)

        try:
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                # TODO: Add data display dialog/widget
                QMessageBox.information(self, "Data Loaded",
                                     f"Loaded {len(df)} draws for {game}")
            else:
                QMessageBox.warning(self, "No Data",
                                 f"No data file exists for {game}")

        except Exception as e:
            logger.error(f"Error loading data: {e}")
            QMessageBox.critical(self, "Error",
                              f"Failed to load data: {str(e)}")

    def verify_data(self):
        """Verify data file integrity"""
        game = self.game_combo.currentText()
        file_path = self.get_data_file_path(game)

        try:
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "No Data",
                                 f"No data file exists for {game}")
                return

            df = pd.read_csv(file_path)
            invalid_count = 0

            for _, row in df.iterrows():
                draw_data = row.to_dict()
                if not self.scraper._validate_draw_data(draw_data, game):
                    invalid_count += 1

            if invalid_count == 0:
                QMessageBox.information(self, "Verification Success",
                                     f"All {len(df)} draws are valid")
            else:
                QMessageBox.warning(self, "Verification Failed",
                                 f"Found {invalid_count} invalid draws")

        except Exception as e:
            logger.error(f"Error verifying data: {e}")
            QMessageBox.critical(self, "Error",
                              f"Failed to verify data: {str(e)}")
