#!/usr/bin/env python3
"""
Script untuk INSERT test data denda langsung ke AppData database
Jalankan sebelum aplikasi restart
"""
import sqlite3
import os
from datetime import datetime, timedelta

# AppData database path
appdata_path = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "LibraryApp")
os.makedirs(appdata_path, exist_ok=True)
db_path = os.path.join(appdata_path, "library_data.db")

print(f"📊 Connecting to: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Clear existing test data
    c.execute("DELETE FROM borrows WHERE member_id = (SELECT id FROM members WHERE nama = 'Test Member Denda')")
    c.execute("DELETE FROM books WHERE judul = 'Test Book Denda'")
    c.execute("DELETE FROM members WHERE nama = 'Test Member Denda'")
    conn.commit()
    print("✓ Cleared old test data")
    
    # Insert member
    c.execute("INSERT INTO members (nama, rayon, kamar, barcode) VALUES (?, ?, ?, ?)",
              ("Test Member Denda", "Rayon A", "101", "TEST_DENDA_001"))
    conn.commit()
    member_id = c.lastrowid
    print(f"✓ Member inserted: ID={member_id}")
    
    # Insert book
    c.execute("INSERT INTO books (judul, kode_buku, kategori, barcode, stok) VALUES (?, ?, ?, ?, ?)",
              ("Test Book Denda", "TEST_DENDA", "Test", "BOOK_TEST_001", 5))
    conn.commit()
    book_id = c.lastrowid
    print(f"✓ Book inserted: ID={book_id}")
    
    # Insert borrow dengan denda
    tanggal_pinjam = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S.%f")
    tanggal_kembali = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%dT%H:%M:%S.%f")
    denda = 6000  # 6 hari × Rp 1000
    
    c.execute("""INSERT INTO borrows (book_id, member_id, tanggal_pinjam, tanggal_kembali, status, denda) 
                 VALUES (?, ?, ?, ?, ?, ?)""",
              (book_id, member_id, tanggal_pinjam, tanggal_kembali, 1, denda))
    conn.commit()
    borrow_id = c.lastrowid
    print(f"✓ Borrow inserted: ID={borrow_id}, Denda=Rp {denda}")
    
    # Verify
    c.execute("""SELECT b.id, m.nama, b.denda FROM borrows b 
                 JOIN members m ON b.member_id = m.id 
                 WHERE b.denda > 0""")
    result = c.fetchall()
    print(f"\n✅ Verification: Found {len(result)} unpaid fines")
    for row in result:
        print(f"   - Borrow ID {row[0]}: {row[1]} - Rp {row[2]}")
    
    conn.close()
    print("\n✅ Test data inserted successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
