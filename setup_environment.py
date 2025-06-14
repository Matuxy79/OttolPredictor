"""
Setup Environment Script for Saskatoon Lotto Predictor

This script provides options for setting up the Python environment for the Saskatoon Lotto Predictor
project using either conda or pip.

Usage:
    python setup_environment.py [--conda | --pip]

Options:
    --conda    Set up the environment using conda (recommended)
    --pip      Set up the environment using pip

If no option is specified, the script will provide instructions for both methods.
"""

import os
import sys
import subprocess
import platform

def check_command_exists(command):
    """Check if a command exists on the system."""
    try:
        subprocess.run(
            [command, "--version"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            check=False
        )
        return True
    except FileNotFoundError:
        return False

def setup_conda_environment():
    """Set up the conda environment using environment.yml."""
    print("\n=== Setting up conda environment ===\n")
    
    # Check if conda is installed
    if not check_command_exists("conda"):
        print("Error: conda is not installed or not in the PATH.")
        print("Please install Anaconda or Miniconda first:")
        print("https://docs.conda.io/en/latest/miniconda.html")
        return False
    
    # Check if environment.yml exists
    if not os.path.exists("environment.yml"):
        print("Error: environment.yml file not found.")
        return False
    
    try:
        # Create the conda environment
        print("Creating conda environment 'ottolpredictor'...")
        subprocess.run(
            ["conda", "env", "create", "-f", "environment.yml"],
            check=True
        )
        
        # Provide activation instructions
        print("\nEnvironment setup complete!")
        print("\nTo activate the environment, run:")
        if platform.system() == "Windows":
            print("    conda activate ottolpredictor")
        else:
            print("    conda activate ottolpredictor")
        
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"Error setting up conda environment: {e}")
        return False

def setup_pip_environment():
    """Set up the environment using pip and requirements.txt."""
    print("\n=== Setting up pip environment ===\n")
    
    # Check if pip is installed
    if not check_command_exists("pip"):
        print("Error: pip is not installed or not in the PATH.")
        print("Please install pip first.")
        return False
    
    # Check if requirements.txt exists
    if not os.path.exists("requirements.txt"):
        print("Error: requirements.txt file not found.")
        return False
    
    try:
        # Install requirements
        print("Installing requirements...")
        subprocess.run(
            ["pip", "install", "-r", "requirements.txt"],
            check=True
        )
        
        print("\nEnvironment setup complete!")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"Error installing requirements: {e}")
        return False

def verify_installation():
    """Verify that the environment is set up correctly."""
    print("\n=== Verifying installation ===\n")
    
    # Create a temporary script to test imports
    test_script = """
import sys
import importlib

required_packages = [
    'beautifulsoup4',
    'requests',
    'lxml',
    'pandas',
    'numpy',
    'PyQt5',
    'matplotlib',
    'pdfplumber',
    'ruptures',
    'hmmlearn',
    'statsmodels',
    'scikit-learn'
]

missing_packages = []

for package in required_packages:
    try:
        importlib.import_module(package)
        print(f"✓ {package}")
    except ImportError:
        missing_packages.append(package)
        print(f"✗ {package}")

if missing_packages:
    print("\\nThe following packages are missing:")
    for package in missing_packages:
        print(f"  - {package}")
    sys.exit(1)
else:
    print("\\nAll required packages are installed!")
    sys.exit(0)
"""
    
    with open("verify_install.py", "w") as f:
        f.write(test_script)
    
    try:
        # Run the verification script
        subprocess.run(
            [sys.executable, "verify_install.py"],
            check=True
        )
        return True
    except subprocess.CalledProcessError:
        return False
    finally:
        # Clean up
        if os.path.exists("verify_install.py"):
            os.remove("verify_install.py")

def print_instructions():
    """Print instructions for setting up the environment."""
    print("\n=== Saskatoon Lotto Predictor Environment Setup ===\n")
    print("This script helps you set up the Python environment for the Saskatoon Lotto Predictor project.")
    print("\nYou have two options for setting up the environment:")
    
    print("\n1. Using conda (recommended):")
    print("   This will create a new conda environment with all required dependencies.")
    print("   Run: python setup_environment.py --conda")
    
    print("\n2. Using pip:")
    print("   This will install all required packages in your current Python environment.")
    print("   Run: python setup_environment.py --pip")
    
    print("\nFor manual setup:")
    
    print("\nConda setup:")
    print("   conda env create -f environment.yml")
    print("   conda activate ottolpredictor")
    
    print("\nPip setup:")
    print("   pip install -r requirements.txt")

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print_instructions()
        return
    
    if sys.argv[1] == "--conda":
        if setup_conda_environment():
            print("\nTo verify the installation, activate the environment and run:")
            print("    python verify_install.py")
    
    elif sys.argv[1] == "--pip":
        if setup_pip_environment():
            verify_installation()
    
    else:
        print(f"Unknown option: {sys.argv[1]}")
        print_instructions()

if __name__ == "__main__":
    main()