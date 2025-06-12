# Scraper GUI Component Implementation

## Overview

This document summarizes the implementation of the scraper GUI component for the Saskatoon Lotto Predictor application. The component allows users to scrape lottery data directly from the application interface, without having to run separate scripts.

## Features

The scraper GUI component provides the following features:

1. **Game Selection**: Users can select which lottery game to scrape data for.
2. **Batch Mode**: Users can choose to scrape historical data in batch mode, or just the current month.
3. **Months Selection**: When batch mode is enabled, users can specify how many months of data to scrape.
4. **Output Format**: Users can choose to save the scraped data as CSV, SQLite database, or both.
5. **Progress Tracking**: The component provides a progress bar and status messages to keep users informed about the scraping process.
6. **Results Display**: The component displays the results of the scraping operation, including any errors that may occur.
7. **Automatic Data Refresh**: Users can choose to automatically refresh the application's data after scraping is complete.

## Implementation Details

The scraper GUI component is implemented as a new tab in the main application window. The implementation consists of:

1. **UI Elements**: The tab includes various UI elements for configuring and running the scraper, such as combo boxes, checkboxes, buttons, a progress bar, and a text area for displaying results.

2. **Worker Thread**: The scraper runs in a background thread to prevent the UI from freezing during the scraping process. This is implemented using Qt's QRunnable and QThreadPool classes.

3. **Signal Handling**: The worker thread communicates with the UI through signals, which are used to update the progress bar, status messages, and results display.

4. **Integration with Existing Code**: The component integrates with the existing scraper code in wclc_scraper.py, using the same methods and classes that are used by the command-line interface.

## How to Use

To use the scraper GUI component:

1. Open the Saskatoon Lotto Predictor application.
2. Click on the "Data Scraper" tab.
3. Configure the scraper:
   - Select the game to scrape data for.
   - Enable or disable batch mode.
   - If batch mode is enabled, select how many months of data to scrape.
   - Choose the output format.
4. Click the "Start Scraping" button to begin the scraping process.
5. Monitor the progress and results in the progress bar and results text area.
6. When scraping is complete, the data will be automatically refreshed if the "Refresh Data After Scraping" option is checked.

## Benefits

The scraper GUI component provides several benefits:

1. **Ease of Use**: Users can scrape data directly from the application interface, without having to run separate scripts or use the command line.
2. **Visual Feedback**: The component provides visual feedback about the scraping process, making it easier to monitor and troubleshoot.
3. **Integration**: The scraped data can be automatically integrated into the application, allowing users to immediately analyze and visualize it.
4. **Configurability**: Users can easily configure the scraper to meet their specific needs, without having to remember command-line arguments or edit configuration files.

## Future Enhancements

Possible future enhancements to the scraper GUI component include:

1. **Scheduled Scraping**: Allow users to schedule scraping operations to run automatically at specified intervals.
2. **Custom URL Support**: Allow users to specify custom URLs to scrape data from.
3. **Advanced Configuration**: Provide more advanced configuration options, such as retry settings, timeout settings, and proxy settings.
4. **Export/Import Configuration**: Allow users to save and load scraper configurations.