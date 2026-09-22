"""Behaviour tests for core.py.

Every test runs against a real SQLite file under tmp_path -- the database is
the thing under test, so it is never mocked and labdesk.db is never touched
(PRINCIPLES.md §9). Wall-clock time is injected through the core.now_iso seam.
"""

import pytest

import core
import seed

OPEN, IN_PROGRESS, RESOLVED, CLOSED = core.STATUSES
PRIYA, DIEGO, HANNAH = core.TECHNICIANS

# How to walk a fresh ticket to each status using only legal transitions.
_ROUTE_TO = {
    OPEN: (),
    IN_PROGRESS: (IN_PROGRESS,),
    RESOLVED: (IN_PROGRESS, RESOLVED),
    CLOSED: (IN_PROGRESS, RESOLVED, CLOSED),
}


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "labdesk_test.db")
    core.init_db(path)
    return path


def _freeze_clock(monkeypatch, moment):
    """Pin core.now_iso() to a fixed ISO string."""
    monkeypatch.setattr(core, "now_iso", lambda: moment)


def _new_ticket(db_path, **overrides):
    fields = {
        "title": "Projector in ENG 276 shows no signal",
        "description": "No signal from the podium laptop.",
        "category": "Lab hardware",
        "priority": "High",
        "source": "Walk-in",
        "requester_name": "Ana Castillo",
        "requester_email": "ana.castillo@sjsu.edu",
    }
    fields.update(overrides)
    return core.create_ticket(db_path, **fields)


def _ticket_in_status(db_path, status, **overrides):
    ticket_id = _new_ticket(db_path, **overrides)
    for step in _ROUTE_TO[status]:
        core.change_status(db_path, ticket_id, step)
    return ticket_id


# --- Submit ------------------------------------------------------------------


def test_new_ticket_is_open_unassigned_and_listed(db_path, monkeypatch):
    _freeze_clock(monkeypatch, "2026-03-02T09:30:00")

    ticket_id = core.create_ticket(
        db_path,
        "Wi-Fi keeps dropping in ENG 405",
        "Connection drops every few minutes near the window.",
        "Network",
        "High",
        "Web form",
        "Meera Patel",
        "meera.patel@sjsu.edu",
    )

    row = core.get_ticket(db_path, ticket_id)
    assert row["title"] == "Wi-Fi keeps dropping in ENG 405"
    assert row["description"] == "Connection drops every few minutes near the window."
    assert row["category"] == "Network"
    assert row["priority"] == "High"
    assert row["source"] == "Web form"
    assert row["requester_name"] == "Meera Patel"
    assert row["requester_email"] == "meera.patel@sjsu.edu"
    assert row["status"] == OPEN
    assert row["assignee"] is None
    assert row["created_at"] == "2026-03-02T09:30:00"
    assert row["resolved_at"] is None
    assert [r["id"] for r in core.list_tickets(db_path)] == [ticket_id]


def test_get_ticket_returns_none_for_an_unknown_id(db_path):
    assert core.get_ticket(db_path, 404) is None


def test_create_ticket_rejects_an_empty_title(db_path):
    with pytest.raises(ValueError) as excinfo:
        _new_ticket(db_path, title="   ")

    assert "title" in str(excinfo.value)
    assert core.list_tickets(db_path) == []


def test_create_ticket_rejects_an_empty_requester_name(db_path):
    with pytest.raises(ValueError) as excinfo:
        _new_ticket(db_path, requester_name="")

    assert "requester_name" in str(excinfo.value)


def test_create_ticket_rejects_an_unknown_category(db_path):
    with pytest.raises(ValueError) as excinfo:
        _new_ticket(db_path, category="Telepathy")

    message = str(excinfo.value)
    assert "category" in message
    assert "Telepathy" in message
    assert core.list_tickets(db_path) == []


# --- Queue -------------------------------------------------------------------


