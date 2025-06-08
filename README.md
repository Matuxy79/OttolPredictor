# Saskatchewan Lotto Scraper

A command-line tool for scraping lottery draw data from Saskatchewan lottery websites.

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/Matuxy79/OttolPredictor.git
   cd OttolPredictor
   ```

2. Create and activate a virtual environment (recommended):
   ```
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Verify your installation:
   ```
   python verify_install.py
   ```
   This will check if all required dependencies are installed correctly.

## Usage

The script supports multiple lottery games and can fetch data from URLs or local HTML files.

### Basic Usage

```
python main.py --url <lottery_url> --game <game_type> [options]
```

or

```
python main.py --file <html_file> --game <game_type> [options]
```

### Examples

1. Fetch Lotto 6/49 data from a URL and save as CSV:
   ```
   python main.py --url "https://www.wclc.com/winning-numbers/lotto-649-extra.htm" --game 649 --format csv
   ```

2. Process a local HTML file for Lotto Max and save to SQLite:
   ```
   python main.py --file "lottomax.html" --game max --format sqlite
   ```

3. Batch scrape Western 649 historical data:
   ```
   python main.py --url "https://www.wclc.com/winning-numbers/western-649-extra.htm" --game western649 --batch 6
   ```

### Options

- `--url`: URL of the lottery results page
- `--file`: Path to saved HTML file
- `--game`: Lottery game type (649, max, western649)
- `--output`: Output file path (default: auto-generated)
- `--format`: Output format (csv, sqlite, both)
- `--batch`: Scrape historical data (months back)
- `--save-html`: Save downloaded HTML for debugging

## Troubleshooting

If you encounter errors:

1. **Missing dependencies**: Make sure you've installed all required packages:
   ```
   pip install -r requirements.txt
   ```

   If you see the error "Couldn't find a tree builder with the features you requested: lxml", it means the lxml package is missing. Install it with:
   ```
   pip install lxml
   ```

2. **File not found**: Verify the HTML file exists and the path is correct. If using a relative path, make sure you're in the correct directory.

3. **URL errors**: Check your internet connection and make sure the URL is valid. Some websites may block scraping or require specific headers.

4. **HTML parsing errors**: The website structure may have changed; try using `--save-html` to inspect the content.

You can run the verification script to check your installation:
```
python verify_install.py
```

## License

MIT
