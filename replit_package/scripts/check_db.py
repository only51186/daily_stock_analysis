# -*- coding: utf-8 -*-
"""
Check database content
"""

import sqlite3
import pandas as pd

db_path = r'G:\豆包ide\daily_stock_analysis\daily_stock_analysis\data\stock_data.db'

print(f"Checking database: {db_path}")

conn = sqlite3.connect(db_path)

# Get all tables
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("\nTables in database:")
for table in tables:
    print(f"  - {table[0]}")

# Check each table
for table in tables:
    table_name = table[0]
    print(f"\n\n=== Table: {table_name} ===")
    
    # Get schema
    cursor.execute(f"PRAGMA table_info({table_name});")
    schema = cursor.fetchall()
    print("\nSchema:")
    for col in schema:
        print(f"  {col[1]} ({col[2]})")
    
    # Get sample data
    try:
        df = pd.read_sql(f"SELECT * FROM {table_name} LIMIT 5", conn)
        print(f"\nSample data ({len(df)} rows):")
        print(df)
    except Exception as e:
        print(f"Error reading data: {e}")

conn.close()
