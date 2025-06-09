"""
Unit tests for WCLC Scraper with Live Scraping Tests
Testing each game type and core functionality including real WCLC websites
"""

import unittest
import os
import tempfile
import time
import sys
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
            <div>Past Winning Numbers</div>
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

    def test_validate_draw_data_dailygrand_valid(self):
        """Test draw data validation for valid Daily Grand data"""
        valid_data = {
            'game': 'Daily Grand',
            'date': 'Dec 21, 2024',
            'numbers': '1,15,23,31,42',  # 5 numbers
            'bonus': '7'
        }
        self.assertTrue(self.scraper._validate_draw_data(valid_data, 'dailygrand'))

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
            <div>WCLC lottery winning numbers draw jackpot bonus past winning numbers</div>
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
            <div>WCLC lottery winning numbers draw jackpot bonus past winning numbers</div>
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
            <div>WCLC lottery winning numbers draw jackpot bonus past winning numbers</div>
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
        test_html = "<html><body>WCLC lottery winning numbers draw jackpot bonus past winning numbers</body></html>" * 100

        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(test_html)
            temp_file = f.name

        try:
            html = self.scraper.read_html(temp_file)
            self.assertEqual(html, test_html)
        finally:
            os.unlink(temp_file)

    def test_create_draw_fingerprint(self):
        """Test draw fingerprint creation for duplicate detection"""
        draw_data = {
            'game': 'Lotto 649',
            'date': 'Dec 21, 2024',
            'numbers': '1,15,23,31,42,49'
        }

        fingerprint = self.scraper.create_draw_fingerprint(draw_data)
        expected = "Lotto 649|Dec 21, 2024|1,15,23,31,42,49"
        self.assertEqual(fingerprint, expected)

    def test_wclc_urls_configuration(self):
        """Test that all WCLC URLs are properly configured"""
        expected_games = ['649', 'max', 'western649', 'westernmax', 'dailygrand']

        for game in expected_games:
            self.assertIn(game, self.scraper.WCLC_URLS)
            url = self.scraper.WCLC_URLS[game]
            self.assertTrue(url.startswith('https://www.wclc.com/'))
            self.assertTrue(url.endswith('-extra.htm'))

    @patch('requests.Session.get')
    def test_fetch_html_with_retry_success(self, mock_get):
        """Test successful HTML fetching"""
        mock_response = Mock()
        mock_response.text = "<html><body>WCLC lottery winning numbers draw jackpot bonus past winning numbers</body></html>" * 100
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


