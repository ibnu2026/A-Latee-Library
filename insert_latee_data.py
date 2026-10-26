#!/usr/bin/env python3
import sqlite3
from datetime import datetime, timedelta

db_path = r'C:\Users\Ahmad Ibnu Zaini\AppData\Roaming\Latee Library\library_data.db'

conn = sqlite3.connect(db_path)
c = conn.cursor()

# Clear old test data
c.execute("DELETE FROM borrows WHERE member_id IN (SELECT id FROM members WHERE nama LIKE '%Test%')")
c.execute("DELETE FROM books WHERE judul LIKE '%Test%'")
c.execute("DELETE FROM members WHERE nama LIKE '%Test%'")
conn.commit()
print("✓ Old data cleared")

# Insert member
c.execute('INSERT INTO members (nama, rayon, kamar, barcode) VALUES (?, ?, ?, ?)',
          ('Test Member Terlambat', 'Rayon A', '101', 'TEST001'))
conn.commit()
member_id = c.lastrowid
print(f"✓ Member: ID={member_id}")

# Insert book
c.execute('INSERT INTO books (judul, kode_buku, kategori, barcode, stok) VALUES (?, ?, ?, ?, ?)',
          ('Buku Test Terlambat', 'TEST001', 'Test', 'BOOK_TEST001', 5))
conn.commit()
book_id = c.lastrowid
print(f"✓ Book: ID={book_id}")

# Insert borrow with denda
tanggal_pinjam = (datetime.now() - timedelta(days=10)).isoformat()
tanggal_kembali = (datetime.now() - timedelta(days=6)).isoformat()

c.execute('''INSERT INTO borrows (book_id, member_id, tanggal_pinjam, tanggal_kembali, status, denda)
             VALUES (?, ?, ?, ?, ?, ?)''',
          (book_id, member_id, tanggal_pinjam, tanggal_kembali, 1, 6000))
conn.commit()
print(f"✓ Borrow: Denda=Rp 6000")

# Verify
c.execute('''SELECT b.id, m.nama, b.denda FROM borrows b
             LEFT JOIN members m ON b.member_id = m.id WHERE b.denda > 0''')
result = c.fetchall()
print(f"\n✅ Test data inserted - {len(result)} fines:")
for row in result:
    print(f"   Borrow {row[0]}: {row[1]} - Rp {row[2]}")

conn.close()
