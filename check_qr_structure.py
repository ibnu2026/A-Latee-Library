#!/usr/bin/env python3
import sqlite3
import os

db_path = os.path.expanduser('~/AppData/Roaming/Latee Library/library_data.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Lihat struktur table pending_qr_codes
print("Tables di database:")
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
for table in c.fetchall():
    print(f"  - {table[0]}")

# Lihat pending_qr_codes
c.execute("PRAGMA table_info(pending_qr_codes)")
print("\nTabel pending_qr_codes:")
for col in c.fetchall():
    print(f"  {col[1]:20} {col[2]}")

# Sample data
c.execute('SELECT * FROM pending_qr_codes LIMIT 1')
r = c.fetchone()
if r:
    print(f"\nSample pending_qr_codes:")
    c.execute("PRAGMA table_info(pending_qr_codes)")
    cols = c.fetchall()
    for i, col in enumerate(cols):
        print(f"  {col[1]:20} = {r[i]}")

conn.close()
