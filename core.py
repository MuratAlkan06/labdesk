"""LabDesk core: all business logic for the CMPE Department Lab Support Desk.

Standard library only (sqlite3, datetime, statistics, contextlib). Importing
Streamlit here is banned (PRINCIPLES.md §3): app.py renders, core.py decides.

Every public function takes ``db_path`` as its first argument so tests can run
against a throwaway database. Wall-clock time is read in exactly one place,
``now_iso()``, so tests can monkeypatch a single seam (PRINCIPLES.md §5).
"""

import sqlite3
import statistics
from contextlib import closing
from datetime import datetime

# --- Domain vocabulary (defined once; every other module reads these) --------

CATEGORIES = [
    "Account access",
    "Lab hardware",
    "Software install",
    "Network",
    "Printing",
    "Other",
]

PRIORITIES = ["Low", "Medium", "High", "Urgent"]

SOURCES = ["Web form", "Email", "Walk-in"]

STATUSES = ["Open", "In Progress", "Resolved", "Closed"]

# The three part-time student technicians who staff the desk.
TECHNICIANS = ["Priya Raman", "Diego Alvarez", "Hannah Kim"]

# Label for tickets with no assignee: used by the queue filter and the
# dashboard workload bucket so the literal is written down only once.
UNASSIGNED = "Unassigned"

# The only legal status moves. Closed is terminal; Resolved can be reopened.
ALLOWED_TRANSITIONS = {
    ("Open", "In Progress"),
    ("In Progress", "Resolved"),
    ("Resolved", "Closed"),
    ("Resolved", "Open"),
}

DEFAULT_DB = "labdesk.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL,
    priority TEXT NOT NULL,
    source TEXT NOT NULL,
    requester_name TEXT NOT NULL,
    requester_email TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Open',
    assignee TEXT,
    created_at TEXT NOT NULL,
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    author TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class TransitionError(Exception):
    """Raised when a status change is not in ALLOWED_TRANSITIONS."""

    def __init__(self, ticket_id, from_status, to_status):
        self.ticket_id = ticket_id
        self.from_status = from_status
        self.to_status = to_status
        allowed = [s for s in STATUSES if (from_status, s) in ALLOWED_TRANSITIONS]
        allowed_text = ", ".join(allowed) if allowed else "nothing"
        super().__init__(
            f"Illegal transition: {from_status} → {to_status}. "
            f"Allowed from {from_status}: {allowed_text}."
        )


# --- Connection and schema ---------------------------------------------------


def get_conn(db_path):
    """Open a connection with row access by column name. Caller closes it."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path):
    """Create the tickets and notes tables if they do not already exist."""
    with closing(get_conn(db_path)) as conn:
        conn.executescript(_SCHEMA)
        conn.commit()


def now_iso():
    """Current local time as an ISO-8601 string, seconds precision.

    The only place this codebase reads the wall clock.
    """
    return datetime.now().isoformat(timespec="seconds")


# --- Validation helpers ------------------------------------------------------


def _require_text(field, value):
    text = (value or "").strip()
    if not text:
        raise ValueError(f"{field} must not be empty.")
    return text


def _require_member(field, value, allowed):
    if value not in allowed:
        raise ValueError(f"{field} must be one of {', '.join(allowed)}; got {value!r}.")
    return value


def _require_ticket(conn, ticket_id):
    row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if row is None:
        raise ValueError(f"ticket_id {ticket_id!r} does not exist.")
    return row


def is_valid_transition(from_status, to_status):
    """True when moving from_status -> to_status is allowed."""
    return (from_status, to_status) in ALLOWED_TRANSITIONS


# --- Submit ------------------------------------------------------------------


def create_ticket(
    db_path,
    title,
    description,
    category,
    priority,
    source,
    requester_name,
    requester_email,
):
    """Insert a new ticket (status Open, unassigned) and return its id.

    Raises ValueError naming the offending field for an empty title or
    requester name, or for a category/priority/source outside the constants.
    """
    title = _require_text("title", title)
    requester_name = _require_text("requester_name", requester_name)
    _require_member("category", category, CATEGORIES)
    _require_member("priority", priority, PRIORITIES)
    _require_member("source", source, SOURCES)

    with closing(get_conn(db_path)) as conn:
        cursor = conn.execute(
            """
            INSERT INTO tickets (
                title, description, category, priority, source,
                requester_name, requester_email, status, assignee,
                created_at, resolved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                (description or "").strip(),
                category,
                priority,
                source,
                requester_name,
                (requester_email or "").strip(),
                "Open",
                None,
                now_iso(),
                None,
            ),
        )
        conn.commit()
        return cursor.lastrowid


# --- Queue -------------------------------------------------------------------


def get_ticket(db_path, ticket_id):
    """Return the ticket row, or None when no such ticket exists."""
    with closing(get_conn(db_path)) as conn:
        return conn.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()


def list_tickets(
    db_path, search=None, status=None, priority=None, category=None, assignee=None
):
    """Return ticket rows newest-first, narrowed by any combination of filters.

    ``search`` is a case-insensitive substring match over title OR description.
    ``assignee=UNASSIGNED`` selects tickets with no assignee. A filter left at
    None is not applied; supplied filters are combined with AND.
    """
    clauses = []
    params = []

    if search:
        pattern = f"%{search.strip().lower()}%"
        clauses.append("(LOWER(title) LIKE ? OR LOWER(description) LIKE ?)")
        params.extend([pattern, pattern])
    if status:
        clauses.append("status = ?")
        params.append(status)
    if priority:
        clauses.append("priority = ?")
        params.append(priority)
    if category:
        clauses.append("category = ?")
        params.append(category)
    if assignee:
        if assignee == UNASSIGNED:
            clauses.append("assignee IS NULL")
        else:
            clauses.append("assignee = ?")
            params.append(assignee)

    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"SELECT * FROM tickets{where} ORDER BY created_at DESC, id DESC"

    with closing(get_conn(db_path)) as conn:
        return conn.execute(sql, params).fetchall()


