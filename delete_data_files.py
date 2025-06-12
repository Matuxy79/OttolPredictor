#!/usr/bin/env python
"""
Simple script to delete all existing scraped data files.
This script has no external dependencies and can be run in any Python environment.
"""

import os
import glob
import sys

def delete_existing_data_files():
    """Delete all existing scraped data CSV files"""
    # List of patterns to match data files
    patterns = [
        "649_results_*.csv",
        "wclc_*_results_*.csv",
        "test_fix.csv"
    ]
    
    deleted_files = []
    
    for pattern in patterns:
        files = glob.glob(pattern)
        for file in files:
            try:
                os.remove(file)
                deleted_files.append(file)
                print(f"Deleted file: {file}")
            except Exception as e:
                print(f"Error deleting file {file}: {e}")
    
    return deleted_files

def main():
    """Main function to delete all data files"""
    print("=" * 80)
    print("DELETING ALL EXISTING SCRAPED DATA FILES")
    print("=" * 80)
    
    deleted_files = delete_existing_data_files()
    
    print("\nSummary:")
    print(f"Total files deleted: {len(deleted_files)}")
    
    if deleted_files:
        print("\nDeleted files:")
        for file in deleted_files:
            print(f"- {file}")
    else:
        print("\nNo files were deleted.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())