#!/usr/bin/env python3
"""
Test dengan data member sungguhan dari database
"""
import sqlite3
import os
from pathlib import Path

db_path = os.path.expanduser('~/AppData/Roaming/Latee Library/library_data.db')

if not os.path.exists(db_path):
    print(f"❌ Database tidak ditemukan: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
c = conn.cursor()

# Lihat struktur table
c.execute("PRAGMA table_info(members)")
columns = c.fetchall()

print("Struktur table members:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

# Ambil member yang punya barcode
c.execute('SELECT id, nama, kamar, barcode FROM members WHERE barcode IS NOT NULL ORDER BY id DESC LIMIT 1')
result = c.fetchone()
conn.close()

if not result:
    print("\n❌ Tidak ada member dengan barcode")
    exit(1)

member_id, nama, kamar, barcode = result

print("\n" + "=" * 70)
print("MEMBER DARI DATABASE")
print("=" * 70)
print(f"ID      : {member_id}")
print(f"Nama    : {nama}")
print(f"Kamar   : {kamar}")
print(f"Barcode : {barcode}")
print("=" * 70)
