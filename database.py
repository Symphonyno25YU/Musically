import sqlite3
from pathlib import Path


DATABASE_PATH = (
    Path(__file__).resolve().parent
    / "library"
    / "music_genre.db"
)


def initialize_database():
    connection = sqlite3.connect(DATABASE_PATH)

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tracks (
            id INTEGER PRIMARY KEY,
            apple_music_id TEXT UNIQUE,
            title TEXT NOT NULL,
            artist TEXT,
            genre TEXT,
            category TEXT
        )
        """
    )

    connection.commit()
    connection.close()


if __name__ == "__main__":
    initialize_database()
    print(f"Database created at: {DATABASE_PATH}")