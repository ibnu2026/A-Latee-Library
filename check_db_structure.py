import sqlite3

db_path = r"C:\Users\Ahmad Ibnu Zaini\AppData\Roaming\Latee Library\library_data.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Check struktur tabel books
c.execute("PRAGMA table_info(books)")
cols = c.fetchall()

print("=== STRUKTUR TABEL BOOKS ===")
for col in cols:
    print(f"{col[1]:20} ({col[2]})")

print("\n=== SAMPLE DATA (5 baris pertama) ===")
c.execute("SELECT id, kode_buku, judul, penulis, pengarang FROM books LIMIT 5")
for row in c.fetchall():
    print(f"ID: {row[0]}, Kode: {row[1]}")
    print(f"  Judul: {row[2]}")
    print(f"  Penulis: {row[3]}")
    print(f"  Pengarang: {row[4]}")
    print()

conn.close()
