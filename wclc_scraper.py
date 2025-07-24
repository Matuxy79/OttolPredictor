"""
Saskatchewan Lotto Data Extractor - Process lottery draw data from HTML files
Parser for lottery draw data from saved HTML files with comprehensive game support
"""


import os
import sqlite3
import pandas as pd
from datetime import datetime

# All HTML parsing methods and unreachable code fully removed. Only batch historical and GUI/manual entry supported.
    


from typing import List, Dict


class WCLCScraper:
    """
    Saskatchewan Lotto Data Extractor - Handles batch historical and manual/GUI entry data only.
    All HTML scraping and CLI logic removed. Centralized, schema-validating data handling.
    """

    def __init__(self):
        pass

    def deduplicate_draws(self, draws: List[Dict]) -> List[Dict]:
        """Remove duplicate draws based on game, date, and numbers."""
        seen = set()
        unique_draws = []
        duplicates_removed = 0
        for draw in draws:
            key = (draw.get('game'), draw.get('date'), tuple(draw.get('numbers', [])))
            if key not in seen:
                seen.add(key)
                unique_draws.append(draw)
            else:
                duplicates_removed += 1
        if duplicates_removed > 0:
            print(f"Removed {duplicates_removed} duplicate draws during final deduplication")
        return unique_draws

    def save_to_csv(self, data: List[Dict], output_file: str) -> None:
        """Save validated data to CSV file"""
        if not data:
            print("No data to save")
            return
        try:
            df = pd.DataFrame(data)
            # Sort by date (newest first) for better readability
            if 'date' in df.columns:
                # Note: Date sorting might need improvement based on actual date format
                df = df.sort_values('date', ascending=False)
            df.to_csv(output_file, index=False)
            print(f"Saved {len(data)} records to {output_file}")
            # Show preview
            print("\n📊 Data Preview:")
            print(df.head(10))
            print(f"\n✅ Total records: {len(data)}")
            # Show date range
            if len(data) > 1 and 'date' in df.columns:
                first_date = df.iloc[-1]['date']  # Oldest (last in sorted order)
                last_date = df.iloc[0]['date']    # Newest (first in sorted order)
                print(f"📅 Date range: {first_date} to {last_date}")
        except Exception as e:
            raise Exception(f"Error saving to CSV: {e}")

    def save_to_sqlite(self, data: List[Dict], db_file: str, table_name: str = 'lottery_draws') -> None:
        """Save lottery data to SQLite database with proper data type handling"""
        if not data:
            print("No data to save")
            return
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            # Create table with proper schema
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game TEXT NOT NULL,
                    date TEXT,
                    numbers TEXT NOT NULL,  -- JSON string, not list
                    bonus TEXT,
                    gold_ball TEXT,
                    scraped_at TEXT,
                    source_block_index INTEGER
                )
            """)
            # Convert data for database insertion
            import json
            for record in data:
                numbers_json = json.dumps(record.get('numbers', []))
                cursor.execute(f"""
                    INSERT INTO {table_name} 
                    (game, date, numbers, bonus, gold_ball, scraped_at, source_block_index)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.get('game', ''),
                    record.get('date', ''),
                    numbers_json,  # Store as JSON string
                    str(record.get('bonus', '')),
                    str(record.get('gold_ball', '')),
                    record.get('scraped_at', ''),
                    record.get('source_block_index', 0)
                ))
            conn.commit()
            print(f"Saved {len(data)} records to {db_file} (table: {table_name})")
        except Exception as e:
            print(f"Error saving to SQLite: {e}")
            raise Exception(f"Failed to save to SQLite: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

# CLI and HTML input removed. This module now only supports batch historical (pre-processed) and GUI/manual entry data.