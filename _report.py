import sqlite3, sys
db = sys.argv[1] if len(sys.argv) > 1 else 'output/tiktok_data.db'
conn = sqlite3.connect(db)
c = conn.execute('SELECT COUNT(*) FROM accounts')
print(f'Total akun: {c.fetchone()[0]}')
c = conn.execute('SELECT COUNT(*) FROM videos')
print(f'Total video: {c.fetchone()[0]}')
c = conn.execute('SELECT COUNT(*) FROM accounts WHERE monetization=1')
print(f'Monetisasi YA: {c.fetchone()[0]}')
c = conn.execute('SELECT COUNT(*) FROM accounts WHERE has_tiktok_shop=1')
print(f'Shop YA: {c.fetchone()[0]}')
print()
rows = conn.execute('SELECT username, followers, video_count, location_detected, location_source, monetization, has_tiktok_shop, engagement_rate FROM accounts ORDER BY followers DESC').fetchall()
for r in rows:
    mon = 'YA' if r[5] else 'TIDAK'
    shop = 'YA' if r[6] else 'TIDAK'
    er = f'{r[7]:.2f}%' if r[7] else '-'
    lok = r[3] or '-'
    src = f'({r[4]})' if r[4] else ''
    print(f'  @{r[0]:25s} fw:{str(r[1] or 0):>8s} vid:{str(r[2] or 0):>5s} lok:{lok:20s} {src:20s} mon:{mon:5s} shop:{shop:5s} er:{er}')
conn.close()
