import sqlite3
from pathlib import Path

# This helper script demonstrates the intended matching logic for import_books_from_excel
# It is not the application code itself but shows how to query by kode_buku + kategori.

db_path = Path('library.db')
if not db_path.exists():
    raise FileNotFoundError(db_path)

with sqlite3.connect(db_path) as con:
    cur = con.cursor()
    cur.execute("SELECT * FROM books WHERE kode_buku=? AND kategori=?", ('BK001', 'Teknologi'))
    print(cur.fetchone())
