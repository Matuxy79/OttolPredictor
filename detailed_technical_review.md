# Saskatoon Lotto Predictor - Technical Review and Specifications

## Executive Summary

This document provides a comprehensive technical review of the Saskatoon Lotto Predictor application, a user-friendly tool designed to help users analyze lottery data and generate predictions for various lottery games. The application features a modular architecture with clear separation of concerns, including a GUI interface, data management capabilities, analytics tools, and prediction algorithms.

Key features include:
- User-friendly GUI with tabbed interface
- Support for multiple lottery games (649, Max, Western649, WesternMax, DailyGrand)
- Data-driven predictions with multiple strategies
- Statistical analysis of lottery data
- Flexible data management with CSV and SQLite support
- Optional data scraping capabilities

## Project Overview

The Saskatoon Lotto Predictor is a comprehensive Python application designed to help users analyze lottery data and generate predictions. It supports multiple lottery games from the Western Canada Lottery Corporation (WCLC) and provides both random and data-driven prediction strategies.

The project uses PyQt5 for the GUI, pandas for data manipulation, and includes optional data scraping capabilities using BeautifulSoup and requests. It follows a modular architecture with clear separation of concerns, making it easy to maintain and extend.

## System Architecture

The application follows a modular architecture with clear separation of concerns:

```
Saskatoon Lotto Predictor
│
├── main.py                 # Main entry point
├── data_manager.py         # Data access and management
├── analytics.py            # Statistical analysis
├── predictor.py            # Prediction algorithms
├── wclc_scraper.py         # Data scraping functionality
│
└── gui/                    # GUI components
    ├── __init__.py
    └── main_window.py      # Main application window
```

### Component Interactions

The application components interact as follows:

1. **main.py** - Entry point that initializes and launches the GUI
2. **GUI (gui/main_window.py)** - Provides the user interface and coordinates interactions between components
3. **Data Manager (data_manager.py)** - Manages data access, loading, and caching
4. **Analytics (analytics.py)** - Performs statistical analysis on lottery data
5. **Predictor (predictor.py)** - Generates predictions based on analytics and user preferences
6. **WCLC Scraper (wclc_scraper.py)** - Optional tool for scraping lottery data from the Western Canada Lottery Corporation website

## Component Details

### Main Entry Point (main.py)

The main.py file serves as the application entry point. It:
- Configures logging
- Imports and initializes the GUI
- Handles any startup errors gracefully

```python
def main():
    """Main application entry point"""
    logger.info("Starting Saskatoon Lotto Predictor")

    # Import the GUI module
    try:
        from gui.main_window import main as launch_gui
        logger.info("Successfully imported GUI module")
    except ImportError as e:
        logger.error(f"Failed to import GUI module: {e}")
        print(f"Error: Failed to import GUI module: {e}")
        return 1

    # Launch the GUI
    try:
        logger.info("Launching GUI...")
        launch_gui()
        return 0
    except Exception as e:
        logger.error(f"Error launching GUI: {e}")
        print(f"Error: Failed to launch GUI: {e}")
        return 1
```

### Data Manager (data_manager.py)

The LotteryDataManager class provides a centralized interface for data access:
- Supports multiple lottery games (649, Max, Western649, WesternMax, DailyGrand)
- Loads data from CSV files or SQLite databases
- Implements caching for performance optimization
- Provides data cleaning and standardization
- Offers summary statistics and frequency analysis

Key methods include:
- `load_game_data`: Loads data for a specific game
- `get_game_summary`: Provides summary statistics for a game
- `get_number_frequency`: Analyzes frequency of numbers
- `get_recent_draws`: Retrieves recent draw data

### Analytics Module (analytics.py)

The LotteryAnalytics class provides statistical analysis:
- Number frequency analysis
- Pair analysis (numbers that appear together)
- Pattern detection (odd/even distribution, high/low distribution)
- Visualization capabilities (placeholder for future implementation)

Key methods include:
- `analyze_number_frequency`: Analyzes frequency of each number
- `get_number_pairs`: Finds frequently occurring number pairs
- `analyze_draw_patterns`: Analyzes patterns in draws
- `plot_number_frequency`: Visualizes number frequency (placeholder)

### Predictor Module (predictor.py)

