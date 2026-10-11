import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'elevator_enterprise.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create Users table for Role-Based Access Control
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            uid TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            role TEXT DEFAULT 'viewer',
            theme TEXT DEFAULT 'dark'
        )
    ''')
    
    # Create History table for exporting PDFs later
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            action TEXT,
            details TEXT,
            user_uid TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Local SQLite Database initialized to bypass Firebase billing constraints!")
