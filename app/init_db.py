import sys
import os

# 添加父目录到路径，以便导入app模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.client import db_manager
import logging

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    print("正在初始化数据库...")
    try:
        db_manager.init_db(schema_path="db/schema.sql")
        print("数据库初始化成功！")
        
        # 重新检查数据库
        print("\n检查数据库表...")
        import sqlite3
        conn = sqlite3.connect('madf.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        if tables:
            print("数据库中的表:")
            for table in tables:
                print(f"  - {table[0]}")
                
                # 查询用户表数据
                if table[0] == 'users':
                    cursor.execute("SELECT id, username, role, created_at FROM users")
                    users = cursor.fetchall()
                    print(f"\n用户列表 ({len(users)}个用户):")
                    for user in users:
                        print(f"  ID: {user[0]}, 用户名: {user[1]}, 角色: {user[2]}, 创建时间: {user[3]}")
        
        conn.close()
        
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
