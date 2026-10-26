#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import os
from pathlib import Path

# Setup
cards_dir = "cards"
qrcodes_dir = "qrcodes"

# Database
db_path = os.path.expanduser("~/AppData/Roaming/Latee Library/library_data.db")

print("=" * 60)
print("INFO: Members dan Barcodes di Database")
print("=" * 60)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT id, nama, nis, kamar, barcode FROM members ORDER BY id")
members = cursor.fetchall()
conn.close()

for member_id, nama, nis, kamar, barcode in members:
    qr_file = f"{barcode}.png" if barcode else "N/A"
    has_qr = os.path.exists(os.path.join(qrcodes_dir, qr_file)) if barcode else False
    print(f"ID {member_id:2d} | {nama:25s} | Barcode: {barcode or 'NONE':20s} | QR: {'✓' if has_qr else '✗'}")

print()
print("=" * 60)
print("QR Files yang ada di folder qrcodes/:")
print("=" * 60)
qr_files = sorted([f.replace('.png', '') for f in os.listdir(qrcodes_dir)])
for qr_barcode in qr_files:
    # Try to find member with this barcode
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nama FROM members WHERE barcode = ?", (qr_barcode,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        member_id, nama = result
        print(f"✓ {qr_barcode} → Member ID {member_id} ({nama})")
    else:
        print(f"⊘ {qr_barcode} → Member tidak ditemukan")
