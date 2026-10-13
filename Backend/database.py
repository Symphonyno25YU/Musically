import sqlite3
from pathlib import Path


DATABASE_PATH = (
    Path(__file__).resolve().parent
    / "library"
    / "music_genre.db"
)
CATEGORIES = (
    "workstudy",
    "creativity",
    "deepthinking",
    "relaxation",
    "intense",
)


def get_connection():
    # Open the local Music Switcher SQLite database.
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    # Create the database and its tracks table when they do not exist.
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY,
                apple_music_id TEXT,
                title TEXT NOT NULL,
                artist TEXT,
                genre TEXT,
                category TEXT NOT NULL,
                UNIQUE(title, category)
            )
            """
        )


def replace_music_library(music_library):
    # Replace all saved category assignments with a newly synced library.
    initialize_database()
    rows = [
        (title, category)
        for category in CATEGORIES
        for title in music_library.get(category, ())
    ]
    with get_connection() as connection:
        connection.execute("DELETE FROM tracks")
        connection.executemany(
            "INSERT INTO tracks (title, category) VALUES (?, ?)",
            rows,
        )


def load_music_library():
    # Return SQLite track rows grouped into the five activity categories.
    initialize_database()
    library = {category: [] for category in CATEGORIES}
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT title, category
            FROM tracks
            ORDER BY id
            """
        ).fetchall()

    for row in rows:
        if row["category"] in library:
            library[row["category"]].append(row["title"])
    return library


if __name__ == "__main__":
    initialize_database()
    print(f"Database created at: {DATABASE_PATH}")
