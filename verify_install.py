"""
Dependency verification script for Saskatchewan Lotto Scraper
This script checks if all required dependencies are installed correctly.
"""

import sys
import importlib
import pkg_resources
import platform

def check_dependency(package_name, min_version=None):
    """Check if a package is installed and meets minimum version requirements."""
    try:
        # Try to import the package
        module = importlib.import_module(package_name)

        # Special case for beautifulsoup4 which is imported as 'bs4'
        if package_name == 'beautifulsoup4':
            package_name = 'bs4'

        # Get installed version
        version = pkg_resources.get_distribution(package_name).version

        # Check version if minimum is specified
        if min_version and pkg_resources.parse_version(version) < pkg_resources.parse_version(min_version):
            print(f"❌ {package_name} version {version} is installed, but version {min_version} or higher is required")
            return False

        print(f"✅ {package_name} {version} is installed")
        return True

    except ImportError:
        print(f"❌ {package_name} is not installed")
        return False
    except Exception as e:
        print(f"❌ Error checking {package_name}: {e}")
        return False

def check_python_version():
    """Check if the Python version is compatible."""
    python_version = platform.python_version()
    major, minor, _ = map(int, python_version.split('.'))

    if major == 3 and (minor >= 11):
        print(f"✅ Python {python_version} is compatible")
        return True
    else:
        print(f"❌ Python {python_version} is not compatible. Please use Python 3.11 or higher")
        return False

def check_lxml_parser():
    """Specifically check if BeautifulSoup can use the lxml parser."""
    try:
        from bs4 import BeautifulSoup
        # Try to create a simple soup object with lxml parser
        soup = BeautifulSoup("<html><body>Test</body></html>", "lxml")
        print("✅ BeautifulSoup can use the lxml parser")
        return True
    except ImportError:
        print("❌ BeautifulSoup is not installed")
        return False
    except Exception as e:
        print(f"❌ BeautifulSoup cannot use the lxml parser: {e}")
        return False

def main():
    print("Checking dependencies for Saskatchewan Lotto Scraper...\n")

    # Check Python version first
    print("Checking Python version:")
    python_compatible = check_python_version()

    if not python_compatible:
        print("\nSummary:")
        print("❌ Python version is not compatible.")
        print("Please use Python 3.11 or higher as specified in the requirements.")
        print("See README.rst for installation instructions.")
        return 1

    # Define required packages with minimum versions
    dependencies = {
        'beautifulsoup4': '4.9.0',
        'lxml': '4.6.0',
        'requests': '2.25.0',
        'pandas': '1.2.0',
        'numpy': '1.19.0',
        'PyQt5': '5.15.0',
        'matplotlib': '3.3.0'
    }

    all_installed = True

    # Check each dependency
    for package, min_version in dependencies.items():
        if not check_dependency(package, min_version):
            all_installed = False

    # Specifically check if BeautifulSoup can use lxml parser
    print("\nVerifying BeautifulSoup with lxml parser:")
    if not check_lxml_parser():
        all_installed = False

    # Summary
    print("\nSummary:")
    if all_installed:
        print("✅ All dependencies are correctly installed!")
        print("You can now run the main script with:")
        print("  python main.py --url <lottery_url> --game <game_type>")
    else:
        print("❌ Some dependencies are missing or have incorrect versions.")
        print("Please install the required dependencies with:")
        print("  pip install -r requirements.txt")

    return 0 if all_installed else 1

if __name__ == "__main__":
    sys.exit(main())