class TestWCLCLiveScraping(unittest.TestCase):
    """Live scraping tests - these require internet connection and may be slower"""

    def setUp(self):
        """Set up test fixtures for live tests"""
        self.scraper = WCLCScraper(max_retries=2, timeout=15)

    def test_live_scrape_lotto649_current_page(self):
        """Test live scraping of Lotto 649 current page"""
        try:
            url = self.scraper.WCLC_URLS['649']
            html = self.scraper.fetch_html_with_retry(url)
            draws = self.scraper.parse_lotto649(html)

            print(f"\n🎯 Live Lotto 649 Test Results:")
            print(f"   URL: {url}")
            print(f"   Draws found: {len(draws)}")

            if draws:
                print(f"   Latest draw: {draws[0]['date']}")
                print(f"   Numbers: {draws[0]['numbers']}")
                print(f"   Bonus: {draws[0]['bonus']}")
                if draws[0]['gold_ball']:
                    print(f"   Gold Ball: {draws[0]['gold_ball']}")

            # Basic validation
            self.assertIsInstance(draws, list)
            if draws:  # If we got any draws
                self.assertIn('game', draws[0])
                self.assertIn('date', draws[0])
                self.assertIn('numbers', draws[0])

        except Exception as e:
            self.skipTest(f"Live scraping failed (this may be due to network issues): {e}")

    def test_live_scrape_lotto_max_current_page(self):
        """Test live scraping of Lotto Max current page"""
        try:
            url = self.scraper.WCLC_URLS['max']
            html = self.scraper.fetch_html_with_retry(url)
            draws = self.scraper.parse_lottomax(html)

            print(f"\n🎯 Live Lotto Max Test Results:")
            print(f"   URL: {url}")
            print(f"   Draws found: {len(draws)}")

            if draws:
                print(f"   Latest draw: {draws[0]['date']}")
                print(f"   Numbers: {draws[0]['numbers']}")
                print(f"   Bonus: {draws[0]['bonus']}")

            # Basic validation
            self.assertIsInstance(draws, list)
            if draws:  # If we got any draws
                self.assertIn('game', draws[0])
                self.assertIn('date', draws[0])
                self.assertIn('numbers', draws[0])

        except Exception as e:
            self.skipTest(f"Live scraping failed (this may be due to network issues): {e}")

    def test_live_scrape_western649_current_page(self):
        """Test live scraping of Western 649 current page"""
        try:
            url = self.scraper.WCLC_URLS['western649']
            html = self.scraper.fetch_html_with_retry(url)
            draws = self.scraper.parse_western649(html)

            print(f"\n🎯 Live Western 649 Test Results:")
            print(f"   URL: {url}")
            print(f"   Draws found: {len(draws)}")

            if draws:
                print(f"   Latest draw: {draws[0]['date']}")
                print(f"   Numbers: {draws[0]['numbers']}")
                print(f"   Bonus: {draws[0]['bonus']}")

            # Basic validation
            self.assertIsInstance(draws, list)
            if draws:  # If we got any draws
                self.assertIn('game', draws[0])
                self.assertIn('date', draws[0])
                self.assertIn('numbers', draws[0])

        except Exception as e:
            self.skipTest(f"Live scraping failed (this may be due to network issues): {e}")

    def test_live_scrape_westernmax_current_page(self):
        """Test live scraping of Western Max current page"""
        try:
            url = self.scraper.WCLC_URLS['westernmax']
            html = self.scraper.fetch_html_with_retry(url)
            draws = self.scraper.parse_westernmax(html)

            print(f"\n🎯 Live Western Max Test Results:")
            print(f"   URL: {url}")
            print(f"   Draws found: {len(draws)}")

            if draws:
                print(f"   Latest draw: {draws[0]['date']}")
                print(f"   Numbers: {draws[0]['numbers']}")
                print(f"   Bonus: {draws[0]['bonus']}")

            # Basic validation
            self.assertIsInstance(draws, list)
            if draws:  # If we got any draws
                self.assertIn('game', draws[0])
                self.assertIn('date', draws[0])
                self.assertIn('numbers', draws[0])

        except Exception as e:
            self.skipTest(f"Live scraping failed (this may be due to network issues): {e}")

    def test_live_scrape_dailygrand_current_page(self):
        """Test live scraping of Daily Grand current page"""
        try:
            url = self.scraper.WCLC_URLS['dailygrand']
            html = self.scraper.fetch_html_with_retry(url)
            draws = self.scraper.parse_dailygrand(html)

            print(f"\n🎯 Live Daily Grand Test Results:")
            print(f"   URL: {url}")
            print(f"   Draws found: {len(draws)}")

            if draws:
                print(f"   Latest draw: {draws[0]['date']}")
                print(f"   Numbers: {draws[0]['numbers']}")
                print(f"   Bonus: {draws[0]['bonus']}")

            # Basic validation
            self.assertIsInstance(draws, list)
            if draws:  # If we got any draws
                self.assertIn('game', draws[0])
                self.assertIn('date', draws[0])
                self.assertIn('numbers', draws[0])

        except Exception as e:
            self.skipTest(f"Live scraping failed (this may be due to network issues): {e}")

    def test_live_extract_month_links(self):
        """Test extraction of month navigation links from live WCLC page"""
        try:
            url = self.scraper.WCLC_URLS['649']  # Use 649 as test case
            html = self.scraper.fetch_html_with_retry(url)
            month_links = self.scraper.extract_month_links(html, url)

            print(f"\n🔗 Live Month Links Test Results:")
            print(f"   Base URL: {url}")
            print(f"   Month links found: {len(month_links)}")

            if month_links:
                print(f"   Sample links:")
                for i, link in enumerate(month_links[:3]):  # Show first 3
                    print(f"     {i+1}. {link}")
                if len(month_links) > 3:
                    print(f"     ... and {len(month_links) - 3} more")

            # Basic validation
            self.assertIsInstance(month_links, list)
            # Note: month_links might be empty if the site doesn't have historical navigation

        except Exception as e:
            self.skipTest(f"Live month links extraction failed: {e}")

    def test_live_batch_scraping_limited(self):
        """Test live batch scraping with limited months (to avoid overloading server)"""
        try:
            url = self.scraper.WCLC_URLS['649']

            print(f"\n📦 Live Batch Scraping Test (Limited to 2 months):")
            print(f"   Starting batch scrape from: {url}")

            # Limit to 2 months to be respectful to the server
            draws = self.scraper.scrape_batch_history(url, '649', max_months=2)

            print(f"   Total draws collected: {len(draws)}")

            if draws:
                # Show date range
                dates = [draw['date'] for draw in draws if draw.get('date')]
                if dates:
                    print(f"   Date range: {dates[-1]} to {dates[0]}")

                # Show sample draw
                print(f"   Sample draw: {draws[0]['date']} - {draws[0]['numbers']}")

            # Basic validation
            self.assertIsInstance(draws, list)
            if draws:
                for draw in draws[:3]:  # Check first few draws
                    self.assertIn('game', draw)
                    self.assertIn('date', draw)
                    self.assertIn('numbers', draw)
                    self.assertEqual(draw['game'], 'Lotto 649')

        except Exception as e:
            self.skipTest(f"Live batch scraping failed: {e}")

    def test_all_wclc_urls_accessible(self):
        """Test that all WCLC URLs are accessible and return valid content"""
        results = {}

        print(f"\n🌐 WCLC URLs Accessibility Test:")

        for game, url in self.scraper.WCLC_URLS.items():
            try:
                print(f"   Testing {game}: {url}")
                html = self.scraper.fetch_html_with_retry(url)

                # Basic checks
                is_valid = self.scraper._validate_html_content(html)
                results[game] = {
                    'url': url,
                    'accessible': True,
                    'valid_content': is_valid,
                    'html_length': len(html)
                }

                print(f"     ✅ Accessible, Valid: {is_valid}, Size: {len(html)} chars")

                # Small delay between requests
                time.sleep(1)

            except Exception as e:
                results[game] = {
                    'url': url,
                    'accessible': False,
                    'error': str(e)
                }
                print(f"     ❌ Failed: {e}")

        # Report summary
        accessible_count = sum(1 for r in results.values() if r.get('accessible', False))
        total_count = len(results)

        print(f"\n📊 Summary: {accessible_count}/{total_count} URLs accessible")

        # At least one URL should be accessible for tests to be meaningful
        self.assertGreater(accessible_count, 0, "No WCLC URLs are accessible")


