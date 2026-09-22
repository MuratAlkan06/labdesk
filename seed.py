"""Reset the LabDesk database and fill it with a demo month of lab tickets.

Run it from the repository root::

    python seed.py

Every run drops and recreates both tables, so re-running is safe by
construction. The ticket content is hand-written and the random seed is fixed,
so two runs differ only in the run-time anchor the 30-day spread hangs from.

Seeding needs historical timestamps, so it writes created_at/resolved_at
directly instead of going through core.now_iso() -- the one place in the
codebase allowed to do that (PRINCIPLES.md §5). It still reads the clock only
through core.now_iso(), and it never writes a status outside of the data it
inserts.
"""

import random
from contextlib import closing
from datetime import datetime, timedelta

import core

# Fixed so every run produces identical demo data.
RANDOM_SEED = 165

# Derived from the single source of truth rather than retyped (PRINCIPLES.md §2).
OPEN, IN_PROGRESS, RESOLVED, CLOSED = core.STATUSES
PRIYA, DIEGO, HANNAH = core.TECHNICIANS

# --- Demo data ---------------------------------------------------------------
# days_ago is counted back from the moment seed.py runs; resolve_hours is the
# lifetime of a Resolved/Closed ticket and must stay under (days_ago - 1) * 24
# so no ticket is ever resolved in the future.

