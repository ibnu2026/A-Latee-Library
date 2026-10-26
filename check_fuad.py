#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect(r'C:\Users\Ahmad Ibnu Zaini\AppData\Roaming\Latee Library\library_data.db')
c = conn.cursor()
c.execute("SELECT id, nama, barcode FROM members WHERE nama='Fuad'")
r = c.fetchone()
if r:
    print(f"ID: {r[0]}, Nama: {r[1]}, Barcode: {r[2]}")
    
    # Check if QR exists
    import os
    qr_file = f"qrcodes/{r[2]}.png"
    print(f"QR File: {qr_file}")
    print(f"QR Exists: {os.path.exists(qr_file)}")
