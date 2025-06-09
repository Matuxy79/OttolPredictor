# Saskatchewan Lotto Scraper - Technical Review Document

## Executive Summary

This document provides a comprehensive technical review of the Saskatchewan Lotto Scraper project, which has been enhanced to support multiple lottery games from the Western Canada Lottery Corporation (WCLC). The project now includes robust error handling, batch historical scraping, and comprehensive testing capabilities.

The key enhancements include:
- Integration with actual WCLC URLs for all supported lottery games
- Support for additional game types (Western Max and Daily Grand)
- Improved month link extraction for historical data scraping
- Enhanced data validation for different game types
- Comprehensive testing framework with both unit and live scraping tests

## Project Overview

The Saskatchewan Lotto Scraper is a Python-based tool designed to extract lottery draw data from the Western Canada Lottery Corporation (WCLC) website. It supports multiple lottery games, including Lotto 649, Lotto Max, Western 649, Western Max, and Daily Grand. The scraper can extract data from both current and historical draws, with options for batch processing.

The project uses BeautifulSoup for HTML parsing, requests for HTTP requests, and pandas for data manipulation. It provides flexible output options, including CSV and SQLite formats.

## Technical Architecture

The project follows a modular, object-oriented architecture with the following key components:

1. **WCLCScraper Class**: The main class that handles all scraping operations, including HTML fetching, parsing, and data extraction.
2. **Custom Exception Classes**: `WCLCScraperError` and `DataValidationError` for robust error handling.
3. **Game-Specific Parsing Methods**: Dedicated methods for parsing different lottery games.
4. **Batch Historical Scraping**: Functionality to extract historical data by following month navigation links.
5. **Data Validation**: Comprehensive validation rules for different game types.
6. **Output Handlers**: Methods for saving data to CSV and SQLite formats.
7. **CLI Interface**: Command-line interface for flexible usage.
8. **Testing Framework**: Comprehensive unit and live scraping tests.

## Implementation Details

### URL Updates

The WCLC URLs have been updated to use the actual URLs for all supported lottery games:

```python
WCLC_URLS = {
    '649': 'https://www.wclc.com/winning-numbers/lotto-649-extra.htm',
    'max': 'https://www.wclc.com/winning-numbers/lotto-max-extra.htm',
    'western649': 'https://www.wclc.com/winning-numbers/western-649-extra.htm',
    'westernmax': 'https://www.wclc.com/winning-numbers/western-max-extra.htm',
    'dailygrand': 'https://www.wclc.com/winning-numbers/daily-grand-extra.htm'
}
```

### Game Type Support

Support has been added for additional game types:
- **Western Max**: Similar to Lotto Max but specific to Western Canada
- **Daily Grand**: A national lottery game with 5 main numbers

The game type validation has been updated to handle these new game types:

```python
if game_type in ['649', 'western649']:
    # Validation for 649-type games
elif game_type in ['max', 'westernmax']:
    # Validation for Max-type games
elif game_type == 'dailygrand':
    # Validation for Daily Grand
```

### Parsing Methods

New parsing methods have been implemented for the additional game types:
- `parse_westernmax`: For parsing Western Max draw data
- `parse_dailygrand`: For parsing Daily Grand draw data

These methods follow the same pattern as the existing parsing methods, with game-specific selectors and validation rules.

### Batch Historical Scraping

The batch historical scraping functionality has been enhanced with improved month link extraction:

```python
def extract_month_links(self, html: str, base_url: str) -> List[str]:
    # Enhanced selectors for finding month links
    selectors_to_try = [
        'a.pastMonthYearWinners[rel]',  # Primary selector
        'a[rel*="back="]',              # Alternative: any link with back parameter
        '.pastWinNumMonths a[rel]',     # Links within month table
        '.month-nav a[rel]',            # Alternative month navigation
        'a[href*="back="]',             # Links with back parameter in href
        '.pastWinNumMonths a',          # Any links in month table
        '.month-nav a',                 # Any links in month navigation
        'a[href*="month="]',            # Links with month parameter
        'a[href*="year="]'              # Links with year parameter
    ]
    
    # Try rel attribute first, then href if rel is not available
    rel_url = link.get('rel') or link.get('href')
    # ...
```

### Data Validation

The data validation has been enhanced to handle different game types with specific rules:

```python
def _validate_draw_data(self, draw_data: Dict, game_type: str) -> bool:
    # Game-specific validation
    if game_type in ['649', 'western649']:
        if len(numbers) != 6:
            # Validation for 649-type games
    elif game_type in ['max', 'westernmax']:
        if len(numbers) != 7:
            # Validation for Max-type games
    elif game_type == 'dailygrand':
        if len(numbers) != 5:
            # Validation for Daily Grand
    # ...
```

### Error Handling

The error handling has been improved with more specific error messages and logging:

```python
try:
    # Operation that might fail
except requests.exceptions.Timeout as e:
    last_exception = e
    logger.warning(f"Timeout on attempt {attempt + 1}: {e}")
    time.sleep(2 ** attempt)  # Exponential backoff
except requests.exceptions.ConnectionError as e:
    # Handle connection errors
except requests.exceptions.HTTPError as e:
    # Handle HTTP errors
except Exception as e:
    # Handle unexpected errors
```

## Testing Strategy

### Unit Tests

The unit tests cover the core functionality of the scraper, including:
- HTML content validation
- Draw data validation for different game types
- Parsing methods for each game type
- Reading HTML from files
- Fetching HTML with retry logic
- Draw fingerprint creation for duplicate detection
- URL configuration validation

### Live Scraping Tests

The live scraping tests verify the scraper's functionality with actual WCLC websites:
- Testing accessibility of all WCLC URLs
- Live scraping of current pages for each game type
- Extraction of month navigation links
- Batch historical scraping with limited months

The live tests can be run separately from the unit tests using command-line options:
```
python test_wclc_scraper.py --live  # Run live tests only
python test_wclc_scraper.py --all   # Run all tests (unit + live)
python test_wclc_scraper.py         # Run unit tests only (default)
```

## Performance Considerations

The scraper includes several performance optimizations:
- **Exponential backoff** for retry attempts to avoid overwhelming the server
- **Caching of processed URLs** to avoid duplicate requests
- **Deduplication of draws** to avoid duplicate data
- **Respectful scraping** with small delays between requests
- **Limiting batch scraping** to a specified number of months

## Security Considerations

The scraper includes several security considerations:
- **Proper error handling** to avoid exposing sensitive information
- **Input validation** to prevent injection attacks
- **Respectful scraping** to avoid triggering security measures
- **User-Agent and Referer headers** to identify the scraper

## Future Enhancements

Potential future enhancements include:
- **Date parsing and normalization** for better sorting and filtering
- **Prize breakdown scraping** for more detailed information
- **Automatic scheduling** for regular updates
- **Store location geocoding** for mapping
- **Statistical analysis** of draw data

## Conclusion

The Saskatchewan Lotto Scraper has been enhanced with support for multiple lottery games, robust error handling, batch historical scraping, and comprehensive testing capabilities. The project now provides a flexible and reliable tool for extracting lottery draw data from the Western Canada Lottery Corporation website.