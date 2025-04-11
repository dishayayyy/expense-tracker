import sqlite3

conn = sqlite3.connect("expenses.db")
c = conn.cursor()

# Add budget column if it doesn't exist
try:
    c.execute("ALTER TABLE users ADD COLUMN budget REAL DEFAULT 0")
    print("✅ 'budget' column added to users table.")
except sqlite3.OperationalError as e:
    print("⚠️", e)

conn.commit()
conn.close()
