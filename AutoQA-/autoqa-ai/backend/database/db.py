import sqlite3
import psycopg2
import psycopg2.extras
import os
from datetime import datetime

# Local SQLite fallback
DB_PATH = os.path.join(os.path.dirname(__file__), "autoqa.db")

def get_connection():
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return psycopg2.connect(db_url)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def execute_query(query, params=None, fetch=False):
    db_url = os.getenv("DATABASE_URL")
    is_pg = bool(db_url)
    
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) if is_pg else conn.cursor()
    
    try:
        if is_pg:
            query = query.replace('?', '%s')
            if not fetch and query.strip().upper().startswith("INSERT"):
                query = query.rstrip("; ") + " RETURNING id"
        
        cursor.execute(query, params or ())
        
        if fetch:
            rows = cursor.fetchall()
            result = [dict(row) for row in rows]
            cursor.close()
            conn.close()
            return result
        
        conn.commit()
        last_id = cursor.fetchone()['id'] if is_pg and cursor.description else cursor.lastrowid
        cursor.close()
        conn.close()
        return last_id
    except Exception as e:
        if conn: conn.close()
        raise e
