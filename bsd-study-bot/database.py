import sqlite3

DATABASE_NAME = "bsd_study.db"


def get_connection():
    return sqlite3.connect(DATABASE_NAME)


def setup_database():
    conn = get_connection()
    cursor = conn.cursor()

    # User study stats
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        total_seconds INTEGER DEFAULT 0,
        crystals INTEGER DEFAULT 0
    )
    """)

    # Currently active study sessions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS active_sessions (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        subject TEXT,
        start_time REAL
    )
    """)

    # Completed study sessions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS study_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        username TEXT,
        subject TEXT,
        duration_seconds INTEGER,
        crystals_earned INTEGER,
        completed_at REAL
    )
    """)

    # Character collection
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        character_name TEXT NOT NULL,
        rarity TEXT NOT NULL,
        copies INTEGER DEFAULT 1
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS question_sets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        source TEXT,
        source_url TEXT,
        created_at REAL DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        set_id INTEGER NOT NULL,
        prompt TEXT NOT NULL,
        answer TEXT NOT NULL,
        position INTEGER NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def create_user(user_id, username):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO users (user_id, username)
    VALUES (?, ?)
    """, (user_id, username))

    conn.commit()
    conn.close()


def update_user_stats(user_id, seconds, crystals):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE users
    SET total_seconds = total_seconds + ?,
        crystals = crystals + ?
    WHERE user_id = ?
    """, (seconds, crystals, user_id))

    conn.commit()
    conn.close()


def get_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT username, total_seconds, crystals
    FROM users
    WHERE user_id = ?
    """, (user_id,))

    user = cursor.fetchone()

    conn.close()

    return user


def add_study_session(
    user_id,
    username,
    subject,
    duration_seconds,
    crystals_earned,
    completed_at
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO study_sessions
    (
        user_id,
        username,
        subject,
        duration_seconds,
        crystals_earned,
        completed_at
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        username,
        subject,
        duration_seconds,
        crystals_earned,
        completed_at
    ))

    conn.commit()
    conn.close()


def get_session_count(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT COUNT(*)
    FROM study_sessions
    WHERE user_id = ?
    """, (user_id,))

    count = cursor.fetchone()[0]

    conn.close()

    return count


def get_favorite_subject(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT subject, SUM(duration_seconds) AS total_time
    FROM study_sessions
    WHERE user_id = ?
    GROUP BY subject
    ORDER BY total_time DESC
    LIMIT 1
    """, (user_id,))

    result = cursor.fetchone()

    conn.close()

    if result:
        return result[0]

    return "None yet"


def add_character(user_id, character_name, rarity):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT copies
    FROM characters
    WHERE user_id = ?
    AND character_name = ?
    """, (user_id, character_name))

    existing = cursor.fetchone()

    if existing:
        cursor.execute("""
        UPDATE characters
        SET copies = copies + 1
        WHERE user_id = ?
        AND character_name = ?
        """, (user_id, character_name))
    else:
        cursor.execute("""
        INSERT INTO characters
        (user_id, character_name, rarity, copies)
        VALUES (?, ?, ?, 1)
        """, (user_id, character_name, rarity))

    conn.commit()
    conn.close()


def get_characters(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT character_name, rarity, copies
    FROM characters
    WHERE user_id = ?
    ORDER BY id
    """, (user_id,))

    characters = cursor.fetchall()

    conn.close()

    return characters


def get_character_cards(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, character_name, rarity, copies
    FROM characters
    WHERE user_id = ?
    ORDER BY id
    """, (user_id,))

    cards = cursor.fetchall()
    conn.close()
    return cards


def get_character_card(card_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, user_id, character_name, rarity, copies
    FROM characters
    WHERE id = ?
    """, (card_id,))

    card = cursor.fetchone()
    conn.close()
    return card
def set_crystals(user_id, amount):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE users
    SET crystals = ?
    WHERE user_id = ?
    """, (amount, user_id))

    conn.commit()
    conn.close()


def create_question_set(owner_id, name, questions, source="manual", source_url=None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO question_sets (owner_id, name, source, source_url)
    VALUES (?, ?, ?, ?)
    """, (owner_id, name, source, source_url))

    set_id = cursor.lastrowid

    cursor.executemany("""
    INSERT INTO questions (set_id, prompt, answer, position)
    VALUES (?, ?, ?, ?)
    """, [
        (set_id, prompt, answer, position)
        for position, (prompt, answer) in enumerate(questions)
    ])

    conn.commit()
    conn.close()

    return set_id


def ensure_question_set(owner_id, name, questions, source="default"):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id
    FROM question_sets
    WHERE owner_id = ? AND lower(name) = lower(?)
    LIMIT 1
    """, (owner_id, name))

    existing = cursor.fetchone()

    if existing and source == "original ACT-style practice":
        cursor.execute("""
        SELECT COUNT(*)
        FROM questions
        WHERE set_id = ?
        """, (existing[0],))

        question_count = cursor.fetchone()[0]

        if question_count != len(questions):
            cursor.execute("""
            DELETE FROM questions
            WHERE set_id = ?
            """, (existing[0],))

            cursor.executemany("""
            INSERT INTO questions (set_id, prompt, answer, position)
            VALUES (?, ?, ?, ?)
            """, [
                (existing[0], prompt, answer, position)
                for position, (prompt, answer) in enumerate(questions)
            ])

            conn.commit()

    conn.close()

    if existing:
        return existing[0]

    return create_question_set(owner_id, name, questions, source=source)


def get_question_sets(owner_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT question_sets.id, question_sets.name, question_sets.source,
           COUNT(questions.id)
    FROM question_sets
    LEFT JOIN questions ON questions.set_id = question_sets.id
    WHERE owner_id = ?
    GROUP BY question_sets.id
    ORDER BY question_sets.id DESC
    """, (owner_id,))

    result = cursor.fetchall()
    conn.close()
    return result


def get_question_set(owner_id, name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, name, source, source_url
    FROM question_sets
    WHERE owner_id = ? AND lower(name) = lower(?)
    ORDER BY id DESC
    LIMIT 1
    """, (owner_id, name))

    question_set = cursor.fetchone()

    if not question_set:
        conn.close()
        return None, []

    cursor.execute("""
    SELECT prompt, answer
    FROM questions
    WHERE set_id = ?
    ORDER BY position
    """, (question_set[0],))

    questions = cursor.fetchall()
    conn.close()
    return question_set, questions