The LotteryPredictor class implements prediction algorithms:
- Quick Pick (random number generation)
- Smart Pick (data-driven predictions based on frequency analysis)
- Multiple prediction strategies (balanced, hot numbers, cold numbers)
- Confidence scoring for predictions

Key methods include:
- `quick_pick`: Generates random number picks
- `smart_pick`: Generates data-driven number picks
- `advanced_prediction`: Placeholder for future advanced algorithms

### GUI Module (gui/main_window.py)

The SaskatoonLottoPredictor class implements the main application window:
- Tab-based interface (Dashboard, Recent Draws, Analytics, Predictions)
- Game selection and configuration
- Data visualization and display
- User-friendly controls for generating predictions

Key methods include:
- `init_ui`: Sets up the user interface
- `create_dashboard_tab`: Creates the dashboard overview tab
- `create_recent_draws_tab`: Creates the recent draws table tab
- `create_analytics_tab`: Creates the analytics and charts tab
- `create_predictions_tab`: Creates the predictions interface tab
- `generate_quick_pick`: Generates random number picks
- `generate_smart_pick`: Generates data-driven number picks

### WCLC Scraper (wclc_scraper.py)

The WCLCScraper class provides data acquisition capabilities:
- Scrapes lottery data from the WCLC website
- Supports batch historical data collection
- Implements robust error handling and retry logic
- Validates and cleans scraped data
- Exports data to CSV or SQLite formats

Key methods include:
- `scrape_batch_history`: Scrapes historical data by following month navigation links
- `parse_lotto649`, `parse_lottomax`, etc.: Game-specific parsing methods
- `save_to_csv`, `save_to_sqlite`: Output handlers

## Data Flow

1. Data is loaded from CSV files or databases by the Data Manager
2. The GUI requests data from the Data Manager to display to the user
3. When the user requests analytics, the Analytics module processes data from the Data Manager
4. When the user requests predictions, the Predictor module uses data from both the Data Manager and Analytics module
5. Results are displayed to the user through the GUI

## Deployment Instructions

### Prerequisites

- Python 3.7 or higher
- Required packages (listed in requirements.txt):
  - PyQt5 (GUI framework)
  - pandas (data manipulation)
  - numpy (numerical operations)
  - matplotlib (visualization)
  - beautifulsoup4 and requests (for data scraping)

### Installation

1. Clone or download the repository
2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```

### Running the Application

1. Launch the application from the main entry point:
   ```
   python main.py
   ```

2. The GUI will load and display the Dashboard tab
3. Select a lottery game from the dropdown menu
4. Use the tabs to navigate between different features:
   - Dashboard: Overview and summary statistics
   - Recent Draws: Table of recent lottery results
   - Analytics: Statistical analysis and visualizations
   - Predictions: Generate and view predictions

### Data Acquisition

There are two ways to acquire lottery data:

1. **Manual Data Files**: Place CSV files containing lottery draw data in the project directory or a 'data' subdirectory. Files should contain columns for game, date, and numbers at minimum.

2. **WCLC Scraper**: Use the included scraper to download data:
   ```
   python wclc_scraper.py --game 649 --batch --output 649_results.csv
   ```

## Performance Considerations

The application includes several performance optimizations:
- **Data caching**: The Data Manager implements caching to avoid repeated file I/O
- **Lazy loading**: Components are loaded only when needed
- **Efficient data structures**: Pandas DataFrames are used for efficient data manipulation
- **Background processing**: Long-running operations can be moved to background threads

## Security Considerations

The application includes several security considerations:
- **Input validation**: User inputs are validated to prevent errors
- **Error handling**: Comprehensive error handling to prevent crashes
- **Data validation**: Lottery data is validated for consistency
- **Respectful scraping**: The scraper includes delays and proper headers

## Future Enhancements

Potential future enhancements include:
- **Enhanced Analytics**: Implement more advanced statistical analysis and pattern detection
- **Visualization**: Add interactive charts and graphs for data visualization
- **Machine Learning**: Incorporate machine learning models for improved predictions
- **Database Integration**: Add support for cloud databases and real-time updates
- **Mobile App**: Develop a companion mobile application

## Conclusion

The Saskatoon Lotto Predictor provides a comprehensive solution for lottery analysis and prediction. Its modular architecture ensures maintainability and extensibility, while the user-friendly GUI makes it accessible to users without technical expertise. The application combines data management, statistical analysis, and prediction algorithms to provide a valuable tool for lottery enthusiasts.
