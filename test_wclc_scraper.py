"""
Unit tests for WCLC Scraper
Testing each game type and core functionality
"""

import unittest
import os
import tempfile
from unittest.mock import patch, Mock
from main import WCLCScraper, WCLCScraperError, DataValidationError

class TestWCLCScraper(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.scraper = WCLCScraper(max_retries=1, timeout=5)
    
    def test_validate_html_content_valid(self):
        """Test HTML content validation with valid lottery content"""
        valid_html = """
        <html>
        <body>
            <div>WCLC Winning Numbers</div>
            <div>Latest Draw Results</div>
            <div>Lotto 649 Jackpot</div>
            <div>Bonus Number</div>
        </body>
        </html>
        """ * 10  # Make it long enough
        
        self.assertTrue(self.scraper._validate_html_content(valid_html))
    
    def test_validate_html_content_invalid(self):
        """Test HTML content validation with invalid content"""
        invalid_html = "<html><body>Not lottery content</body></html>"
        self.assertFalse(self.scraper._validate_html_content(invalid_html))
    
    def test_validate_draw_data_lotto649_valid(self):
        """Test draw data validation for valid Lotto 649 data"""
        valid_data = {
            'game': 'Lotto 649',
            'date': 'Dec 21, 2024',
            'numbers': '1,15,23,31,42,49',
            'bonus': '7'
        }
        self.assertTrue(self.scraper._validate_draw_data(valid_data, '649'))
    
    def test_validate_draw_data_lotto649_invalid_count(self):
        """Test draw data validation for invalid number count"""
        invalid_data = {
            'game': 'Lotto 649',
            'date': 'Dec 21, 2024',
            'numbers': '1,15,23,31,42',  # Only 5 numbers
            'bonus': '7'
        }
        self.assertFalse(self.scraper._validate_draw_data(invalid_data, '649'))
    
    def test_validate_draw_data_lotto649_invalid_range(self):
        """Test draw data validation for numbers out of range"""
        invalid_data = {
            'game': 'Lotto 649',
            'date': 'Dec 21, 2024',
            'numbers': '1,15,23,31,42,55',  # 55 is out of range
            'bonus': '7'
        }
        self.assertFalse(self.scraper._validate_draw_data(invalid_data, '649'))
    
    def test_validate_draw_data_lottomax_valid(self):
        """Test draw data validation for valid Lotto Max data"""
        valid_data = {
            'game': 'Lotto Max',
            'date': 'Dec 21, 2024',
            'numbers': '1,15,23,31,42,49,50',  # 7 numbers
            'bonus': '7'
        }
        self.assertTrue(self.scraper._validate_draw_data(valid_data, 'max'))
    
    def test_parse_lotto649_with_sample_html(self):
        """Test Lotto 649 parsing with sample HTML"""
        sample_html = """
        <html>
        <body>
            <div class="pastWinNum">
                <div class="pastWinNumDate">Dec 21, 2024</div>
                <ul>
                    <li class="pastWinNumber">1</li>
                    <li class="pastWinNumber">15</li>
                    <li class="pastWinNumber">23</li>
                    <li class="pastWinNumber">31</li>
                    <li class="pastWinNumber">42</li>
                    <li class="pastWinNumber">49</li>
                    <li class="pastWinNumberBonus">Bonus: 7</li>
                    <li class="pastWinNumberGold">Gold Ball: 3</li>
                </ul>
            </div>
            <div>WCLC lottery winning numbers draw jackpot bonus</div>
        </body>
        </html>
        """
        
        draws = self.scraper.parse_lotto649(sample_html)
        
        self.assertEqual(len(draws), 1)
        self.assertEqual(draws[0]['game'], 'Lotto 649')
        self.assertEqual(draws[0]['date'], 'Dec 21, 2024')
        self.assertEqual(draws[0]['numbers'], '1,15,23,31,42,49')
        self.assertEqual(draws[0]['bonus'], '7')
        self.assertEqual(draws[0]['gold_ball'], '3')
    
    def test_parse_lottomax_with_sample_html(self):
        """Test Lotto Max parsing with sample HTML"""
        sample_html = """
        <html>
        <body>
            <div class="pastWinNum">
                <div class="pastWinNumDate">Dec 20, 2024</div>
                <ul>
                    <li class="pastWinNumber">5</li>
                    <li class="pastWinNumber">12</li>
                    <li class="pastWinNumber">18</li>
                    <li class="pastWinNumber">25</li>
                    <li class="pastWinNumber">33</li>
                    <li class="pastWinNumber">41</li>
                    <li class="pastWinNumber">48</li>
                    <li class="pastWinNumberBonus">Bonus: 15</li>
                </ul>
            </div>
            <div>WCLC lottery winning numbers draw jackpot bonus</div>
        </body>
        </html>
        """
        
        draws = self.scraper.parse_lottomax(sample_html)
        
        self.assertEqual(len(draws), 1)
        self.assertEqual(draws[0]['game'], 'Lotto Max')
        self.assertEqual(draws[0]['numbers'], '5,12,18,25,33,41,48')
        self.assertEqual(draws[0]['bonus'], '15')
    
    def test_parse_western649_with_sample_html(self):
        """Test Western 649 parsing with sample HTML"""
        sample_html = """
        <html>
        <body>
            <div class="pastWinNum">
                <div class="pastWinNumDate">Dec 19, 2024</div>
                <ul>
                    <li class="pastWinNumber">3</li>
                    <li class="pastWinNumber">14</li>
                    <li class="pastWinNumber">22</li>
                    <li class="pastWinNumber">27</li>
                    <li class="pastWinNumber">35</li>
                    <li class="pastWinNumber">46</li>
                    <li class="pastWinNumberBonus">Bonus: 9</li>
                </ul>
            </div>
            <div>WCLC lottery winning numbers draw jackpot bonus</div>
        </body>
        </html>
        """
        
        draws = self.scraper.parse_western649(sample_html)
        
        self.assertEqual(len(draws), 1)
        self.assertEqual(draws[0]['game'], 'Western 649')
        self.assertEqual(draws[0]['numbers'], '3,14,22,27,35,46')
        self.assertEqual(draws[0]['bonus'], '9')
    
    def test_read_html_file_not_found(self):
        """Test reading HTML from non-existent file"""
        with self.assertRaises(WCLCScraperError):
            self.scraper.read_html('nonexistent.html')
    
    def test_read_html_valid_file(self):
        """Test reading HTML from valid file"""
        test_html = "<html><body>WCLC lottery winning numbers draw jackpot bonus</body></html>" * 100
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(test_html)
            temp_file = f.name
        
        try:
            html = self.scraper.read_html(temp_file)
            self.assertEqual(html, test_html)
        finally:
            os.unlink(temp_file)
    
    @patch('requests.Session.get')
    def test_fetch_html_with_retry_success(self, mock_get):
        """Test successful HTML fetching"""
        mock_response = Mock()
        mock_response.text = "<html><body>WCLC lottery winning numbers draw jackpot bonus</body></html>" * 100
        mock_response.headers = {'content-type': 'text/html'}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        html = self.scraper.fetch_html_with_retry('https://test.com')
        self.assertTrue(len(html) > 0)
        mock_get.assert_called_once()
    
    @patch('requests.Session.get')
    def test_fetch_html_with_retry_failure(self, mock_get):
        """Test HTML fetching with all retries failing"""
        mock_get.side_effect = Exception("Network error")
        
        with self.assertRaises(WCLCScraperError):
            self.scraper.fetch_html_with_retry('https://test.com')
        
        self.assertEqual(mock_get.call_count, self.scraper.max_retries)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)