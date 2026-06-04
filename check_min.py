import psycopg2

conn = psycopg2.connect(
    host="127.0.0.1", port=5432, dbname="quant_core",
    user="postgres", password="root"
)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM raw_min_block")
print(f"总记录数: {cur.fetchone()[0]:,}")

cur.execute("SELECT MIN(snapshot_time), MAX(snapshot_time) FROM raw_min_block")
r = cur.fetchone()
print(f"时间范围: {r[0]} ~ {r[1]}")

cur.execute("SELECT COUNT(DISTINCT block_code) FROM raw_min_block")
print(f"板块数: {cur.fetchone()[0]}")

cur.execute("""
    SELECT snapshot_time, COUNT(*) as cnt
    FROM raw_min_block
    GROUP BY snapshot_time
    ORDER BY snapshot_time DESC
    LIMIT 5
""")
print("最近5个采集点:")
for row in cur.fetchall():
    print(f"  {row[0]} -> {row[1]}条")

cur.execute("SELECT raw_no, COUNT(*) FROM raw_min_block GROUP BY raw_no LIMIT 10")
print("raw_no 分布(前10):")
for row in cur.fetchall():
    print(f"  {row[0]} -> {row[1]}")

cur.execute("""
    SELECT snapshot_time::date as dt, COUNT(DISTINCT snapshot_time) as snap_count, COUNT(*) as total_rows
    FROM raw_min_block
    GROUP BY snapshot_time::date
    ORDER BY dt DESC
    LIMIT 5
""")
print("每日采集概况:")
for row in cur.fetchall():
    print(f"  {row[0]} 采集点={row[1]} 总行数={row[2]:,}")

conn.close()
