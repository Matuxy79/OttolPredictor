"""
PDF archive parser for historical WCLC data

CRITICAL IMPLEMENTATION NOTES:
1. WCLC PDFs use format: "2024-06-15    01 02 03 04 05 06    Bonus: 07"
2. Must handle both Lotto 649 (6 numbers) and Lotto Max (7 numbers)
3. Some PDFs may have inconsistent spacing or formatting
4. Must normalize ALL data to match existing CSV structure
5. Error handling is CRITICAL - PDFs can be corrupted
"""

import pdfplumber
import pandas as pd
import re
from datetime import datetime
from typing import List, Dict, Optional
import logging
import os
import json

class WCLCPDFParser:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.logger = logging.getLogger(__name__)

    def parse_649_archive(self) -> pd.DataFrame:
        """Parse LOTTO 649 SINCE INCEPTION.pdf"""
        pdf_path = os.path.join(self.data_dir, "LOTTO 649 SINCE INCEPTION.pdf")
        self.logger.info(f"Parsing 649 archive from {pdf_path}")

        if not os.path.exists(pdf_path):
            self.logger.error(f"PDF file not found: {pdf_path}")
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        draws = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                self.logger.info(f"PDF has {total_pages} pages")

                for page_num, page in enumerate(pdf.pages):
                    self.logger.debug(f"Processing page {page_num+1}/{total_pages}")

                    try:
                        text = page.extract_text()
                        if not text:
                            self.logger.warning(f"No text extracted from page {page_num+1}")
                            continue

                        # Process each line of the page
                        lines = text.split('\n')
                        for line in lines:
                            try:
                                draw_data = self._parse_649_line(line)
                                if draw_data:
                                    draws.append(draw_data)
                            except Exception as e:
                                self.logger.warning(f"Error parsing line: {line}. Error: {e}")
                                continue

                    except Exception as e:
                        self.logger.error(f"Error processing page {page_num+1}: {e}")
                        continue

        except Exception as e:
            self.logger.error(f"Error opening PDF: {e}")
            raise

        # Convert to DataFrame
        if not draws:
            self.logger.warning("No draws parsed from PDF")
            return pd.DataFrame()

        df = pd.DataFrame(draws)
        self.logger.info(f"Successfully parsed {len(df)} draws from 649 PDF")

        # Normalize to match CSV format
        df = self._normalize_to_csv_format(df)
        # Schema validation: ensure canonical fields
        try:
            from utils.data_validation import validate_draw_record
            import pandas as pd
            df = df.apply(lambda row: validate_draw_record(row.to_dict()), axis=1)
            df = pd.DataFrame(list(df))
        except Exception as e:
            self.logger.warning(f"Error validating draw records: {e}")
        return df

    def parse_max_archive(self) -> pd.DataFrame:
        """Parse LOTTO MAX since Inception.pdf"""
        pdf_path = os.path.join(self.data_dir, "LOTTO MAX since Inception.pdf")
        self.logger.info(f"Parsing Max archive from {pdf_path}")

        if not os.path.exists(pdf_path):
            self.logger.error(f"PDF file not found: {pdf_path}")
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        draws = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                self.logger.info(f"PDF has {total_pages} pages")

                for page_num, page in enumerate(pdf.pages):
                    self.logger.debug(f"Processing page {page_num+1}/{total_pages}")

                    try:
                        text = page.extract_text()
                        if not text:
                            self.logger.warning(f"No text extracted from page {page_num+1}")
                            continue

                        # Process each line of the page
                        lines = text.split('\n')
                        for line in lines:
                            try:
                                draw_data = self._parse_max_line(line)
                                if draw_data:
                                    draws.append(draw_data)
                            except Exception as e:
                                self.logger.warning(f"Error parsing line: {line}. Error: {e}")
                                continue

                    except Exception as e:
                        self.logger.error(f"Error processing page {page_num+1}: {e}")
                        continue

        except Exception as e:
            self.logger.error(f"Error opening PDF: {e}")
            raise

        # Convert to DataFrame
        if not draws:
            self.logger.warning("No draws parsed from PDF")
            return pd.DataFrame()

        df = pd.DataFrame(draws)
        self.logger.info(f"Successfully parsed {len(df)} draws from Max PDF")

        # Normalize to match CSV format
        df = self._normalize_to_csv_format(df)
        # Schema validation: ensure canonical fields
        try:
            from utils.data_validation import validate_draw_record
            import pandas as pd
            df = df.apply(lambda row: validate_draw_record(row.to_dict()), axis=1)
            df = pd.DataFrame(list(df))
        except Exception as e:
            self.logger.warning(f"Error validating draw records: {e}")
        return df

    def _parse_649_line(self, line: str) -> Optional[Dict]:
        """
        Parse a single line from the 649 PDF with comprehensive format support

        Expected formats:
        - "2024-06-15    01 02 03 04 05 06    Bonus: 07"
        - "June 15, 2024  1  2  3  4  5  6  Bonus 7"
        - "15 Jun 2024    01 02 03 04 05 06    07"
        """
        # Skip header or irrelevant lines
        if not line or len(line) < 15:
            return None

        # Skip obvious header lines
        skip_patterns = ["LOTTO", "Page", "Date", "Draw", "Numbers", "Bonus", "---", "==="]
        if any(pattern in line.upper() for pattern in skip_patterns):
            return None

        # Enhanced regex patterns to handle various date formats
        patterns = [
            # Pattern 1: YYYY-MM-DD format with various spacing
            r'(\d{4}-\d{2}-\d{2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+.*?(\d{1,2})',

            # Pattern 2: YYYY/MM/DD format  
            r'(\d{4}/\d{2}/\d{2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+.*?(\d{1,2})',

            # Pattern 3: Full month name with comma (e.g., "June 15, 2024")
            r'([A-Za-z]+\s+\d{1,2},\s+\d{4})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+.*?(\d{1,2})',

            # Pattern 4: Abbreviated month (e.g., "15 Jun 2024")
            r'(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+.*?(\d{1,2})',

            # Pattern 5: DD/MM/YYYY format
            r'(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+.*?(\d{1,2})',

            # Pattern 6: Abbreviated month without comma (e.g., "Jun 15 2024")
            r'([A-Za-z]{3}\s+\d{1,2}\s+\d{4})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+.*?(\d{1,2})'
        ]

        for pattern in patterns:
            match = re.match(pattern, line.strip())
            if match:
                groups = match.groups()
                date_str = groups[0]

                try:
                    # Parse numbers (groups 1-6)
                    numbers = []
                    for i in range(1, 7):
                        num = int(groups[i])
                        if 1 <= num <= 49:  # Valid 649 range
                            numbers.append(num)
                        else:
                            # Invalid number range, skip this line
                            return None

                    # Parse bonus (group 7)
                    bonus = None
                    if len(groups) > 7 and groups[7]:
                        bonus_val = int(groups[7])
                        if 1 <= bonus_val <= 49:
                            bonus = bonus_val

                    # Ensure we have exactly 6 numbers
                    if len(numbers) != 6:
                        return None

                    # Normalize date to YYYY-MM-DD format
                    normalized_date = self._normalize_date(date_str)

                    return {
                        'game': 'Lotto 649',
                        'date': normalized_date,
                        'numbers': numbers,  # Keep as list
                        'bonus': bonus,
                        'source': 'WCLC_PDF_Archive'
                    }

                except (ValueError, IndexError) as e:
                    # Failed to parse numbers, skip this line
                    continue

        # If no pattern matched, try a more flexible approach
        if re.search(r'\d{4}[-/]\d{2}[-/]\d{2}|\d{1,2}\s+[A-Za-z]{3}\s+\d{4}|[A-Za-z]+\s+\d{1,2},\s+\d{4}', line):
            self.logger.debug(f"Attempting flexible parsing for line: {line}")

            # Extract date - now including full month name format
            date_match = re.search(r'(\d{4}[-/]\d{2}[-/]\d{2}|\d{1,2}\s+[A-Za-z]{3}\s+\d{4}|[A-Za-z]+\s+\d{1,2},\s+\d{4})', line)
            if not date_match:
                return None

            date_str = date_match.group(1)

            # Try to extract 6 numbers and a bonus
            numbers_match = re.findall(r'\b\d{1,2}\b', line[date_match.end():])
            if len(numbers_match) < 7:  # Need at least 6 numbers + bonus
                return None

            # Validate numbers are in range
            valid_numbers = []
            for num_str in numbers_match[:6]:
                num = int(num_str)
                if 1 <= num <= 49:  # Valid 649 range
                    valid_numbers.append(num)
                else:
                    # Invalid number, might be part of something else
                    return None

            if len(valid_numbers) != 6:
                return None

            # Parse bonus
            bonus = None
            if len(numbers_match) > 6:
                bonus_val = int(numbers_match[6])
                if 1 <= bonus_val <= 49:
                    bonus = bonus_val

            # Normalize date format
            normalized_date = self._normalize_date(date_str)

            return {
                'date': normalized_date,
                'numbers': valid_numbers,
                'bonus': bonus,
                'game': 'Lotto 649',
                'source': 'WCLC_PDF_Archive'
            }

        return None

    def _parse_max_line(self, line: str) -> Optional[Dict]:
        """
        Parse a single line from the Max PDF with comprehensive format support

        Expected formats:
        - "2024-06-15    01 02 03 04 05 06 07    Bonus: 08"
        - "June 15, 2024  1  2  3  4  5  6  7  Bonus 8"
        - "15 Jun 2024    01 02 03 04 05 06 07    08"
        """
        # Skip header or irrelevant lines
        if not line or len(line) < 15:
            return None

        # Skip obvious header lines
        skip_patterns = ["LOTTO", "Page", "Date", "Draw", "Numbers", "Bonus", "---", "==="]
        if any(pattern in line.upper() for pattern in skip_patterns):
            return None

        # Enhanced regex patterns to handle various date formats
        patterns = [
            # Pattern 1: YYYY-MM-DD format with various spacing
            r'(\d{4}-\d{2}-\d{2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+.*?(\d{1,2})',

            # Pattern 2: YYYY/MM/DD format  
            r'(\d{4}/\d{2}/\d{2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+.*?(\d{1,2})',

            # Pattern 3: Full month name with comma (e.g., "June 15, 2024")
            r'([A-Za-z]+\s+\d{1,2},\s+\d{4})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+.*?(\d{1,2})',

            # Pattern 4: Abbreviated month (e.g., "15 Jun 2024")
            r'(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+.*?(\d{1,2})',

            # Pattern 5: DD/MM/YYYY format
            r'(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+.*?(\d{1,2})',

            # Pattern 6: Abbreviated month without comma (e.g., "Jun 15 2024")
            r'([A-Za-z]{3}\s+\d{1,2}\s+\d{4})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+.*?(\d{1,2})'
        ]

        for pattern in patterns:
            match = re.match(pattern, line.strip())
            if match:
                groups = match.groups()
                date_str = groups[0]

                try:
                    # Parse numbers (groups 1-7)
                    numbers = []
                    for i in range(1, 8):
                        num = int(groups[i])
                        if 1 <= num <= 50:  # Valid Max range
                            numbers.append(num)
                        else:
                            # Invalid number range, skip this line
                            return None

                    # Parse bonus (group 8)
                    bonus = None
                    if len(groups) > 8 and groups[8]:
                        bonus_val = int(groups[8])
                        if 1 <= bonus_val <= 50:
                            bonus = bonus_val

                    # Ensure we have exactly 7 numbers
                    if len(numbers) != 7:
                        return None

                    # Normalize date to YYYY-MM-DD format
                    normalized_date = self._normalize_date(date_str)

                    return {
                        'game': 'Lotto Max',
                        'date': normalized_date,
                        'numbers': numbers,  # Keep as list
                        'bonus': bonus,
                        'source': 'WCLC_PDF_Archive'
                    }

                except (ValueError, IndexError) as e:
                    # Failed to parse numbers, skip this line
                    continue

        # If no pattern matched, try a more flexible approach
        if re.search(r'\d{4}[-/]\d{2}[-/]\d{2}|\d{1,2}\s+[A-Za-z]{3}\s+\d{4}|[A-Za-z]+\s+\d{1,2},\s+\d{4}', line):
            self.logger.debug(f"Attempting flexible parsing for line: {line}")

            # Extract date - now including full month name format
            date_match = re.search(r'(\d{4}[-/]\d{2}[-/]\d{2}|\d{1,2}\s+[A-Za-z]{3}\s+\d{4}|[A-Za-z]+\s+\d{1,2},\s+\d{4})', line)
            if not date_match:
                return None

            date_str = date_match.group(1)

            # Try to extract 7 numbers and a bonus
            numbers_match = re.findall(r'\b\d{1,2}\b', line[date_match.end():])
            if len(numbers_match) < 8:  # Need at least 7 numbers + bonus
                return None

            # Validate numbers are in range
            valid_numbers = []
            for num_str in numbers_match[:7]:
                num = int(num_str)
                if 1 <= num <= 50:  # Valid Max range
                    valid_numbers.append(num)
                else:
                    # Invalid number, might be part of something else
                    return None

            if len(valid_numbers) != 7:
                return None

            # Parse bonus
            bonus = None
            if len(numbers_match) > 7:
                bonus_val = int(numbers_match[7])
                if 1 <= bonus_val <= 50:
                    bonus = bonus_val

            # Normalize date format
            normalized_date = self._normalize_date(date_str)

            return {
                'date': normalized_date,
                'numbers': valid_numbers,
                'bonus': bonus,
                'game': 'Lotto Max',
                'source': 'WCLC_PDF_Archive'
            }

        return None

    def _normalize_date(self, date_str: str) -> str:
        """Convert various date formats to consistent YYYY-MM-DD format"""
        if not date_str or date_str.lower() in ['unknown', 'nan', 'nat']:
            return 'Unknown'

        date_str = date_str.strip()

        # Common date formats to try
        date_formats = [
            '%Y-%m-%d',         # 2024-06-15
            '%Y/%m/%d',         # 2024/06/15
            '%B %d, %Y',        # June 15, 2024
            '%b %d, %Y',        # Jun 15, 2024
            '%d %B %Y',         # 15 June 2024
            '%d %b %Y',         # 15 Jun 2024
            '%b %d %Y',         # Jun 15 2024
            '%B %d %Y',         # June 15 2024
            '%m/%d/%Y',         # 06/15/2024
            '%d/%m/%Y',         # 15/06/2024
        ]

        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                return parsed_date.strftime('%Y-%m-%d')
            except ValueError:
                continue

        # If no format works, log warning and return original
        self.logger.warning(f"Could not parse date format: '{date_str}'")
        return date_str

    def _normalize_to_csv_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert PDF data to match existing CSV structure"""
        if df.empty:
            return df

        # Add required columns to match CSV format
        df['scraped_at'] = datetime.now().isoformat()
        df['source_block_index'] = range(len(df))

        # Convert numbers to string representation to match CSV format
        df['numbers'] = df['numbers'].apply(lambda x: str(x))

        # Add gold_ball column (None for PDF data)
        if 'gold_ball' not in df.columns:
            df['gold_ball'] = None

        # Ensure column order matches CSV
        columns = ['game', 'date', 'numbers', 'bonus', 'gold_ball', 'scraped_at', 'source_block_index']

        # Only include columns that exist in the DataFrame
        existing_columns = [col for col in columns if col in df.columns]

        return df[existing_columns]

    def save_processed_data(self, df: pd.DataFrame, game: str) -> str:
        """Save processed data to CSV in the processed directory"""
        if df.empty:
            self.logger.warning(f"No data to save for {game}")
            return ""

        # Create processed directory if it doesn't exist
        processed_dir = os.path.join(self.data_dir, "processed")
        os.makedirs(processed_dir, exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{game.lower().replace(' ', '_')}_pdf_archive_{timestamp}.csv"
        filepath = os.path.join(processed_dir, filename)

        # Save to CSV
        df.to_csv(filepath, index=False)
        self.logger.info(f"Saved {len(df)} records to {filepath}")

        return filepath
