"""
Centralized logging configuration for Saskatoon Lotto Predictor
"""

import logging
import os
from datetime import datetime
from config import AppConfig

def setup_logging(level=logging.INFO):
    """Setup application-wide logging"""
    
    # Ensure log directory exists
    os.makedirs(AppConfig.LOG_DIR, exist_ok=True)
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    
    # Setup file handler
    log_file = os.path.join(AppConfig.LOG_DIR, f"lotto_predictor_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(level)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger

def get_logger(name):
    """Get a logger for a specific module"""
    return logging.getLogger(name)