@pytest.fixture
def queue_db(db_path, monkeypatch):
    """Four tickets whose fields make every filter combination checkable."""
    ids = {}

    def add(key, created_at, **overrides):
        _freeze_clock(monkeypatch, created_at)
        ids[key] = _new_ticket(db_path, **overrides)

    add(
        "projector",
        "2026-03-01T09:00:00",
        title="Projector in ENG 276 shows no signal",
        description="No signal from the podium laptop.",
        category="Lab hardware",
        priority="High",
    )
    add(
        "wifi",
        "2026-03-02T09:00:00",
        title="Wi-Fi keeps dropping in ENG 405",
        description="The PROJECTOR cart in the same room is also unplugged.",
        category="Network",
        priority="High",
    )
    add(
        "printer",
        "2026-03-03T09:00:00",
        title="Printer jams on duplex jobs",
        description="Single sided printing is fine.",
        category="Printing",
        priority="Low",
    )
    add(
        "lamp",
        "2026-03-04T09:00:00",
        title="Projector lamp replaced but colors look green",
        description="Strong green tint since the swap.",
        category="Lab hardware",
        priority="High",
    )

    core.assign_ticket(db_path, ids["projector"], PRIYA)
    core.assign_ticket(db_path, ids["lamp"], DIEGO)
    core.change_status(db_path, ids["lamp"], IN_PROGRESS)
    return db_path, ids


def test_tickets_are_listed_newest_first(queue_db):
    db_path, ids = queue_db

    listed = [row["id"] for row in core.list_tickets(db_path)]

    assert listed == [ids["lamp"], ids["printer"], ids["wifi"], ids["projector"]]


def test_search_matches_title_or_description_case_insensitively(queue_db):
    db_path, ids = queue_db

    found = {row["id"] for row in core.list_tickets(db_path, search="pRoJeCtOr")}

    # title match, description match, and a second title match
    assert found == {ids["projector"], ids["wifi"], ids["lamp"]}


def test_filters_combine_with_and(queue_db):
    db_path, ids = queue_db

    by_status = core.list_tickets(db_path, search="projector", status=OPEN)
    by_category_and_priority = core.list_tickets(
        db_path, category="Lab hardware", priority="High"
    )
    narrowed = core.list_tickets(
        db_path, search="PROJECTOR", status=OPEN, priority="High", assignee=PRIYA
    )

    assert [row["id"] for row in by_status] == [ids["wifi"], ids["projector"]]
    assert [row["id"] for row in by_category_and_priority] == [
        ids["lamp"],
        ids["projector"],
    ]
    assert [row["id"] for row in narrowed] == [ids["projector"]]


def test_unassigned_filter_returns_only_tickets_with_no_assignee(queue_db):
    db_path, ids = queue_db

    unassigned = core.list_tickets(db_path, assignee=core.UNASSIGNED)

    assert [row["id"] for row in unassigned] == [ids["printer"], ids["wifi"]]


def test_filters_that_match_nothing_return_an_empty_list(queue_db):
    db_path, _ = queue_db

    assert core.list_tickets(db_path, search="hovercraft") == []


# --- Triage ------------------------------------------------------------------


def test_notes_are_listed_oldest_first(db_path, monkeypatch):
    ticket_id = _new_ticket(db_path)

    _freeze_clock(monkeypatch, "2026-03-02T10:00:00")
    core.add_note(db_path, ticket_id, PRIYA, "Checked the HDMI switcher.")
    _freeze_clock(monkeypatch, "2026-03-02T15:00:00")
    core.add_note(db_path, ticket_id, PRIYA, "Loaner cable in place.")

    notes = core.list_notes(db_path, ticket_id)
    assert [note["body"] for note in notes] == [
        "Checked the HDMI switcher.",
        "Loaner cable in place.",
    ]
    assert [note["author"] for note in notes] == [PRIYA, PRIYA]
    assert notes[0]["created_at"] == "2026-03-02T10:00:00"


def test_assign_ticket_rejects_someone_who_is_not_a_technician(db_path):
    ticket_id = _new_ticket(db_path)

    with pytest.raises(ValueError) as excinfo:
        core.assign_ticket(db_path, ticket_id, "Sammy Spartan")

    assert "assignee" in str(excinfo.value)
    assert core.get_ticket(db_path, ticket_id)["assignee"] is None


def test_open_to_in_progress_is_allowed(db_path):
    ticket_id = _new_ticket(db_path)

    core.change_status(db_path, ticket_id, IN_PROGRESS)

    assert core.get_ticket(db_path, ticket_id)["status"] == IN_PROGRESS


def test_open_to_closed_is_rejected(db_path):
    ticket_id = _ticket_in_status(db_path, OPEN)

    with pytest.raises(core.TransitionError) as excinfo:
        core.change_status(db_path, ticket_id, CLOSED)

    message = str(excinfo.value)
    assert OPEN in message and CLOSED in message
    assert core.get_ticket(db_path, ticket_id)["status"] == OPEN


