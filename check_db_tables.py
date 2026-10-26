#!/usr/bin/env python3
"""Check database table structure"""
import sqlite3

DB_PATH = "library_data.db"

try:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = c.fetchall()
    print("[DB] Tables in database:")
    for table in tables:
        print(f"  - {table[0]}")
    
    # Check if visitors table exists
    if ('visitors',) in tables:
        print("\n[OK] 'visitors' table exists")
        c.execute("PRAGMA table_info(visitors)")
        cols = c.fetchall()
        print("  Columns:")
        for col in cols:
            print(f"    - {col[1]} ({col[2]})")
    else:
        print("\n[WARN] 'visitors' table does NOT exist - will be created on application startup")
    
    conn.close()
except Exception as e:
    print(f"[ERROR] {e}")