TICKET_SEEDS = [
    # -- Open --------------------------------------------------------------
    {
        "title": "Projector in ENG 276 shows no signal",
        "description": "The ceiling projector shows 'No Signal' from both podium laptops. Lab section starts at 1:30 and we cannot show slides.",
        "category": "Lab hardware",
        "priority": "Urgent",
        "source": "Walk-in",
        "requester_name": "Ana Castillo",
        "requester_email": "ana.castillo@sjsu.edu",
        "status": OPEN,
        "assignee": PRIYA,
        "days_ago": 11,
        "resolve_hours": None,
        "notes": [
            "Checked the HDMI switcher: input 2 is dead, input 1 works. Ordered a replacement from stores.",
            "Loaner cable in place so this week's sections can run; still waiting on the switcher to arrive.",
        ],
    },
    {
        "title": "Cannot log into lab iMac at station 12",
        "description": "My SJSU ID works on every other machine in ENG 213 but station 12 says the account is unavailable.",
        "category": "Account access",
        "priority": "High",
        "source": "Web form",
        "requester_name": "Brian Nguyen",
        "requester_email": "brian.nguyen@sjsu.edu",
        "status": OPEN,
        "assignee": None,
        "days_ago": 9,
        "resolve_hours": None,
        "notes": [],
    },
    {
        "title": "Wi-Fi keeps dropping in ENG 405 during labs",
        "description": "Connection drops every few minutes near the window side of the room. Affects most of our lab group.",
        "category": "Network",
        "priority": "High",
        "source": "Web form",
        "requester_name": "Meera Patel",
        "requester_email": "meera.patel@sjsu.edu",
        "status": OPEN,
        "assignee": PRIYA,
        "days_ago": 12,
        "resolve_hours": None,
        "notes": [
            "Reproduced on two laptops on the window side. Logged the access point name and channel.",
            "Facilities ticket opened with campus networking.",
            "Campus networking says a firmware push is scheduled for this week.",
        ],
    },
    {
        "title": "Request Vivado installed on the FPGA benches",
        "description": "CMPE 127 needs Vivado on benches 1 through 6 before the midterm project starts.",
        "category": "Software install",
        "priority": "Medium",
        "source": "Email",
        "requester_name": "Daniel Okafor",
        "requester_email": "daniel.okafor@sjsu.edu",
        "status": OPEN,
        "assignee": None,
        "days_ago": 4,
        "resolve_hours": None,
        "notes": [],
    },
    {
        "title": "Oscilloscope probe missing from bench 7",
        "description": "Only one probe left on the bench. The second one was not in the drawer at the start of the session.",
        "category": "Lab hardware",
        "priority": "Low",
        "source": "Walk-in",
        "requester_name": "Jasmine Vu",
        "requester_email": "jasmine.vu@sjsu.edu",
        "status": OPEN,
        "assignee": HANNAH,
        "days_ago": 3,
        "resolve_hours": None,
        "notes": [],
    },
    {
        "title": "Lab account locked after too many failed logins",
        "description": "Mistyped my password several times and now the lab account is locked. I have a demo tomorrow morning.",
        "category": "Account access",
        "priority": "Urgent",
        "source": "Walk-in",
        "requester_name": "Tyler Brooks",
        "requester_email": "tyler.brooks@sjsu.edu",
        "status": OPEN,
        "assignee": DIEGO,
        "days_ago": 1,
        "resolve_hours": None,
        "notes": [],
    },
    {
        "title": "Badge reader on the ENG 276 door rejects my Tower Card",
        "description": "The reader beeps twice and stays red. Other students in the same section get in fine.",
        "category": "Other",
        "priority": "Medium",
        "source": "Email",
        "requester_name": "Grace Lim",
        "requester_email": "grace.lim@sjsu.edu",
        "status": OPEN,
        "assignee": None,
        "days_ago": 7,
        "resolve_hours": None,
        "notes": [],
    },
    {
        "title": "Color printer prints blank pages after toner swap",
        "description": "Pages come out completely blank since the toner cartridge was replaced on Friday.",
        "category": "Printing",
        "priority": "Low",
        "source": "Web form",
        "requester_name": "Omar Haddad",
        "requester_email": "omar.haddad@sjsu.edu",
        "status": OPEN,
        "assignee": PRIYA,
        "days_ago": 2,
        "resolve_hours": None,
        "notes": [],
    },
    # -- In Progress -------------------------------------------------------
    {
        "title": "MATLAB license server rejects checkout in ENG 213",
        "description": "MATLAB opens then quits with a license checkout failure on every machine in the room.",
        "category": "Software install",
        "priority": "High",
        "source": "Email",
        "requester_name": "Sofia Martinez",
        "requester_email": "sofia.martinez@sjsu.edu",
        "status": IN_PROGRESS,
        "assignee": DIEGO,
        "days_ago": 5,
        "resolve_hours": None,
        "notes": [
            "License manager is up, but the lab subnet is not on the allow list.",
            "Sent the subnet to the college license admin and am waiting on confirmation.",
        ],
    },
    {
        "title": "Shared printer in ENG 213 jams on every duplex job",
        "description": "Single-sided printing works. Anything double-sided jams in the middle of the first sheet.",
        "category": "Printing",
        "priority": "Medium",
        "source": "Walk-in",
        "requester_name": "Kevin Doan",
        "requester_email": "kevin.doan@sjsu.edu",
        "status": IN_PROGRESS,
        "assignee": PRIYA,
        "days_ago": 4,
        "resolve_hours": None,
        "notes": [
            "Cleared two sheets from the duplexer. The jam repeats on heavy stock only.",
        ],
    },
    {
        "title": "Bench PC 4 will not power on",
        "description": "No lights, no fans. The outlet works because the bench lamp on the same strip is fine.",
        "category": "Lab hardware",
        "priority": "High",
        "source": "Walk-in",
        "requester_name": "Ryan Alvarado",
        "requester_email": "ryan.alvarado@sjsu.edu",
        "status": IN_PROGRESS,
        "assignee": PRIYA,
        "days_ago": 8,
        "resolve_hours": None,
        "notes": [
            "Power supply has no standby light. Swapped the power cable to rule it out, same result.",
            "Pulled a spare supply from the parts shelf; installing it after the afternoon lab.",
        ],
    },
    {
        "title": "Ethernet port at seat 19 gives no link light",
        "description": "Wired connection is required for the embedded systems assignment and this seat has no link at all.",
        "category": "Network",
        "priority": "Medium",
        "source": "Web form",
        "requester_name": "Chloe Nakamura",
        "requester_email": "chloe.nakamura@sjsu.edu",
        "status": IN_PROGRESS,
        "assignee": DIEGO,
        "days_ago": 6,
        "resolve_hours": None,
        "notes": [],
    },
    {
        "title": "Need my lab drive quota raised for the senior project",
        "description": "Our capstone dataset is about 12 GB and the lab profile quota is 5 GB.",
        "category": "Other",
        "priority": "Low",
        "source": "Email",
        "requester_name": "Ibrahim Sayed",
        "requester_email": "ibrahim.sayed@sjsu.edu",
        "status": IN_PROGRESS,
        "assignee": HANNAH,
        "days_ago": 10,
        "resolve_hours": None,
        "notes": [],
    },
    # -- Resolved ----------------------------------------------------------
    {
        "title": "Chrome profile on lab iMac 3 will not sync bookmarks",
        "description": "Sign-in loops back to the sign-in page every time on that one machine.",
        "category": "Software install",
        "priority": "Low",
        "source": "Web form",
        "requester_name": "Lucas Ferreira",
        "requester_email": "lucas.ferreira@sjsu.edu",
        "status": RESOLVED,
        "assignee": HANNAH,
        "days_ago": 5,
        "resolve_hours": 20,
        "notes": [],
    },
    {
        "title": "Quartus install fails with a permissions error",
        "description": "The installer stops partway with an error about writing to the program folder.",
        "category": "Software install",
        "priority": "Medium",
        "source": "Email",
        "requester_name": "Priyanka Shah",
        "requester_email": "priyanka.shah@sjsu.edu",
        "status": RESOLVED,
        "assignee": DIEGO,
        "days_ago": 6,
        "resolve_hours": 30,
        "notes": [
            "Installer needs admin rights on the lab image; ran it from the lab admin account.",
            "Verified Quartus launches from a standard lab account afterward.",
        ],
    },
    {
        "title": "Soldering station tip burnt out at bench 2",
        "description": "The tip will not hold solder any more and the station reads low temperature.",
        "category": "Lab hardware",
        "priority": "Medium",
        "source": "Walk-in",
        "requester_name": "Emma Sullivan",
        "requester_email": "emma.sullivan@sjsu.edu",
        "status": RESOLVED,
        "assignee": PRIYA,
        "days_ago": 4,
        "resolve_hours": 6,
        "notes": [],
    },
    {
        "title": "Cannot reach the department file share from ENG 405",
        "description": "The share mounts in ENG 213 but times out from every machine in ENG 405.",
        "category": "Network",
        "priority": "High",
        "source": "Web form",
        "requester_name": "Victor Chen",
        "requester_email": "victor.chen@sjsu.edu",
        "status": RESOLVED,
        "assignee": PRIYA,
        "days_ago": 9,
        "resolve_hours": 48,
        "notes": [
            "Only ENG 405 is affected and ENG 213 mounts fine, so this looks like the room VLAN.",
            "Re-registered the room's DNS entry and the share mounts again.",
        ],
    },
    {
        "title": "Print quota shows zero pages after adding funds",
        "description": "Added ten dollars at the kiosk yesterday and the balance still shows zero pages.",
        "category": "Printing",
        "priority": "Medium",
        "source": "Email",
        "requester_name": "Hana Suzuki",
        "requester_email": "hana.suzuki@sjsu.edu",
        "status": RESOLVED,
        "assignee": DIEGO,
        "days_ago": 7,
        "resolve_hours": 26,
        "notes": [],
    },
    {
        "title": "Forgot lab workstation password before a demo",
        "description": "Need a reset for the shared workstation account ahead of the 9 am project demo.",
        "category": "Account access",
        "priority": "Urgent",
        "source": "Walk-in",
        "requester_name": "Marcus Hill",
        "requester_email": "marcus.hill@sjsu.edu",
        "status": RESOLVED,
        "assignee": HANNAH,
        "days_ago": 3,
        "resolve_hours": 2,
        "notes": [
            "Checked the Tower Card in person and reset the workstation password at the desk.",
        ],
    },
    {
        "title": "Lost and found: USB drive left in ENG 276",
        "description": "Left a black USB drive in the front-row machine after Tuesday's lab.",
        "category": "Other",
        "priority": "Low",
        "source": "Walk-in",
        "requester_name": "Alina Petrov",
        "requester_email": "alina.petrov@sjsu.edu",
        "status": RESOLVED,
        "assignee": PRIYA,
        "days_ago": 8,
        "resolve_hours": 72,
        "notes": [],
    },
    # -- Closed ------------------------------------------------------------
    {
        "title": "Projector colors look washed out in ENG 213",
        "description": "Everything on the projector has a strong green tint since the lamp was replaced.",
        "category": "Lab hardware",
        "priority": "Medium",
        "source": "Web form",
        "requester_name": "Noah Kim",
        "requester_email": "noah.kim@sjsu.edu",
        "status": CLOSED,
        "assignee": PRIYA,
        "days_ago": 14,
        "resolve_hours": 30,
        "notes": [],
    },
    {
        "title": "New grader account for CMPE 102 section 5",
        "description": "Our new grader needs lab access so she can run the autograder on the lab machines.",
        "category": "Account access",
        "priority": "Medium",
        "source": "Email",
        "requester_name": "Rachel Adams",
        "requester_email": "rachel.adams@sjsu.edu",
        "status": CLOSED,
        "assignee": DIEGO,
        "days_ago": 16,
        "resolve_hours": 48,
        "notes": [],
    },
    {
        "title": "Install Anaconda on the data lab images",
        "description": "CMPE 131 needs Anaconda with pandas and matplotlib on the ENG 213 image.",
        "category": "Software install",
        "priority": "Medium",
        "source": "Email",
        "requester_name": "Jorge Ramirez",
        "requester_email": "jorge.ramirez@sjsu.edu",
        "status": CLOSED,
        "assignee": HANNAH,
        "days_ago": 18,
        "resolve_hours": 96,
        "notes": [],
    },
    {
        "title": "Network switch in the ENG 276 rack lost two ports",
        "description": "Benches 11 and 12 lost their wired connection in the middle of a lab session.",
        "category": "Network",
        "priority": "Urgent",
        "source": "Walk-in",
        "requester_name": "Derek Foster",
        "requester_email": "derek.foster@sjsu.edu",
        "status": CLOSED,
        "assignee": PRIYA,
        "days_ago": 21,
        "resolve_hours": 10,
        "notes": [
            "Ports 11 and 12 show a link but pass no traffic. Moved both benches to spare ports.",
            "Switch replaced from departmental spares and the old unit is tagged for return.",
        ],
    },
    {
        "title": "Large-format printer out of paper for poster day",
        "description": "Senior project posters are due this afternoon and the roll is empty.",
        "category": "Printing",
        "priority": "High",
        "source": "Walk-in",
        "requester_name": "Sarah Bennett",
        "requester_email": "sarah.bennett@sjsu.edu",
        "status": CLOSED,
        "assignee": DIEGO,
        "days_ago": 23,
        "resolve_hours": 4,
        "notes": [],
    },
    {
        "title": "Keyboard and mouse missing from station 9",
        "description": "Station 9 has a monitor and tower but no keyboard or mouse this morning.",
        "category": "Lab hardware",
        "priority": "Low",
        "source": "Walk-in",
        "requester_name": "Tommy Nguyen",
        "requester_email": "tommy.nguyen@sjsu.edu",
        "status": CLOSED,
        "assignee": PRIYA,
        "days_ago": 25,
        "resolve_hours": 20,
        "notes": [],
    },
    {
        "title": "Cannot access the shared lab calendar",
        "description": "The lab reservation calendar says I do not have permission to view it.",
        "category": "Account access",
        "priority": "Low",
        "source": "Web form",
        "requester_name": "Elena Rossi",
        "requester_email": "elena.rossi@sjsu.edu",
        "status": CLOSED,
        "assignee": HANNAH,
        "days_ago": 26,
        "resolve_hours": 34,
        "notes": [],
    },
    {
        "title": "Request a second monitor for the capstone bench",
        "description": "Our team works from the capstone bench most evenings and one monitor is tight for debugging.",
        "category": "Other",
        "priority": "Medium",
        "source": "Web form",
        "requester_name": "Alex Turner",
        "requester_email": "alex.turner@sjsu.edu",
        "status": CLOSED,
        "assignee": PRIYA,
        "days_ago": 28,
        "resolve_hours": 120,
        "notes": [],
    },
    {
        "title": "VPN required to reach the license server from home",
        "description": "Tools that work in the lab fail to find the license server from off campus.",
        "category": "Network",
        "priority": "High",
        "source": "Email",
        "requester_name": "Dmitri Volkov",
        "requester_email": "dmitri.volkov@sjsu.edu",
        "status": CLOSED,
        "assignee": DIEGO,
        "days_ago": 29,
        "resolve_hours": 52,
        "notes": [
            "Confirmed the license server is reachable from the campus network only, by design.",
            "Sent the campus VPN setup page and confirmed checkout works over the VPN.",
        ],
    },
    {
        "title": "Printer driver missing on the new Windows image",
        "description": "The ENG 213 printer does not appear in the printer list after the image update.",
        "category": "Printing",
        "priority": "High",
        "source": "Email",
        "requester_name": "Nina Alvarez",
        "requester_email": "nina.alvarez@sjsu.edu",
        "status": CLOSED,
        "assignee": PRIYA,
        "days_ago": 27,
        "resolve_hours": 18,
        "notes": [],
    },
]

