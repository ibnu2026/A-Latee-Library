import sqlite3
from pathlib import Path

root = Path('.')
for dbfile in sorted(root.glob('*.db')):
    print('DB:', dbfile)
    try:
        con = sqlite3.connect(dbfile)
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cur.fetchall()]
        print('  tables:', tables)
        if 'users' in tables:
            cur.execute('PRAGMA table_info(users)')
            cols = [row[1] for row in cur.fetchall()]
            print('  cols:', cols)
            rows = cur.execute('SELECT * FROM users').fetchall()
            print('  row count:', len(rows))
            for row in rows[:20]:
                print('   ', row)
        con.close()
    except Exception as exc:
        print('  error:', exc)
    print()