def test_open_to_resolved_is_rejected(db_path):
    ticket_id = _ticket_in_status(db_path, OPEN)

    with pytest.raises(core.TransitionError) as excinfo:
        core.change_status(db_path, ticket_id, RESOLVED)

    message = str(excinfo.value)
    assert OPEN in message and RESOLVED in message
    assert core.get_ticket(db_path, ticket_id)["status"] == OPEN


def test_closed_to_open_is_rejected(db_path):
    ticket_id = _ticket_in_status(db_path, CLOSED)

    with pytest.raises(core.TransitionError) as excinfo:
        core.change_status(db_path, ticket_id, OPEN)

    message = str(excinfo.value)
    assert CLOSED in message and OPEN in message
    assert excinfo.value.ticket_id == ticket_id
    assert core.get_ticket(db_path, ticket_id)["status"] == CLOSED


def test_resolving_stamps_resolved_at(db_path, monkeypatch):
    _freeze_clock(monkeypatch, "2026-03-02T09:00:00")
    ticket_id = _ticket_in_status(db_path, IN_PROGRESS)

    _freeze_clock(monkeypatch, "2026-03-03T14:00:00")
    core.change_status(db_path, ticket_id, RESOLVED)

    row = core.get_ticket(db_path, ticket_id)
    assert row["status"] == RESOLVED
    assert row["created_at"] == "2026-03-02T09:00:00"
    assert row["resolved_at"] == "2026-03-03T14:00:00"


def test_reopening_clears_resolved_at_and_keeps_the_assignee(db_path, monkeypatch):
    _freeze_clock(monkeypatch, "2026-03-02T09:00:00")
    ticket_id = _ticket_in_status(db_path, RESOLVED)
    core.assign_ticket(db_path, ticket_id, HANNAH)
    assert core.get_ticket(db_path, ticket_id)["resolved_at"] is not None

    core.change_status(db_path, ticket_id, OPEN)

    row = core.get_ticket(db_path, ticket_id)
    assert row["status"] == OPEN
    assert row["resolved_at"] is None
    assert row["assignee"] == HANNAH


def test_closing_preserves_resolved_at(db_path, monkeypatch):
    _freeze_clock(monkeypatch, "2026-03-02T09:00:00")
    ticket_id = _ticket_in_status(db_path, IN_PROGRESS)
    _freeze_clock(monkeypatch, "2026-03-04T11:00:00")
    core.change_status(db_path, ticket_id, RESOLVED)

    _freeze_clock(monkeypatch, "2026-03-09T08:00:00")
    core.change_status(db_path, ticket_id, CLOSED)

    row = core.get_ticket(db_path, ticket_id)
    assert row["status"] == CLOSED
    assert row["resolved_at"] == "2026-03-04T11:00:00"


# --- Dashboard ---------------------------------------------------------------


@pytest.fixture
def metrics_db(db_path, monkeypatch):
    """Eight tickets with counts, sources and resolution times known by hand.

    Open: t1, t2, t7, t8   In Progress: t3, t4   Resolved: t5   Closed: t6
    Resolution times: t5 = 4 h, t6 = 48 h  ->  mean 26.0 h
    """
    ids = {}

    def add(key, created_at, **overrides):
        _freeze_clock(monkeypatch, created_at)
        ids[key] = _new_ticket(db_path, **overrides)

    add("t1", "2026-03-01T09:00:00", priority="Urgent", source="Walk-in")
    add("t2", "2026-03-02T09:00:00", priority="High", source="Web form")
    add("t3", "2026-03-03T09:00:00", priority="High", source="Web form")
    add("t4", "2026-03-04T09:00:00", priority="Medium", source="Email")
    add("t5", "2026-03-05T09:00:00", priority="Low", source="Email")
    add("t6", "2026-03-06T09:00:00", priority="Low", source="Walk-in")
    add("t7", "2026-03-07T09:00:00", priority="Medium", source="Web form")
    add("t8", "2026-03-08T09:00:00", priority="Medium", source="Email")

    core.assign_ticket(db_path, ids["t2"], PRIYA)
    core.assign_ticket(db_path, ids["t3"], PRIYA)
    core.change_status(db_path, ids["t3"], IN_PROGRESS)
    core.assign_ticket(db_path, ids["t4"], DIEGO)
    core.change_status(db_path, ids["t4"], IN_PROGRESS)

    core.assign_ticket(db_path, ids["t5"], DIEGO)
    core.change_status(db_path, ids["t5"], IN_PROGRESS)
    _freeze_clock(monkeypatch, "2026-03-05T13:00:00")  # 4 hours
    core.change_status(db_path, ids["t5"], RESOLVED)

    core.assign_ticket(db_path, ids["t6"], HANNAH)
    core.change_status(db_path, ids["t6"], IN_PROGRESS)
    _freeze_clock(monkeypatch, "2026-03-08T09:00:00")  # 48 hours
    core.change_status(db_path, ids["t6"], RESOLVED)
    core.change_status(db_path, ids["t6"], CLOSED)

    return db_path, ids


