import sqlite3
import os
import sys

# Add parent directory to path to import db module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from database.db import get_connection, DB_PATH
except ImportError:
    # Fallback if run from a different context
    from db import get_connection, DB_PATH

def translate_query(query, is_pg):
    if not is_pg:
        return query
    
    q = query.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    return q

def init_db():
    db_url = os.getenv("DATABASE_URL")
    is_pg = bool(db_url)
    
    print(f"Initializing {'PostgreSQL' if is_pg else 'SQLite'} database...")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Combined Schema (All basic tables)
        queries = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(255) NOT NULL UNIQUE,
                email VARCHAR(255) NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                user_id INTEGER,
                role TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS autonomous_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                module_name TEXT,
                requirement_text TEXT,
                url TEXT,
                repo_url TEXT,
                execution_mode TEXT,
                status TEXT DEFAULT 'Starting',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS autonomous_test_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                title TEXT,
                objective TEXT,
                module_name TEXT,
                preconditions TEXT,
                input_data TEXT,
                steps TEXT,
                category TEXT,
                tags TEXT,
                automatable INTEGER DEFAULT 1,
                blocked_reason TEXT,
                status TEXT DEFAULT 'Pending',
                action TEXT,
                selector TEXT,
                action_value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES autonomous_runs(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS autonomous_execution_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                test_case_id TEXT,
                step_number INTEGER,
                current_url TEXT,
                action TEXT,
                status TEXT,
                message TEXT,
                screenshot_path TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES autonomous_runs(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS autonomous_healing_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                original_selector TEXT,
                failure_reason TEXT,
                suggested_selector TEXT,
                confidence_score REAL,
                status TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES autonomous_runs(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS autonomous_risk_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                module_risk_score INTEGER,
                release_readiness TEXT,
                confidence_score INTEGER,
                high_risk_areas TEXT,
                recommendations TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES autonomous_runs(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS autonomous_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                executive_summary TEXT,
                final_verdict TEXT,
                report_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES autonomous_runs(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS dev_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                requirements_text TEXT,
                tech_stack TEXT,
                status TEXT DEFAULT 'Active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS dev_diagrams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                user_id INTEGER NOT NULL,
                diagram_type TEXT NOT NULL,
                title TEXT,
                mermaid_code TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES dev_projects(id) ON DELETE SET NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS dev_code (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                user_id INTEGER NOT NULL,
                language TEXT NOT NULL,
                title TEXT,
                code_content TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES dev_projects(id) ON DELETE SET NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS platform_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                project_id INTEGER,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES dev_projects(id) ON DELETE SET NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS message_replies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                sender_id INTEGER NOT NULL,
                body TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (message_id) REFERENCES platform_messages(id) ON DELETE CASCADE,
                FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS github_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                repo_url TEXT,
                analysis_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        ]

        # Execute table creations with syntax translation
        for q in queries:
            try:
                translated = translate_query(q, is_pg)
                cursor.execute(translated)
            except Exception as e:
                print(f"Warning: Table creation error: {e}")
        
        # Additive columns (Try/Except for simple migrations)
        migrations = [
            "ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'qa_engineer'"
        ]
        for m in migrations:
            try:
                if is_pg:
                    cursor.execute("SAVEPOINT sp_user_role")
                    cursor.execute(m)
                    cursor.execute("RELEASE SAVEPOINT sp_user_role")
                else:
                    cursor.execute(m)
            except Exception as e:
                if is_pg:
                    cursor.execute("ROLLBACK TO SAVEPOINT sp_user_role")
                pass

        conn.commit()
            
        cursor.close()
        conn.close()
        print(f"Database {'PostgreSQL' if is_pg else 'SQLite'} initialized successfully.")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    init_db()
