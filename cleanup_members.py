import sqlite3

db_path = r'C:\Users\Ahmad Ibnu Zaini\AppData\Roaming\Latee Library\library_data.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("=== Cleaning up members table ===\n")

# Hapus kolom yang tidak digunakan: nis, alamat, tempat, tanggal_lahir
cols_to_drop = ['nis', 'alamat', 'tempat', 'tanggal_lahir']

for col in cols_to_drop:
    try:
        c.execute(f'ALTER TABLE members DROP COLUMN {col}')
        conn.commit()
        print(f'✓ Kolom "{col}" berhasil dihapus')
    except Exception as e:
        print(f'✗ Gagal hapus "{col}": {e}')

# Show final structure
print('\n=== Struktur members sekarang ===')
c.execute('PRAGMA table_info(members)')
cols = c.fetchall()
for col in cols:
    print(f'  {col[1]} ({col[2]})')

conn.close()
print('\n✓ Database cleanup selesai!')
