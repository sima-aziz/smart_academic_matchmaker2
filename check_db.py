import sqlite3

conn = sqlite3.connect("database/app.db")
cursor = conn.cursor()

cursor.execute("SELECT id, first_name, last_name, email, password FROM users")
rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()
