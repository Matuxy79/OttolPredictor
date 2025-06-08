# Lottery 649 Web Scraper
# Extracts draw results from HTML and saves to CSV

# 1. Import dependencies
from bs4 import BeautifulSoup
import pandas as pd
import os

def extract_lotto649_data(html_file='lotto649.html', output_file='lotto649_results.csv'):
    """
    Extract Lotto 649 draw data from HTML file and save to CSV

    Args:
        html_file (str): Path to the HTML file containing lottery data
        output_file (str): Path for the output CSV file
    """

    # Check if HTML file exists
    if not os.path.exists(html_file):
        print(f"Error: {html_file} not found!")
        print("Please save the webpage HTML to 'lotto649.html' first.")
        return False

    # 2. Load the HTML file
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html = f.read()
    except Exception as e:
        print(f"Error reading HTML file: {e}")
        return False

    # 3. Parse HTML
    soup = BeautifulSoup(html, 'lxml')

    # 4. Extract data (loop through each draw block)
    draws = []
    draw_blocks = soup.find_all('div', class_='pastWinNum')

    if not draw_blocks:
        print("No draw blocks found. Please check the HTML structure.")
        print("Looking for divs with class 'pastWinNum'...")
        return False

    print(f"Found {len(draw_blocks)} draw blocks. Processing...")

    for block in draw_blocks:
        # Get date
        date_element = block.find('div', class_='pastWinNumDate')
        date = date_element.get_text(strip=True) if date_element else ''

        # Get main numbers
        number_elements = block.find_all('li', class_='pastWinNumber')
        numbers = [li.get_text(strip=True) for li in number_elements]

        # Get bonus number
        bonus = ''
        bonus_element = block.find('li', class_='pastWinNumberBonus')
        if bonus_element:
            # Extract just the number part after "Bonus"
            bonus_text = bonus_element.get_text(strip=True)
            bonus = ''.join(filter(str.isdigit, bonus_text))

        # Optional: Get Gold Ball if it exists
        gold_ball = ''
        gold_element = block.find('li', class_='pastWinNumberGold')
        if gold_element:
            gold_ball = ''.join(filter(str.isdigit, gold_element.get_text()))

        # Store the draw data
        draw_data = {
            'date': date,
            'numbers': ','.join(numbers),
            'bonus': bonus,
        }

        # Add Gold Ball if found
        if gold_ball:
            draw_data['gold_ball'] = gold_ball

        draws.append(draw_data)

    # 5. Output to CSV
    if draws:
        df = pd.DataFrame(draws)
        df.to_csv(output_file, index=False)
        print(f"Success! {len(draws)} draws saved to {output_file}")

        # Display first few rows as preview
        print("\nPreview of extracted data:")
        print(df.head())
        return True
    else:
        print("No draw data extracted. Please check the HTML structure.")
        return False

def install_dependencies():
    """
    Print installation instructions for required dependencies
    """
    print("To install required dependencies, run:")
    print("pip install beautifulsoup4 lxml pandas")
    print()

if __name__ == '__main__':
    print("Lotto 649 Data Extractor")
    print("=" * 30)

    # Check if dependencies might be missing and show install instructions
    try:
        from bs4 import BeautifulSoup
        import pandas as pd
    except ImportError as e:
        print(f"Missing dependency: {e}")
        install_dependencies()
        exit(1)

    # Run the extraction
    success = extract_lotto649_data()

    if success:
        print("\nNext steps:")
        print("1. Open lotto649_results.csv in Excel or any spreadsheet app")
        print("2. Use the data for analysis, statistics, or your next-gen tool")
        print("3. For Lotto Max or other games, update the CSS selectors accordingly")
    else:
        print("\nTroubleshooting:")
        print("1. Make sure 'lotto649.html' is in the same directory")
        print("2. Check that the HTML contains lottery draw data")
        print("3. Verify the CSS class names match the website structure")
