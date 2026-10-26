import sqlite3
from pathlib import Path
import hashlib

DB_PATH = Path('library_data.db')
if not DB_PATH.exists():
    raise FileNotFoundError(DB_PATH)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Ensure users table exists
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
if not cur.fetchone():
    raise RuntimeError('users table not found in library_data.db')

# Determine columns
cur.execute('PRAGMA table_info(users)')
cols = [row[1] for row in cur.fetchall()]
print('users columns:', cols)

# Remove any existing user except admin
if 'username' in cols:
    cur.execute("DELETE FROM users WHERE LOWER(username) <> 'admin'")
else:
    cur.execute('DELETE FROM users')

# Confirm admin exists or insert a fresh admin
cur.execute("SELECT COUNT(*) FROM users WHERE LOWER(username) = 'admin'")
admin_count = cur.fetchone()[0]
if admin_count == 0:
    password_hash = hashlib.sha256('admin123'.encode('utf-8')).hexdigest()
    insert_cols = ['username', 'password_hash', 'full_name']
    if 'avatar_path' in cols:
        insert_cols.append('avatar_path')
    if 'role' in cols:
        insert_cols.append('role')
    if 'jabatan' in cols:
        insert_cols.append('jabatan')
    if 'created_at' in cols:
        insert_cols.append('created_at')

    values = ['admin', password_hash, 'Administrator']
    if 'avatar_path' in cols:
        values.append(None)
    if 'role' in cols:
        values.append('administrator')
    if 'jabatan' in cols:
        values.append('Administrator')
    if 'created_at' in cols:
        values.append(None)

    placeholders = ','.join('?' for _ in insert_cols)
    cur.execute(f"INSERT INTO users({','.join(insert_cols)}) VALUES({placeholders})", values)
    print('Inserted default admin user')
else:
    print('Admin user already exists')

# Remove any potential ibnu2026 explicitly
cur.execute("DELETE FROM users WHERE LOWER(username) = 'ibnu2026'")
cur.execute("DELETE FROM users WHERE LOWER(full_name) = 'ibnu2026'")

conn.commit()
conn.close()
print('library_data.db normalized to include only admin')