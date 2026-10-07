"""Lu's long-term memory, kept in SQLite.

Every message is archived by session, so restarting Lu picks the conversation back up.
Lasting memories are saved and corrected through tools. Both are searched with FTS5.
A child-mode session only sees its own messages and memories.
"""
import json
import sqlite3

db = None
session = None
child_mode = False

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY, child_mode INTEGER NOT NULL,
    started TEXT NOT NULL DEFAULT (datetime('now', 'localtime')));
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY, session INTEGER NOT NULL, message TEXT NOT NULL,
    created TEXT NOT NULL DEFAULT (datetime('now', 'localtime')));
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY, session INTEGER NOT NULL, text TEXT NOT NULL,
    updated TEXT NOT NULL DEFAULT (datetime('now', 'localtime')));
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(text);
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(text);
"""

# Rows a search or edit may touch: all of them, or only this session's in child mode.
IN_SCOPE = "(? = 0 OR session = ?)"


def connect(path):
    """Open the database and resume the last session."""
    global db, session, child_mode
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    last = db.execute("SELECT id, child_mode FROM sessions ORDER BY id DESC LIMIT 1").fetchone()
    if last:
        session, child_mode = last[0], bool(last[1])
    else:
        start_session(False)


def start_session(child):
    global session, child_mode
    with db:
        session = db.execute("INSERT INTO sessions (child_mode) VALUES (?)", (int(child),)).lastrowid
    child_mode = child


def scope():
    return (int(child_mode), session)


def load_session(limit=200):
    rows = db.execute("SELECT message FROM messages WHERE session = ? ORDER BY id DESC LIMIT ?",
                      (session, limit)).fetchall()
    return [json.loads(message) for (message,) in reversed(rows)]


def save(message):
    with db:
        row = db.execute("INSERT INTO messages (session, message) VALUES (?, ?)",
                         (session, json.dumps(message))).lastrowid
        if message["role"] in ("user", "assistant") and message.get("content"):
            db.execute("INSERT INTO messages_fts (rowid, text) VALUES (?, ?)", (row, message["content"]))


def match(text):
    """Any of the words in text, each quoted so FTS5 reads it as plain text."""
    return " OR ".join('"' + word.replace('"', '""') + '"' for word in text.split())


def find_memories(text, limit=5):
    if not text.split():
        return []
    rows = db.execute(
        "SELECT m.id, m.text, m.updated FROM memories_fts JOIN memories m ON m.id = memories_fts.rowid"
        f" WHERE memories_fts MATCH ? AND {IN_SCOPE} ORDER BY rank LIMIT ?",
        (match(text), *scope(), limit)).fetchall()
    return [{"id": id, "text": text, "updated": updated} for id, text, updated in rows]


def find_messages(text, limit=5):
    if not text.split():
        return []
    rows = db.execute(
        "SELECT m.message, m.created FROM messages_fts JOIN messages m ON m.id = messages_fts.rowid"
        f" WHERE messages_fts MATCH ? AND {IN_SCOPE} ORDER BY rank LIMIT ?",
        (match(text), *scope(), limit)).fetchall()
    found = [(json.loads(message), created) for message, created in rows]
    return [{"role": m["role"], "text": m["content"], "when": created} for m, created in found]


# Tools

def remember(text: str) -> dict:
    with db:
        id = db.execute("INSERT INTO memories (session, text) VALUES (?, ?)", (session, text)).lastrowid
        db.execute("INSERT INTO memories_fts (rowid, text) VALUES (?, ?)", (id, text))
    return {"id": id}


def recall(query: str) -> dict:
    return {"memories": find_memories(query), "conversations": find_messages(query)}


def update_memory(id: int, text: str) -> dict:
    with db:
        updated = db.execute(f"UPDATE memories SET text = ?, updated = datetime('now', 'localtime')"
                             f" WHERE id = ? AND {IN_SCOPE}", (text, id, *scope())).rowcount
        if updated:
            db.execute("UPDATE memories_fts SET text = ? WHERE rowid = ?", (text, id))
    return {"updated": bool(updated)}


def forget(id: int) -> dict:
    with db:
        forgotten = db.execute(f"DELETE FROM memories WHERE id = ? AND {IN_SCOPE}", (id, *scope())).rowcount
        if forgotten:
            db.execute("DELETE FROM memories_fts WHERE rowid = ?", (id,))
    return {"forgotten": bool(forgotten)}
