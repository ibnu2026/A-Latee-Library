#!/usr/bin/env python3
"""
Script untuk membuat test data peminjaman yang sudah lewat batas (terlambat)
Untuk testing fitur denda peminjaman terlambat
"""

import sqlite3
from datetime import datetime, timedelta
import sys

def create_overdue_borrow():
    """Buat data peminjaman terlambat untuk testing"""
    try:
        # Connect to database
        db_path = "library.db"
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Check if members exist, if not create test member
        c.execute("SELECT COUNT(*) FROM members")
        member_count = c.fetchone()[0]
        
        if member_count == 0:
            print("📝 Membuat test member...")
            c.execute('''INSERT INTO members (nama, kamar, rayon, barcode, tanggal_daftar)
                         VALUES (?, ?, ?, ?, ?)''',
                      ("Test Member Terlambat", "101", "Rayon A", "TEST001", datetime.now().isoformat()))
            conn.commit()
            print("✓ Test member berhasil dibuat")
        
        # Get member
        c.execute("SELECT id, nama, kamar, rayon FROM members LIMIT 1")
        member = c.fetchone()
        if not member:
            print("❌ Error: Gagal membuat/ambil data members!")
            return False
        
        member_id, member_name, member_kamar, member_rayon = member
        print(f"\n✓ Anggota: {member_name} (Rayon: {member_rayon}, Kamar: {member_kamar})")
        
        # Check if books exist, if not create test book
        c.execute("SELECT COUNT(*) FROM books WHERE stok > 0")
        book_count = c.fetchone()[0]
        
        if book_count == 0:
            print("📚 Membuat test buku...")
            c.execute('''INSERT INTO books (kode_buku, judul, pengarang, penerbit, stok, status, tgl_masuk)
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      ("TEST001", "Buku Test Terlambat", "Penulis Test", "Penerbit Test", 5, "ada", datetime.now().isoformat()))
            conn.commit()
            print("✓ Test buku berhasil dibuat")
        
        # Get book with stok
        c.execute("SELECT id, judul, stok FROM books WHERE stok > 0 LIMIT 1")
        book = c.fetchone()
        if not book:
            print("❌ Error: Tidak ada buku yang tersedia!")
            return False
        
        book_id, book_title, stok = book
        print(f"✓ Buku: {book_title} (Stok: {stok})")
        
        # Create overdue borrow record
        # Set tanggal_pinjam 10 hari yang lalu (melebihi batas 4 hari = 6 hari terlambat)
        tanggal_pinjam = (datetime.now() - timedelta(days=10)).isoformat()
        tanggal_kembali = (datetime.now() - timedelta(days=6)).isoformat()  # Kembali 6 hari terlambat
        
        # Hitung denda: 6 hari * Rp 1000 = Rp 6000
        denda = 6 * 1000
        
        print(f"\n📋 Data Peminjaman Terlambat:")
        print(f"  Tanggal Pinjam: {tanggal_pinjam[:10]}")
        print(f"  Tanggal Kembali: {tanggal_kembali[:10]}")
        print(f"  Hari Terlambat: 6 hari")
        print(f"  Denda: Rp {denda:,}")
        
        # Insert ke database
        c.execute('''INSERT INTO borrows (book_id, member_id, tanggal_pinjam, tanggal_kembali, status, denda, diperpanjang)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (book_id, member_id, tanggal_pinjam, tanggal_kembali, 1, denda, 0))
        
        # Kurangi stok jika sudah dipinjam
        c.execute("SELECT stok FROM books WHERE id=?", (book_id,))
        current_stok = c.fetchone()[0]
        if current_stok > 0:
            c.execute("UPDATE books SET stok=stok-1 WHERE id=?", (book_id,))
        
        conn.commit()
        print("\n✅ Data peminjaman terlambat berhasil dibuat!")
        print("\n🎯 Testing:")
        print("1. Buka aplikasi, pergi ke menu '💰 Denda'")
        print("2. Lihat peminjaman terlambat dengan denda Rp 6.000")
        print("3. Klik kanan pada denda untuk tandai LUNAS")
        print("4. Atau coba scan member ini untuk peminjaman (akan muncul warning denda)")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Membuat Test Data Peminjaman Terlambat ===\n")
    success = create_overdue_borrow()
    sys.exit(0 if success else 1)