def list_notes(db_path, ticket_id):
    """Return the notes on a ticket, oldest-first."""
    with closing(get_conn(db_path)) as conn:
        return conn.execute(
            "SELECT * FROM notes WHERE ticket_id = ? ORDER BY created_at ASC, id ASC",
            (ticket_id,),
        ).fetchall()


# --- Triage ------------------------------------------------------------------


def add_note(db_path, ticket_id, author, body):
    """Append a note to a ticket and return the new note id."""
    author = _require_text("author", author)
    body = _require_text("body", body)

    with closing(get_conn(db_path)) as conn:
        _require_ticket(conn, ticket_id)
        cursor = conn.execute(
            "INSERT INTO notes (ticket_id, author, body, created_at) VALUES (?, ?, ?, ?)",
            (ticket_id, author, body, now_iso()),
        )
        conn.commit()
        return cursor.lastrowid


def assign_ticket(db_path, ticket_id, assignee):
    """Assign a ticket to a technician, or to nobody when assignee is None."""
    if assignee is not None:
        _require_member("assignee", assignee, TECHNICIANS)

    with closing(get_conn(db_path)) as conn:
        _require_ticket(conn, ticket_id)
        conn.execute(
            "UPDATE tickets SET assignee = ? WHERE id = ?", (assignee, ticket_id)
        )
        conn.commit()


def change_status(db_path, ticket_id, new_status):
    """Move a ticket to new_status, enforcing ALLOWED_TRANSITIONS.

    Entering Resolved stamps resolved_at; reopening (Resolved -> Open) clears
    it and keeps the assignee; closing preserves it. The only place in the
    codebase that writes tickets.status (PRINCIPLES.md §2).
    """
    _require_member("new_status", new_status, STATUSES)

    with closing(get_conn(db_path)) as conn:
        current = _require_ticket(conn, ticket_id)["status"]
        if not is_valid_transition(current, new_status):
            raise TransitionError(ticket_id, current, new_status)

        if new_status == "Resolved":
            conn.execute(
                "UPDATE tickets SET status = ?, resolved_at = ? WHERE id = ?",
                (new_status, now_iso(), ticket_id),
            )
        elif current == "Resolved" and new_status == "Open":
            conn.execute(
                "UPDATE tickets SET status = ?, resolved_at = NULL WHERE id = ?",
                (new_status, ticket_id),
            )
        else:
            conn.execute(
                "UPDATE tickets SET status = ? WHERE id = ?", (new_status, ticket_id)
            )
        conn.commit()


# --- Dashboard ---------------------------------------------------------------


def _hours_between(start_iso, end_iso):
    delta = datetime.fromisoformat(end_iso) - datetime.fromisoformat(start_iso)
    return delta.total_seconds() / 3600.0


def dashboard_metrics(db_path):
    """Return the four dashboard readings as one dict.

    Keys:
      by_status              {status: count} for every status, zeros included
      by_priority            {priority: count} for every priority
      workload               {technician or UNASSIGNED: open + in-progress count}
      oldest_open            up to 5 oldest Open/In Progress rows, oldest first
      avg_resolution_hours   mean of resolved_at - created_at, or None
      by_source              {source: {"count": int, "share": 0-1 float}}

    Deliberately absent: any per-technician resolution-speed comparison
    (PRINCIPLES.md §1). Workload counts open work only.
    """
    with closing(get_conn(db_path)) as conn:
        by_status = {status: 0 for status in STATUSES}
        for row in conn.execute("SELECT status, COUNT(*) AS n FROM tickets GROUP BY status"):
            by_status[row["status"]] = row["n"]

        by_priority = {priority: 0 for priority in PRIORITIES}
        for row in conn.execute(
            "SELECT priority, COUNT(*) AS n FROM tickets GROUP BY priority"
        ):
            by_priority[row["priority"]] = row["n"]

        workload = {technician: 0 for technician in TECHNICIANS}
        workload[UNASSIGNED] = 0
        for row in conn.execute(
            """
            SELECT COALESCE(assignee, ?) AS who, COUNT(*) AS n
            FROM tickets WHERE status IN (?, ?) GROUP BY who
            """,
            (UNASSIGNED, "Open", "In Progress"),
        ):
            workload[row["who"]] = row["n"]

        oldest_open = conn.execute(
            """
            SELECT * FROM tickets WHERE status IN (?, ?)
            ORDER BY created_at ASC, id ASC LIMIT 5
            """,
            ("Open", "In Progress"),
        ).fetchall()

        durations = [
            _hours_between(row["created_at"], row["resolved_at"])
            for row in conn.execute(
                "SELECT created_at, resolved_at FROM tickets WHERE resolved_at IS NOT NULL"
            )
        ]
        avg_resolution_hours = statistics.mean(durations) if durations else None

        source_counts = {source: 0 for source in SOURCES}
        for row in conn.execute(
            "SELECT source, COUNT(*) AS n FROM tickets GROUP BY source"
        ):
            source_counts[row["source"]] = row["n"]
        total = sum(source_counts.values())
        by_source = {
            source: {
                "count": count,
                "share": (count / total) if total else 0.0,
            }
            for source, count in source_counts.items()
        }

    return {
        "by_status": by_status,
        "by_priority": by_priority,
        "workload": workload,
        "oldest_open": oldest_open,
        "avg_resolution_hours": avg_resolution_hours,
        "by_source": by_source,
    }
