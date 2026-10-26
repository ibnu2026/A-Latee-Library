import sqlite3
conn = sqlite3.connect('library_data.db')
c = conn.cursor()
try:
    c.execute("ALTER TABLE books ADD COLUMN status TEXT DEFAULT 'ada'")
except Exception as e:
    print('status:', e)
try:
    c.execute("ALTER TABLE books ADD COLUMN jumlah_dipinjam INTEGER DEFAULT 0")
except Exception as e:
    print('jumlah_dipinjam:', e)
conn.commit()
conn.close()
print('Done')
