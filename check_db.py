import sqlite3
db = sqlite3.connect('music_library.db')
c = db.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print("Tables:", tables)
for t in tables:
    name = t[0]
    c.execute(f"PRAGMA table_info({name})")
    cols = c.fetchall()
    print(f"\n{name}: {[col[1] for col in cols]}")
db.close()
