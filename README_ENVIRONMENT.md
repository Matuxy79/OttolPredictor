# Python Environment Setup for Saskatoon Lotto Predictor

This document provides instructions for setting up the Python environment required to run the Saskatoon Lotto Predictor application.

## Requirements

- Python 3.11 or 3.12
- pip or conda package manager

## Option 1: Automated Setup (Recommended)

The project includes a setup script that can automatically set up your environment.

### Using the Setup Script

1. Open a terminal or command prompt
2. Navigate to the project directory
3. Run the setup script with one of the following options:

```bash
# For conda setup (recommended)
python setup_environment.py --conda

# For pip setup
python setup_environment.py --pip
```

4. Follow the on-screen instructions

## Option 2: Manual Setup

### Using Conda (Recommended)

1. Make sure you have Anaconda or Miniconda installed
2. Open a terminal or command prompt
3. Navigate to the project directory
4. Create the environment from the environment.yml file:

```bash
conda env create -f environment.yml
```

5. Activate the environment:

```bash
conda activate ottolpredictor
```

### Using Pip

1. Make sure you have Python and pip installed
2. Open a terminal or command prompt
3. Navigate to the project directory
4. Install the required packages:

```bash
pip install -r requirements.txt
```

## Verifying the Installation

To verify that all required packages are installed correctly, run:

```bash
python verify_install.py
```

This script will check if all required packages can be imported and will report any missing packages.

## Required Packages

The following packages are required to run the application:

- beautifulsoup4>=4.9.0
- requests>=2.25.0
- lxml>=4.6.0
- pandas>=1.2.0
- numpy>=1.19.0
- PyQt5>=5.15.0
- matplotlib>=3.3.0
- pdfplumber>=0.7.0
- ruptures>=1.1.0
- hmmlearn>=0.2.8
- statsmodels>=0.14.0
- scikit-learn>=1.3.0

## Troubleshooting

### Common Issues

1. **Missing packages after installation**
   - Try reinstalling the package manually: `pip install <package_name>`
   - Check if the package has a different import name

2. **Conda environment creation fails**
   - Update conda: `conda update -n base -c defaults conda`
   - Try creating the environment with specific channels: `conda env create -f environment.yml -c conda-forge`

3. **PyQt5 installation issues**
   - On some systems, PyQt5 might need to be installed separately: `pip install PyQt5`
   - On Linux, you might need additional system packages: `sudo apt-get install python3-pyqt5`

4. **Import errors when running the application**
   - Make sure you've activated the conda environment: `conda activate ottolpredictor`
   - Check if all packages are installed: `python verify_install.py`

### Getting Help

If you encounter any issues with the environment setup, please:

1. Check the error messages for specific package issues
2. Verify that your Python version is compatible (3.11 or 3.12)
3. Make sure you have the latest version of pip or conda
4. Try installing the problematic package manually