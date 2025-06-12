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
* **Pure Python Statistics**: Statistical functions implemented in pure Python with no external dependencies
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

.. note::
   Python 3.11 and higher (including 3.13) is fully supported. The code now uses a pure Python
   implementation of statistical functions with no external dependencies, ensuring consistent
   behavior across all Python versions.

Option 1: Using pip (Standard Python)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Create and activate a virtual environment with Python 3.11 or higher::

    py -3.13 -m venv .venv  # For Python 3.13
    # OR
    py -3.12 -m venv .venv  # For Python 3.12
    # OR
    py -3.11 -m venv .venv  # For Python 3.11
    .venv\Scripts\activate  # On Windows

2. Install the required dependencies::

    pip install -r requirements.txt

3. Verify your installation::

    python verify_install.py

Option 2: Using Conda (Alternative installation method)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Install Miniconda or Anaconda if you haven't already

2. Create and activate the conda environment::

    conda env create -f environment.yml
    conda activate ottolpredictor

3. Verify your installation::

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

    python main.py --game <game_type> --batch [options]

Supported Games:
- 649: Lotto 6/49
- max: Lotto Max
- western649: Western 649
- westernmax: Western Max
- dailygrand: Daily Grand

Examples:

1. Scrape Lotto 6/49 data for the last month and save to CSV::

    python main.py --game 649 --batch --max-months 1 --format csv

2. Scrape Lotto Max data for the last 3 months and save to CSV::

    python main.py --game max --batch --max-months 3 --format csv

3. Scrape Western 649 complete history and save to CSV::

    python main.py --game western649 --batch --format csv

4. Scrape Western Max data for the last 6 months and save to both CSV and SQLite::

    python main.py --game westernmax --batch --max-months 6 --format both

5. Scrape Daily Grand data and save to SQLite::

    python main.py --game dailygrand --batch --format sqlite

Key Parameters:
- --batch: Enable batch scraping of historical data
- --max-months: Maximum number of months to scrape (default: all available)
- --format: Output format (csv, sqlite, or both)
- --output: Custom output filename (default: auto-generated)

For more options, run::

    python main.py --help
