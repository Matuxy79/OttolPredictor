=================================
Saskatoon Lotto Predictor
=================================

A comprehensive lottery prediction system for Saskatchewan lottery games, featuring data scraping, statistical analysis, and machine learning-based predictions.

System Architecture
------------------

The Saskatoon Lotto Predictor is built on a three-layer architecture:

1. **Presentation Layer**: User interfaces for interacting with the system
2. **Business Logic Layer**: Core functionality and algorithms
3. **Data Access Layer**: Data storage and external API interactions

Component Inventory
------------------

Presentation Layer
~~~~~~~~~~~~~~~~~

**GUI Module** (``gui/``)
    * ``main_window.py``: Primary PyQt5 interface with dashboard, recent draws, analytics, and prediction tabs
    * ``__init__.py``: Package initialization

**CLI Interface**
    * ``main.py``: Command-line entry point with ArgumentParser for batch operations

Business Logic Layer
~~~~~~~~~~~~~~~~~~~

**Data Manager** (``data_manager.py``)
    * ``LotteryDataManager`` class: Unified data access API
    * Data validation, caching, and format conversion
    * Implements Repository pattern for data access abstraction

**Analytics Engine** (``analytics.py``)
    * Statistical analysis of lottery data
    * Pattern recognition algorithms
    * Frequency analysis and trend detection

**Prediction Engine** (``predictor.py``)
    * ML-based prediction algorithms
    * Strategy patterns for different prediction approaches
    * Confidence scoring for predictions

**Scraping Engine** (``wclc_scraper.py``)
    * ``WCLCScraper`` class: Robust web scraping for lottery data
    * Multi-game support (649, Max, Western 649, Western Max, Daily Grand)
    * Batch processing for historical data
    * Error handling and retry logic

Data Access Layer
~~~~~~~~~~~~~~~~

**Configuration** (``config.py``)
    * ``AppConfig`` class: Centralized configuration management
    * Game configurations, directories, scraping settings
    * Environment variable support

**Schema** (``schema.py``)
    * ``DrawRecord`` class: Standardized lottery draw record
    * ``DataValidator`` class: Data integrity validation
    * Type definitions and conversions

**Logging** (``logging_config.py``)
    * Centralized logging configuration
    * File and console handlers
    * Consistent logging across all modules

Testing Framework
~~~~~~~~~~~~~~~~

**Scraper Tests** (``test_wclc_scraper.py``)
    * Unit tests for WCLC scraper functionality
    * Live scraping tests for all supported games
    * Validation tests for draw data

**GUI Tests** (``test_gui.py``)
    * Tests for GUI functionality
    * Event handling and display verification

Pipeline Stages
--------------

1. **Data Acquisition**

   * Web scraping from WCLC websites
   * Batch processing of historical data
   * Data validation and cleaning

2. **Data Processing**

   * Storage in CSV or SQLite formats
   * Caching for performance optimization
   * Format standardization

3. **Analysis**

   * Statistical analysis of draw patterns
   * Frequency analysis of numbers
   * Trend detection and visualization

4. **Prediction**

   * Algorithm selection based on strategy
   * Confidence scoring of predictions
   * Multiple prediction set generation

5. **Presentation**

   * Dashboard with summary statistics
   * Recent draws visualization
   * Interactive prediction interface

Advanced Features
---------------

* **Multi-game Support**: Handles multiple lottery game formats
* **Batch Historical Scraping**: Retrieves and processes complete historical datasets
* **Smart Predictions**: Data-driven prediction algorithms with confidence scoring
* **Adaptive Rate Limiting**: Intelligent throttling for respectful web scraping
* **Centralized Configuration**: Single source of truth for all application settings
* **Standardized Logging**: Consistent logging across all modules
* **Data Validation**: Robust validation of all lottery data
* **Caching Layer**: Performance optimization for data access

Installation
-----------

1. Clone this repository::

    git clone https://github.com/Matuxy79/OttolPredictor.git
    cd OttolPredictor

2. Create and activate a virtual environment (recommended)::

    python -m venv .venv
    .venv\Scripts\activate  # On Windows

3. Install the required dependencies::

    pip install -r requirements.txt

4. Verify your installation::

    python verify_install.py

Usage
-----

GUI Mode
~~~~~~~~

To launch the graphical user interface::

    python main.py

CLI Mode
~~~~~~~~

For command-line batch operations::

    python wclc_scraper.py --game <game_type> [options]

Examples:

1. Scrape current month only::

    python wclc_scraper.py --game 649 --output results.csv

2. Scrape all available history::

    python wclc_scraper.py --game 649 --batch --output complete_649_history.csv

3. Scrape last 6 months::

    python wclc_scraper.py --game max --batch --max-months 6 --format both

For more options, run::

    python wclc_scraper.py --help
