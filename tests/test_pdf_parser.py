"""Test PDF parsing against known good data"""

import unittest
import os
import sys
import pandas as pd
from datetime import datetime
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_sources.pdf_parser import WCLCPDFParser
from core.data_validator import DataValidator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestPDFParser(unittest.TestCase):
    """Test the PDF parser functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.parser = WCLCPDFParser(data_dir="data")
        
        # Create a small test dataset for comparison
        self.test_649_data = [
            {
                'game': 'Lotto 649',
                'date': '2024-06-01',
                'numbers': [1, 2, 3, 4, 5, 6],
                'bonus': 7,
                'source': 'WCLC_PDF_Archive'
            },
            {
                'game': 'Lotto 649',
                'date': '2024-06-05',
                'numbers': [10, 20, 30, 40, 41, 49],
                'bonus': 25,
                'source': 'WCLC_PDF_Archive'
            }
        ]
        
        self.test_max_data = [
            {
                'game': 'Lotto Max',
                'date': '2024-06-02',
                'numbers': [5, 10, 15, 20, 25, 30, 35],
                'bonus': 40,
                'source': 'WCLC_PDF_Archive'
            },
            {
                'game': 'Lotto Max',
                'date': '2024-06-06',
                'numbers': [7, 14, 21, 28, 35, 42, 49],
                'bonus': 10,
                'source': 'WCLC_PDF_Archive'
            }
        ]
    
    def test_649_parsing(self):
        """Test that PDF parser produces expected format for 649"""
        # Skip if PDF file doesn't exist
        pdf_path = os.path.join("data", "LOTTO 649 SINCE INCEPTION.pdf")
        if not os.path.exists(pdf_path):
            logger.warning(f"Skipping test_649_parsing: PDF file not found at {pdf_path}")
            self.skipTest(f"PDF file not found: {pdf_path}")
        
        try:
            # Parse a small section of the PDF
            df = self.parser.parse_649_archive()
            
            # Check that we got some data
            self.assertFalse(df.empty, "No data parsed from 649 PDF")
            
            # Check required columns
            required_columns = ['game', 'date', 'numbers', 'bonus']
            for col in required_columns:
                self.assertIn(col, df.columns, f"Missing required column: {col}")
            
            # Check data types
            self.assertEqual(df['game'].iloc[0], 'Lotto 649', "Game name should be 'Lotto 649'")
            
            # Validate a sample of rows
            for _, row in df.head(5).iterrows():
                # Convert row to dict for validation
                draw_data = row.to_dict()
                
                # Normalize numbers field for validation
                if 'numbers' in draw_data:
                    draw_data['numbers'] = DataValidator.normalize_numbers_field(draw_data['numbers'])
                
                # Validate format
                self.assertTrue(
                    DataValidator.validate_draw_format(draw_data),
                    f"Invalid draw format: {draw_data}"
                )
            
            logger.info(f"Successfully validated {len(df)} draws from 649 PDF")
        
        except Exception as e:
            self.fail(f"Error parsing 649 PDF: {e}")
    
    def test_max_parsing(self):
        """Test that PDF parser produces expected format for Max"""
        # Skip if PDF file doesn't exist
        pdf_path = os.path.join("data", "LOTTO MAX since Inception.pdf")
        if not os.path.exists(pdf_path):
            logger.warning(f"Skipping test_max_parsing: PDF file not found at {pdf_path}")
            self.skipTest(f"PDF file not found: {pdf_path}")
        
        try:
            # Parse a small section of the PDF
            df = self.parser.parse_max_archive()
            
            # Check that we got some data
            self.assertFalse(df.empty, "No data parsed from Max PDF")
            
            # Check required columns
            required_columns = ['game', 'date', 'numbers', 'bonus']
            for col in required_columns:
                self.assertIn(col, df.columns, f"Missing required column: {col}")
            
            # Check data types
            self.assertEqual(df['game'].iloc[0], 'Lotto Max', "Game name should be 'Lotto Max'")
            
            # Validate a sample of rows
            for _, row in df.head(5).iterrows():
                # Convert row to dict for validation
                draw_data = row.to_dict()
                
                # Normalize numbers field for validation
                if 'numbers' in draw_data:
                    draw_data['numbers'] = DataValidator.normalize_numbers_field(draw_data['numbers'])
                
                # Validate format
                self.assertTrue(
                    DataValidator.validate_draw_format(draw_data),
                    f"Invalid draw format: {draw_data}"
                )
            
            logger.info(f"Successfully validated {len(df)} draws from Max PDF")
        
        except Exception as e:
            self.fail(f"Error parsing Max PDF: {e}")
    
    def test_data_consistency(self):
        """Test that PDF data doesn't conflict with existing CSV data"""
        # Skip if no CSV files exist
        csv_files = [f for f in os.listdir() if f.endswith('.csv') and ('649' in f or 'max' in f)]
        if not csv_files:
            logger.warning("Skipping test_data_consistency: No CSV files found")
            self.skipTest("No CSV files found for comparison")
        
        try:
            # Load CSV data
            csv_data = None
            for csv_file in csv_files:
                if csv_data is None:
                    csv_data = pd.read_csv(csv_file)
                else:
                    csv_data = pd.concat([csv_data, pd.read_csv(csv_file)])
            
            if csv_data is None or csv_data.empty:
                logger.warning("Skipping test_data_consistency: CSV files are empty")
                self.skipTest("CSV files are empty")
            
            # Check for date column
            if 'date' not in csv_data.columns:
                logger.warning("Skipping test_data_consistency: CSV files don't have 'date' column")
                self.skipTest("CSV files don't have 'date' column")
            
            # Get unique dates from CSV
            csv_dates = set(csv_data['date'].unique())
            
            # Check 649 PDF data for conflicts
            pdf_path = os.path.join("data", "LOTTO 649 SINCE INCEPTION.pdf")
            if os.path.exists(pdf_path):
                pdf_649_data = self.parser.parse_649_archive()
                
                if not pdf_649_data.empty and 'date' in pdf_649_data.columns:
                    # Check for date overlaps
                    pdf_dates = set(pdf_649_data['date'].unique())
                    overlapping_dates = pdf_dates.intersection(csv_dates)
                    
                    # For overlapping dates, check for data consistency
                    if overlapping_dates:
                        for date in list(overlapping_dates)[:5]:  # Check first 5 overlaps
                            csv_row = csv_data[csv_data['date'] == date].iloc[0]
                            pdf_row = pdf_649_data[pdf_649_data['date'] == date].iloc[0]
                            
                            # Convert to dictionaries
                            csv_dict = csv_row.to_dict()
                            pdf_dict = pdf_row.to_dict()
                            
                            # Normalize numbers for comparison
                            if 'numbers' in csv_dict and 'numbers' in pdf_dict:
                                csv_numbers = DataValidator.normalize_numbers_field(csv_dict['numbers'])
                                pdf_numbers = DataValidator.normalize_numbers_field(pdf_dict['numbers'])
                                
                                # Check that numbers match
                                self.assertEqual(
                                    sorted(csv_numbers),
                                    sorted(pdf_numbers),
                                    f"Numbers don't match for date {date}: CSV {csv_numbers}, PDF {pdf_numbers}"
                                )
                            
                            # Check bonus number
                            if 'bonus' in csv_dict and 'bonus' in pdf_dict:
                                csv_bonus = int(csv_dict['bonus']) if csv_dict['bonus'] is not None else None
                                pdf_bonus = int(pdf_dict['bonus']) if pdf_dict['bonus'] is not None else None
                                
                                self.assertEqual(
                                    csv_bonus,
                                    pdf_bonus,
                                    f"Bonus doesn't match for date {date}: CSV {csv_bonus}, PDF {pdf_bonus}"
                                )
                    
                    logger.info(f"Checked consistency for {len(overlapping_dates)} overlapping dates between CSV and 649 PDF")
            
            # Check Max PDF data for conflicts
            pdf_path = os.path.join("data", "LOTTO MAX since Inception.pdf")
            if os.path.exists(pdf_path):
                pdf_max_data = self.parser.parse_max_archive()
                
                if not pdf_max_data.empty and 'date' in pdf_max_data.columns:
                    # Check for date overlaps
                    pdf_dates = set(pdf_max_data['date'].unique())
                    overlapping_dates = pdf_dates.intersection(csv_dates)
                    
                    # For overlapping dates, check for data consistency
                    if overlapping_dates:
                        for date in list(overlapping_dates)[:5]:  # Check first 5 overlaps
                            csv_row = csv_data[csv_data['date'] == date].iloc[0]
                            pdf_row = pdf_max_data[pdf_max_data['date'] == date].iloc[0]
                            
                            # Convert to dictionaries
                            csv_dict = csv_row.to_dict()
                            pdf_dict = pdf_row.to_dict()
                            
                            # Normalize numbers for comparison
                            if 'numbers' in csv_dict and 'numbers' in pdf_dict:
                                csv_numbers = DataValidator.normalize_numbers_field(csv_dict['numbers'])
                                pdf_numbers = DataValidator.normalize_numbers_field(pdf_dict['numbers'])
                                
                                # Check that numbers match
                                self.assertEqual(
                                    sorted(csv_numbers),
                                    sorted(pdf_numbers),
                                    f"Numbers don't match for date {date}: CSV {csv_numbers}, PDF {pdf_numbers}"
                                )
                            
                            # Check bonus number
                            if 'bonus' in csv_dict and 'bonus' in pdf_dict:
                                csv_bonus = int(csv_dict['bonus']) if csv_dict['bonus'] is not None else None
                                pdf_bonus = int(pdf_dict['bonus']) if pdf_dict['bonus'] is not None else None
                                
                                self.assertEqual(
                                    csv_bonus,
                                    pdf_bonus,
                                    f"Bonus doesn't match for date {date}: CSV {csv_bonus}, PDF {pdf_bonus}"
                                )
                    
                    logger.info(f"Checked consistency for {len(overlapping_dates)} overlapping dates between CSV and Max PDF")
        
        except Exception as e:
            self.fail(f"Error checking data consistency: {e}")
    
    def test_line_parsing_649(self):
        """Test parsing of individual 649 lines"""
        # Test various line formats
        test_lines = [
            "2024-06-01    01 02 03 04 05 06    Bonus: 07",
            "2024/06/05    10 20 30 40 41 49    Bonus: 25",
            "15 Jun 2024    01 02 03 04 05 06    07",
            "2024-06-10    01 02 03 04 05 06    07"
        ]
        
        expected_results = [
            {
                'date': '2024-06-01',
                'numbers': [1, 2, 3, 4, 5, 6],
                'bonus': 7,
                'game': 'Lotto 649',
                'source': 'WCLC_PDF_Archive'
            },
            {
                'date': '2024-06-05',
                'numbers': [10, 20, 30, 40, 41, 49],
                'bonus': 25,
                'game': 'Lotto 649',
                'source': 'WCLC_PDF_Archive'
            },
            {
                'date': '2024-06-15',
                'numbers': [1, 2, 3, 4, 5, 6],
                'bonus': 7,
                'game': 'Lotto 649',
                'source': 'WCLC_PDF_Archive'
            },
            {
                'date': '2024-06-10',
                'numbers': [1, 2, 3, 4, 5, 6],
                'bonus': 7,
                'game': 'Lotto 649',
                'source': 'WCLC_PDF_Archive'
            }
        ]
        
        for i, line in enumerate(test_lines):
            result = self.parser._parse_649_line(line)
            self.assertIsNotNone(result, f"Failed to parse line: {line}")
            
            # Check date
            self.assertEqual(result['date'], expected_results[i]['date'], 
                            f"Date mismatch for line: {line}")
            
            # Check numbers
            self.assertEqual(result['numbers'], expected_results[i]['numbers'], 
                            f"Numbers mismatch for line: {line}")
            
            # Check bonus
            self.assertEqual(result['bonus'], expected_results[i]['bonus'], 
                            f"Bonus mismatch for line: {line}")
    
    def test_line_parsing_max(self):
        """Test parsing of individual Max lines"""
        # Test various line formats
        test_lines = [
            "2024-06-02    05 10 15 20 25 30 35    Bonus: 40",
            "2024/06/06    07 14 21 28 35 42 49    Bonus: 10",
            "15 Jun 2024    05 10 15 20 25 30 35    40",
            "2024-06-12    07 14 21 28 35 42 49    10"
        ]
        
        expected_results = [
            {
                'date': '2024-06-02',
                'numbers': [5, 10, 15, 20, 25, 30, 35],
                'bonus': 40,
                'game': 'Lotto Max',
                'source': 'WCLC_PDF_Archive'
            },
            {
                'date': '2024-06-06',
                'numbers': [7, 14, 21, 28, 35, 42, 49],
                'bonus': 10,
                'game': 'Lotto Max',
                'source': 'WCLC_PDF_Archive'
            },
            {
                'date': '2024-06-15',
                'numbers': [5, 10, 15, 20, 25, 30, 35],
                'bonus': 40,
                'game': 'Lotto Max',
                'source': 'WCLC_PDF_Archive'
            },
            {
                'date': '2024-06-12',
                'numbers': [7, 14, 21, 28, 35, 42, 49],
                'bonus': 10,
                'game': 'Lotto Max',
                'source': 'WCLC_PDF_Archive'
            }
        ]
        
        for i, line in enumerate(test_lines):
            result = self.parser._parse_max_line(line)
            self.assertIsNotNone(result, f"Failed to parse line: {line}")
            
            # Check date
            self.assertEqual(result['date'], expected_results[i]['date'], 
                            f"Date mismatch for line: {line}")
            
            # Check numbers
            self.assertEqual(result['numbers'], expected_results[i]['numbers'], 
                            f"Numbers mismatch for line: {line}")
            
            # Check bonus
            self.assertEqual(result['bonus'], expected_results[i]['bonus'], 
                            f"Bonus mismatch for line: {line}")

if __name__ == '__main__':
    unittest.main()