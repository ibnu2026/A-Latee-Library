#!/usr/bin/env python3
"""
Script untuk initialize database dan membuat test data peminjaman terlambat
"""

import sys
sys.path.insert(0, '.')

from LibraryDekstopApp import Database
from datetime import datetime, timedelta

def init_and_create_test():
    """Initialize database dan buat test data"""
    try:
        # Initialize database
        print("📊 Menginitialize database...")
        db = Database("library.db")
        print("✓ Database terinialisasi")
        
        # Get or create member
        c = db.conn.cursor()
        c.execute("SELECT id, nama FROM members LIMIT 1")
        member = c.fetchone()
        
        if not member:
            print("📝 Membuat test member...")
            c.execute('''INSERT INTO members (nama, kamar, rayon, barcode, nis, alamat)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      ("Test Member Terlambat", "101", "Rayon A", "TEST001", "0001", "Test Address"))
            db.conn.commit()
            c.execute("SELECT id, nama FROM members WHERE barcode='TEST001'")
            member = c.fetchone()
            print("✓ Test member berhasil dibuat")
        
        member_id, member_name = member
        print(f"✓ Member: {member_name} (ID: {member_id})")
        
        # Get or create book
        c.execute("SELECT id, judul, stok FROM books WHERE stok > 0 LIMIT 1")
        book = c.fetchone()
        
        if not book:
            print("📚 Membuat test buku...")
            c.execute('''INSERT INTO books (kode_buku, judul, pengarang, penerbit, kategori, stok, status)
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      ("TEST001", "Buku Test Terlambat", "Penulis Test", "Penerbit Test", "Test", 5, "ada"))
            db.conn.commit()
            c.execute("SELECT id, judul, stok FROM books WHERE kode_buku='TEST001'")
            book = c.fetchone()
            print("✓ Test buku berhasil dibuat")
        
        book_id, book_title, stok = book
        print(f"✓ Buku: {book_title} (Stok: {stok})")
        
        # Create overdue borrow
        tanggal_pinjam = (datetime.now() - timedelta(days=10)).isoformat()
        tanggal_kembali = (datetime.now() - timedelta(days=6)).isoformat()
        denda = 6 * 1000  # 6 hari * Rp 1000
        
        print(f"\n📋 Membuat peminjaman terlambat:")
        print(f"  Tanggal Pinjam: {tanggal_pinjam[:10]}")
        print(f"  Tanggal Kembali: {tanggal_kembali[:10]}")
        print(f"  Hari Terlambat: 6 hari")
        print(f"  Denda: Rp {denda:,}")
        
        c.execute('''INSERT INTO borrows (book_id, member_id, tanggal_pinjam, tanggal_kembali, status, denda, diperpanjang)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (book_id, member_id, tanggal_pinjam, tanggal_kembali, 1, denda, 0))
        db.conn.commit()
        
        print("\n✅ Test data peminjaman terlambat berhasil dibuat!")
        print("\n🎯 Untuk testing:")
        print("1. Refresh aplikasi atau buka menu '💰 Denda'")
        print("2. Lihat peminjaman terlambat dengan denda Rp 6.000")
        print("3. Klik kanan → 'Tandai Denda Sudah Dibayar'")
        print("4. Coba scan member ini untuk peminjaman (warning denda akan muncul)")
        
        db.conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Inisialisasi Database & Membuat Test Data ===\n")
    success = init_and_create_test()
    sys.exit(0 if success else 1)