def test_dashboard_counts_tickets_by_status(metrics_db):
    db_path, _ = metrics_db

    metrics = core.dashboard_metrics(db_path)

    assert metrics["by_status"] == {
        OPEN: 4,
        IN_PROGRESS: 2,
        RESOLVED: 1,
        CLOSED: 1,
    }


def test_dashboard_counts_tickets_by_priority(metrics_db):
    db_path, _ = metrics_db

    metrics = core.dashboard_metrics(db_path)

    assert metrics["by_priority"] == {"Low": 2, "Medium": 3, "High": 2, "Urgent": 1}


def test_dashboard_workload_counts_active_tickets_per_technician(metrics_db):
    db_path, _ = metrics_db

    metrics = core.dashboard_metrics(db_path)

    assert metrics["workload"] == {
        PRIYA: 2,
        DIEGO: 1,
        HANNAH: 0,
        core.UNASSIGNED: 3,
    }


def test_dashboard_reports_counts_and_shares_by_source(metrics_db):
    db_path, _ = metrics_db

    by_source = core.dashboard_metrics(db_path)["by_source"]

    assert {name: entry["count"] for name, entry in by_source.items()} == {
        "Web form": 3,
        "Email": 3,
        "Walk-in": 2,
    }
    assert by_source["Web form"]["share"] == pytest.approx(0.375)
    assert by_source["Email"]["share"] == pytest.approx(0.375)
    assert by_source["Walk-in"]["share"] == pytest.approx(0.25)
    assert sum(entry["share"] for entry in by_source.values()) == pytest.approx(1.0)


def test_dashboard_averages_resolution_hours_over_resolved_tickets(metrics_db):
    db_path, _ = metrics_db

    metrics = core.dashboard_metrics(db_path)

    assert metrics["avg_resolution_hours"] == pytest.approx(26.0)


def test_dashboard_average_resolution_is_none_without_resolved_tickets(db_path):
    _new_ticket(db_path)

    metrics = core.dashboard_metrics(db_path)

    assert metrics["avg_resolution_hours"] is None


def test_dashboard_lists_the_five_oldest_active_tickets_oldest_first(metrics_db):
    db_path, ids = metrics_db

    oldest_open = core.dashboard_metrics(db_path)["oldest_open"]

    assert [row["id"] for row in oldest_open] == [
        ids["t1"],
        ids["t2"],
        ids["t3"],
        ids["t4"],
        ids["t7"],
    ]


# --- Seed --------------------------------------------------------------------


def test_seeding_twice_produces_the_same_counts(tmp_path):
    db_path = str(tmp_path / "seeded.db")

    first = seed.seed_database(db_path)
    second = seed.seed_database(db_path)

    assert first == second
    assert first[0] == len(seed.TICKET_SEEDS)
    assert first[1] > 0
    assert len(core.list_tickets(db_path)) == first[0]


def test_seed_data_covers_every_category_priority_source_and_status(tmp_path):
    db_path = str(tmp_path / "seeded.db")
    seed.seed_database(db_path)

    tickets = core.list_tickets(db_path)

    assert {row["category"] for row in tickets} == set(core.CATEGORIES)
    assert {row["priority"] for row in tickets} == set(core.PRIORITIES)
    assert {row["source"] for row in tickets} == set(core.SOURCES)
    assert {row["status"] for row in tickets} == set(core.STATUSES)
    assert {row["assignee"] for row in tickets if row["assignee"]} == set(
        core.TECHNICIANS
    )
