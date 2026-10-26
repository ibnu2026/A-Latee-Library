#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import os
from pathlib import Path

# Setup
cards_dir = "cards"
qrcodes_dir = "qrcodes"
os.makedirs(cards_dir, exist_ok=True)

# Database
db_path = os.path.expanduser("~/AppData/Roaming/Latee Library/library_data.db")

print("=" * 60)
print("BATCH CREATE CARDS - Generate kartu untuk semua QR codes")
print("=" * 60)
print()

# Import database class
import sys
sys.path.insert(0, os.getcwd())
from LibraryDekstopApp import Database

db = Database()

# Get all members
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT id, nama, nis, kamar, barcode FROM members ORDER BY id")
members = cursor.fetchall()
conn.close()

created = 0
skipped = 0

for member_id, nama, nis, kamar, barcode in members:
    if not barcode:
        print(f"⊘ ID {member_id} ({nama}): Tidak ada barcode")
        continue
    
    qr_file = os.path.join(qrcodes_dir, f"{barcode}.png")
    card_file = os.path.join(cards_dir, f"{nama}_{barcode}.jpg")
    
    if not os.path.exists(qr_file):
        print(f"⊘ ID {member_id} ({nama}): QR file tidak ada ({qr_file})")
        continue
    
    if os.path.exists(card_file):
        print(f"✓ ID {member_id} ({nama}): Kartu sudah ada")
        skipped += 1
        continue
    
    # Create card
    card_path = db.create_member_card_with_design(nama, barcode, kamar or "", qr_file)
    if card_path:
        size_kb = os.path.getsize(card_path) / 1024
        print(f"✓ ID {member_id} ({nama}): Kartu dibuat ({size_kb:.1f} KB)")
        created += 1
    else:
        print(f"✗ ID {member_id} ({nama}): Gagal membuat kartu")

print()
print("=" * 60)
print(f"✅ Selesai!")
print(f"   Kartu baru: {created}")
print(f"   Kartu sudah ada: {skipped}")
print("=" * 60)
