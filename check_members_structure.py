#!/usr/bin/env python3
import sqlite3
import os

db_path = os.path.expanduser('~/AppData/Roaming/Latee Library/library_data.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Lihat struktur table members
c.execute("PRAGMA table_info(members)")
print("\nTabel members:")
for col in c.fetchall():
    print(f"  {col[1]:20} {col[2]}")

# Ambil sample member
c.execute('SELECT * FROM members WHERE barcode IS NOT NULL LIMIT 1')
r = c.fetchone()
if r:
    print(f"\nSample member (full):")
    c.execute("PRAGMA table_info(members)")
    cols = c.fetchall()
    for i, col in enumerate(cols):
        print(f"  {col[1]:20} = {r[i]}")

conn.close()
