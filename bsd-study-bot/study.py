import time
import database


def start_session(user_id, username, subject):
    database.create_user(user_id, username)

    conn = database.get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT user_id
    FROM active_sessions
    WHERE user_id = ?
    """, (user_id,))

    existing_session = cursor.fetchone()

    if existing_session:
        conn.close()
        return False

    cursor.execute("""
    INSERT INTO active_sessions
    (user_id, username, subject, start_time)
    VALUES (?, ?, ?, ?)
    """, (
        user_id,
        username,
        subject,
        time.time()
    ))

    conn.commit()
    conn.close()

    return True


def end_session(user_id):
    conn = database.get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT username, subject, start_time
    FROM active_sessions
    WHERE user_id = ?
    """, (user_id,))

    session = cursor.fetchone()

    if not session:
        conn.close()
        return None

    username, subject, start_time = session

    duration_seconds = int(
        time.time() - start_time
    )

    # 1 minute of studying = 1 Ability Crystal
    crystals_earned = duration_seconds // 60

    database.add_study_session(
        user_id,
        username,
        subject,
        duration_seconds,
        crystals_earned,
        time.time()
    )

    cursor.execute("""
    DELETE FROM active_sessions
    WHERE user_id = ?
    """, (user_id,))

    conn.commit()
    conn.close()

    database.update_user_stats(
        user_id,
        duration_seconds,
        crystals_earned
    )

    return {
        "subject": subject,
        "duration": duration_seconds,
        "crystals": crystals_earned
    }


def format_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"

    return f"{minutes}m {seconds}s"