_INSERT_TICKET = """
INSERT INTO tickets (
    title, description, category, priority, source,
    requester_name, requester_email, status, assignee, created_at, resolved_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

_INSERT_NOTE = """
INSERT INTO notes (ticket_id, author, body, created_at) VALUES (?, ?, ?, ?)
"""


def _timestamp(moment):
    """Format a datetime the way core.now_iso() does."""
    return moment.isoformat(timespec="seconds")


def _created_at(anchor, days_ago):
    """A desk-hours moment days_ago days before the run-time anchor."""
    day = anchor - timedelta(days=days_ago)
    return day.replace(
        hour=random.randint(8, 18),
        minute=random.choice((0, 10, 15, 25, 30, 40, 45, 55)),
        second=0,
        microsecond=0,
    )


def _check_seed(spec):
    """Fail loudly on demo data that the app could not display correctly."""
    for field, allowed in (
        ("category", core.CATEGORIES),
        ("priority", core.PRIORITIES),
        ("source", core.SOURCES),
        ("status", core.STATUSES),
    ):
        if spec[field] not in allowed:
            raise ValueError(f"seed data: {spec['title']!r} has an unknown {field}.")
    if spec["assignee"] is not None and spec["assignee"] not in core.TECHNICIANS:
        raise ValueError(f"seed data: {spec['title']!r} has an unknown assignee.")
    if spec["status"] != OPEN and spec["assignee"] is None:
        raise ValueError(f"seed data: {spec['title']!r} is {spec['status']} but unassigned.")
    resolved_status = spec["status"] in (RESOLVED, CLOSED)
    if resolved_status != (spec["resolve_hours"] is not None):
        raise ValueError(f"seed data: {spec['title']!r} resolve_hours does not match its status.")


def reset_db(db_path):
    """Drop both tables if they exist and recreate the schema."""
    with closing(core.get_conn(db_path)) as conn:
        conn.execute("DROP TABLE IF EXISTS notes")
        conn.execute("DROP TABLE IF EXISTS tickets")
        conn.commit()
    core.init_db(db_path)


def seed_database(db_path=core.DEFAULT_DB):
    """Reset db_path and insert the demo tickets. Returns (tickets, notes)."""
    random.seed(RANDOM_SEED)
    anchor = datetime.fromisoformat(core.now_iso())
    reset_db(db_path)

    ticket_count = 0
    note_count = 0
    with closing(core.get_conn(db_path)) as conn:
        for spec in TICKET_SEEDS:
            _check_seed(spec)
            created = _created_at(anchor, spec["days_ago"])
            resolved = None
            if spec["resolve_hours"] is not None:
                resolved = created + timedelta(hours=spec["resolve_hours"])
                if resolved > anchor:
                    raise ValueError(
                        f"seed data: {spec['title']!r} would resolve in the future."
                    )

            cursor = conn.execute(
                _INSERT_TICKET,
                (
                    spec["title"],
                    spec["description"],
                    spec["category"],
                    spec["priority"],
                    spec["source"],
                    spec["requester_name"],
                    spec["requester_email"],
                    spec["status"],
                    spec["assignee"],
                    _timestamp(created),
                    _timestamp(resolved) if resolved else None,
                ),
            )
            ticket_count += 1

            bodies = spec["notes"]
            if bodies:
                last_activity = resolved or anchor
                step = (last_activity - created) / (len(bodies) + 1)
                for position, body in enumerate(bodies, start=1):
                    conn.execute(
                        _INSERT_NOTE,
                        (
                            cursor.lastrowid,
                            spec["assignee"],
                            body,
                            _timestamp(created + step * position),
                        ),
                    )
                    note_count += 1
        conn.commit()

    return ticket_count, note_count


def main():
    tickets, notes = seed_database(core.DEFAULT_DB)
    print(f"Seeded {core.DEFAULT_DB}: {tickets} tickets, {notes} notes.")


if __name__ == "__main__":
    main()
