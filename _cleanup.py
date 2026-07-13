import sqlite3, csv, os, sys

db_path = sys.argv[1] if len(sys.argv) > 1 else 'output/tiktok_data.db'
db = sqlite3.connect(db_path)
db.row_factory = sqlite3.Row

bad = db.execute("SELECT username, length(nickname) as nlen FROM accounts WHERE nickname IS NULL OR nickname = '' OR nickname LIKE '%<%' OR nickname LIKE '%svg%' OR length(nickname) > 100 OR scraped_at IS NULL OR scraped_at = ''").fetchall()
print(f'Baris kotor: {len(bad)}')
for r in bad:
    print(f'  @{r["username"]} ({r["nlen"]} chars)')

deleted = 0
for r in bad:
    db.execute("DELETE FROM accounts WHERE username = ?", (r["username"],))
    db.execute("DELETE FROM videos WHERE account_id = ?", (r["username"],))
    deleted += 1
db.commit()
print(f'Dihapus: {deleted} akun')

from database import Database
d = Database(db_path)
d.conn = db
d.export_csv('output/accounts.csv', 'output/videos.csv')
print('CSV OK')

c = db.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
print(f'Akun: {c}')
c = db.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
print(f'Video: {c}')
db.close()
