import sqlite3, os
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'db.sqlite3'))
print('DB:', DB_PATH)
con = sqlite3.connect(DB_PATH)
cur = con.cursor()
for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    print(row[0])
con.close()
