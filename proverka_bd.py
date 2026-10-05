import sqlite3
import pandas as pd
import config

conn = sqlite3.connect(config.DB_PATH)

df = pd.read_sql_query("SELECT * FROM highlights", conn)
conn.close()

print(f"Всего записей в БД: {len(df)}")
print(df.head(10))