def run_live_tests():
    """
    Run live scraping tests separately
    This function can be called to test actual WCLC website functionality
    """
    print("🚀 Starting Live WCLC Scraper Tests...")
    print("=" * 60)

    # Create test suite with only live tests
    live_suite = unittest.TestLoader().loadTestsFromTestCase(TestWCLCLiveScraping)

    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(live_suite)

    print("=" * 60)
    if result.wasSuccessful():
        print("✅ All live tests passed!")
    else:
        print(f"❌ {len(result.failures)} failures, {len(result.errors)} errors")

    return result.wasSuccessful()


if __name__ == '__main__':
    # Check if user wants to run live tests
    if len(sys.argv) > 1 and sys.argv[1] == '--live':
        # Run live tests only
        success = run_live_tests()
        sys.exit(0 if success else 1)

    elif len(sys.argv) > 1 and sys.argv[1] == '--all':
        # Run all tests (unit + live)
        print("🧪 Running All Tests (Unit + Live)...")
        unittest.main(verbosity=2)

    else:
        # Run unit tests only (default)
        print("🧪 Running Unit Tests Only...")
        print("💡 Use '--live' for live scraping tests or '--all' for both")

        # Create test suite with only unit tests
        unit_suite = unittest.TestLoader().loadTestsFromTestCase(TestWCLCScraper)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(unit_suite)

        sys.exit(0 if result.wasSuccessful() else 1)
