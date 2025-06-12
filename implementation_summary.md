# Implementation Summary: GUI Analytics Component and Data Scraping

## Overview

This document summarizes the changes made to implement the requirements specified in the issue:

> update gui component for analytics to represent data,
> scrape 6 months of data for 649 and max

## Changes Made

### 1. Enhanced Analytics Visualization

The GUI analytics component has been updated to display meaningful visualizations of lottery data:

- **Number Frequency Analysis**: A bar chart showing the frequency of each number in the lottery game's history, with the most frequent numbers highlighted.
- **Draw Trend Analysis**: A line chart showing how the sum of drawn numbers changes over time, with a moving average line to help identify trends.

### 2. Updated Files

The following files were modified or created:

- **analytics.py**: Implemented visualization methods:
  - `plot_number_frequency()`: Creates a bar chart of number frequencies
  - `plot_trend_analysis()`: Creates a line chart of number sum trends over time

- **gui/main_window.py**: Updated the GUI to display visualizations:
  - Enhanced `create_analytics_tab()` to create a layout for charts
  - Added `update_analytics_charts()` to generate and display charts
  - Updated event handlers to refresh charts when game selection changes

- **scrape_6_months.py**: Created a new script to scrape 6 months of data for Lotto 649 and Lotto Max

### 3. Data Scraping Functionality

The existing `scrape_batch_history()` method in `wclc_scraper.py` already supported scraping a specified number of months. We leveraged this functionality to create a dedicated script for scraping 6 months of data for the required games.

## How to Test

1. **Run the Data Scraping Script**:
   ```
   python scrape_6_months.py
   ```
   This will scrape 6 months of data for Lotto 649 and Lotto Max and save it to CSV files.

2. **Launch the GUI Application**:
   ```
   python main.py
   ```

3. **View the Analytics Tab**:
   - Select different games from the dropdown to see their analytics visualizations
   - The charts will update automatically when you change the selected game

## Dependencies

The implementation requires the following Python packages:
- matplotlib (for creating visualizations)
- pandas (for data manipulation)
- PyQt5 (for the GUI)
- requests (for web scraping)
- BeautifulSoup (for HTML parsing)

## Notes

- The analytics visualizations are generated on-demand when the user switches games or refreshes data.
- The charts are embedded directly in the PyQt5 interface using matplotlib's Qt backend.
- Error handling is implemented to gracefully handle cases where data is missing or visualization fails.