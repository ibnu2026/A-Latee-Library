#!/usr/bin/env python3
"""Initialize database with tables"""
import sys
import sqlite3

DB_PATH = "library_data.db"

# Create the Database class inline to avoid PyQt5 import issues
class Database:
    def __init__(self, path=DB_PATH):
        self.conn = sqlite3.connect(path)
        self.create_tables()
        print("[DB] Database initialized successfully")
    
    def create_tables(self):
        c = self.conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS books(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kode_buku TEXT,
            kategori TEXT,
            judul TEXT,
            penulis TEXT,
            penerbit TEXT,
            barcode TEXT UNIQUE,
            stok INTEGER DEFAULT 1,
            status TEXT DEFAULT 'ada',
            jumlah_dipinjam INTEGER DEFAULT 0,
            UNIQUE(kode_buku, kategori)
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS members(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nis TEXT,
            nama TEXT,
            rayon TEXT,
            kamar TEXT,
            alamat TEXT,
            barcode TEXT UNIQUE,
            jenis_santri TEXT DEFAULT 'lama',
            qr_id TEXT
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS borrows(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER,
            member_id INTEGER,
            tanggal_pinjam TEXT,
            tanggal_kembali TEXT,
            status INTEGER DEFAULT 0,
            diperpanjang INTEGER DEFAULT 0,
            denda INTEGER DEFAULT 0,
            FOREIGN KEY(book_id) REFERENCES books(id),
            FOREIGN KEY(member_id) REFERENCES members(id)
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS visitors(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT,
            kamar TEXT,
            rayon TEXT,
            fingerprint_id TEXT UNIQUE,
            waktu_kunjungan TEXT
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS visitor_visits(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visitor_id INTEGER NOT NULL,
            waktu_kunjungan TEXT NOT NULL,
            FOREIGN KEY(visitor_id) REFERENCES visitors(id)
        )''')
        c.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_visitor_visits_unique_time
                     ON visitor_visits(visitor_id, waktu_kunjungan)''')
        c.execute('''
            INSERT OR IGNORE INTO visitor_visits(visitor_id, waktu_kunjungan)
            SELECT id, waktu_kunjungan
            FROM visitors
            WHERE waktu_kunjungan IS NOT NULL AND waktu_kunjungan != ''
        ''')

        c.execute('''CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            full_name TEXT,
            avatar_path TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS santri_fingerprints(
            santri_id INTEGER PRIMARY KEY,
            nama TEXT NOT NULL,
            template_data BLOB NOT NULL,
            template_hash TEXT UNIQUE,
            quality INTEGER DEFAULT 80,
            timestamp TEXT DEFAULT (datetime('now')),
            rayon TEXT,
            kamar TEXT,
            status TEXT DEFAULT 'active'
        )''')

        self.conn.commit()
        
        # Create index for template_hash
        try:
            c.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_template_hash_unique
                         ON santri_fingerprints(template_hash)''')
            self.conn.commit()
            print("[OK] Created unique index on template_hash")
        except Exception as e:
            print(f"[WARN] Index creation: {e}")

if __name__ == "__main__":
    try:
        db = Database()
        
        # Verify tables were created
        c = db.conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in c.fetchall()]
        print(f"\n[OK] Created tables: {', '.join(tables)}")
        
        # Verify visitors table structure
        c.execute("PRAGMA table_info(visitors)")
        cols = [col[1] for col in c.fetchall()]
        print(f"[OK] Visitors table columns: {', '.join(cols)}")
        
        db.conn.close()
        print("\n✅ Database initialization complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
