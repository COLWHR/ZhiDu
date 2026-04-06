import sqlite3
import os

db_path = 'madf.db'
if not os.path.exists(db_path):
    print(f"数据库文件不存在: {db_path}")
    print("当前目录文件:", os.listdir('.'))
else:
    print(f"找到数据库文件: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查询所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("\n=== 数据库中的表 ===")
    for table in tables:
        print(f"- {table[0]}")
        
        # 查看表结构
        cursor.execute(f"PRAGMA table_info({table[0]})")
        columns = cursor.fetchall()
        print(f"  字段: {[col[1] for col in columns]}")
        
        # 查看表数据
        try:
            cursor.execute(f"SELECT * FROM {table[0]}")
            rows = cursor.fetchall()
            print(f"  数据行数: {len(rows)}")
            if rows:
                print(f"  前3条数据:")
                for i, row in enumerate(rows[:3]):
                    print(f"    {i+1}. {row}")
        except Exception as e:
            print(f"  查询数据失败: {e}")
    
    conn.close()
