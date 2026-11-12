
from pathlib import Path
import sqlite3
from contextlib import contextmanager


ROOT_DIR = Path(__file__).resolve().parents[2]


class Database:

    def __init__(self, db_path=None):

        self.db_path = (
            Path(db_path)
            if db_path
            else ROOT_DIR / "data" / "stheno.db"
        )

        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.initialize()

    @contextmanager
    def connect(self):

        connection = sqlite3.connect(
            self.db_path,
            timeout=10
        )

        connection.row_factory = sqlite3.Row

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        try:
            yield connection
            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    def initialize(self):

        with self.connect() as conn:

            conn.execute(
                "PRAGMA journal_mode = WAL"
            )

            conn.executescript("""

                CREATE TABLE IF NOT EXISTS conversations (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    title TEXT NOT NULL
                        DEFAULT 'New conversation',

                    created_at TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,

                    updated_at TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                );


                CREATE TABLE IF NOT EXISTS messages (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    conversation_id INTEGER NOT NULL,

                    role TEXT NOT NULL
                        CHECK(role IN (
                            'system',
                            'user',
                            'assistant'
                        )),

                    content TEXT NOT NULL,

                    created_at TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (conversation_id)
                        REFERENCES conversations(id)
                        ON DELETE CASCADE
                );


                CREATE INDEX IF NOT EXISTS
                    idx_messages_conversation

                ON messages(conversation_id, id);


                CREATE TABLE IF NOT EXISTS memories (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    category TEXT NOT NULL
                        DEFAULT 'general',

                    content TEXT NOT NULL,

                    importance INTEGER NOT NULL
                        DEFAULT 1,

                    source_conversation_id INTEGER,

                    created_at TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,

                    updated_at TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (source_conversation_id)
                        REFERENCES conversations(id)
                        ON DELETE SET NULL
                );

            """)


if __name__ == "__main__":

    database = Database()

    print("[OK] SQLite initialized!")
    print(f"Database: {database.db_path}")
