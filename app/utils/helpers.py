# sqlite3 CLI helper tool (optional)

import sqlite3
DB_PATH = 'foodwaste.db'

def init_sample_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS sample_test (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()
    print("Sample DB check complete.")

if __name__ == '__main__':
    init_sample_db()