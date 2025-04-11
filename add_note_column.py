import sqlite3

conn = sqlite3.connect("expenses.db")  # or expense_tracker.db
c = conn.cursor()
c.execute("ALTER TABLE expenses ADD COLUMN note TEXT;")
conn.commit()
conn.close()

print("Column 'note' added successfully.")
