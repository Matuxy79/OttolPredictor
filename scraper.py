import argparse
import os
import re
import time
from urllib.parse import urlparse

import pandas as pd
from bs4 import BeautifulSoup


class WebScraper:
    def __init__(self, output_dir="output"):
        """
        Initializes the WebScraper class.

        Args:
            output_dir (str, optional): The directory to save the output files. Defaults to "output".
        """
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def fetch_html(self, file_path):
        """
        Fetches the HTML content from a local file.

        Args:
            file_path (str): The path to the local HTML file.

        Returns:
            str: The HTML content of the page, or None if an error occurred.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
            return html_content
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None

    def extract_data(self, html_content, url):
        """
        Extracts data from the HTML content of a webpage.

        Args:
            html_content (str): The HTML content to parse.
            url (str): The URL of the webpage.

        Returns:
            pandas.DataFrame: A DataFrame containing the extracted data, or None if no data is extracted.
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            table = soup.find('table')

            if not table:
                print("No table found on the page.")
                return None

            headers = [th.text.strip() for th in table.find_all('th')]
            data = []
            for row in table.find_all('tr')[1:]:
                values = [td.text.strip() for td in row.find_all('td')]
                data.append(dict(zip(headers, values)))

            if not data:
                print("No data found in the table.")
                return None

            df = pd.DataFrame(data)
            return df

        except Exception as e:
            print(f"Error extracting data from {url}: {e}")
            return None

    def save_data(self, df, base_filename):
        """
        Saves the extracted data to a CSV file.

        Args:
            df (pandas.DataFrame): The DataFrame to save.
            base_filename (str): The base filename for the output CSV file.
        """
        filepath = os.path.join(self.output_dir, f"{base_filename}.csv")
        df.to_csv(filepath, index=False)
        print(f"Data saved to {filepath}")

    def run_scraper(self, file_paths):
        """
        Runs the web scraper on a list of URLs.

        Args:
            file_paths (list): A list of local file paths to scrape.
        """
        for file_path in file_paths:
            # Extract base filename from the file path
            base_filename = os.path.splitext(os.path.basename(file_path))[0]
            print(f"Scraping data from {file_path}...")

            html_content = self.fetch_html(file_path)
            if not html_content:
                print(f"Failed to fetch HTML from {file_path}. Skipping...")
                continue

            df = self.extract_data(html_content, file_path)
            if df is not None:
                self.save_data(df, base_filename)
            else:
                print(f"No data extracted from {file_path}.")

def main():
    parser = argparse.ArgumentParser(description="Web scraper to extract tabular data from HTML files.")
    parser.add_argument("file_paths", nargs="+", help="Path(s) to the local HTML file(s) to scrape.")
    parser.add_argument("--output_dir", default="output", help="Output directory for the CSV files.")

    args = parser.parse_args()

    scraper = WebScraper(output_dir=args.output_dir)
    scraper.run_scraper(args.file_paths)

if __name__ == "__main__":
    main()

