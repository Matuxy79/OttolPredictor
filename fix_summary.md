# Fix Summary: Missing lxml Dependency

## Issue Description
The script was failing with the error:
```
Couldn't find a tree builder with the features you requested: lxml. Do you need to install a parser library?
```

This error occurs when BeautifulSoup is configured to use the 'lxml' parser, but the lxml package is not installed in the Python environment.

## Changes Made

1. **Created requirements.txt file**
   - Added all necessary dependencies with minimum version requirements:
     - beautifulsoup4>=4.9.0
     - lxml>=4.6.0
     - requests>=2.25.0
     - pandas>=1.2.0

2. **Created verify_install.py script**
   - Implemented a verification script that checks if all required dependencies are installed
   - Added specific test for BeautifulSoup with lxml parser
   - Provides clear feedback and instructions for missing dependencies

3. **Updated README.md**
   - Added installation instructions
   - Added usage examples
   - Added troubleshooting section with specific guidance for the lxml error
   - Added information about the verification script

## How to Fix the Issue

To fix the "Couldn't find a tree builder with the features you requested: lxml" error:

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Verify the installation:
   ```
   python verify_install.py
   ```

3. If the lxml package is still missing, install it directly:
   ```
   pip install lxml
   ```

## Why This Works

The script uses BeautifulSoup with the 'lxml' parser in multiple places:
- Line 88: `soup = BeautifulSoup(html, 'lxml')` in parse_lotto649
- Line 150: `soup = BeautifulSoup(html, 'lxml')` in parse_lottomax
- Line 206: `soup = BeautifulSoup(html, 'lxml')` in parse_western649

The lxml parser is preferred over the built-in HTML parser because it's faster and more feature-rich. By installing the lxml package, BeautifulSoup can use this parser as specified in the code.

## Additional Notes

- The requirements.txt file includes version specifications to ensure compatibility
- The verification script provides a way to check the installation before running the main script
- The README.md now includes comprehensive documentation for installation, usage, and troubleshooting