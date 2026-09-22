"""LabDesk Streamlit UI: Submit, Queue, Triage, Dashboard.

This module renders; core.py decides (PRINCIPLES.md §3). It writes no SQL and
opens no database connection of its own: every question about the data is
answered by a core function, and every option list is read from a core
constant rather than retyped (PRINCIPLES.md §2).

Run it from the repository root, where the database core.DEFAULT_DB lives::

    streamlit run app.py
"""

from datetime import datetime

import streamlit as st

import core

DB_PATH = core.DEFAULT_DB

# The no-filter choice in every queue selectbox; core reads None for "no filter".
ANY_VALUE = "All"

# The desk lead triages but is never assigned tickets, so they are not in
# core.TECHNICIANS. They can still author a note.
DESK_LEAD = "Desk Lead"
NOTE_AUTHORS = core.TECHNICIANS + [DESK_LEAD]

SUBMIT_PAGE = "Submit Ticket"
QUEUE_PAGE = "Queue"
DASHBOARD_PAGE = "Dashboard"
PAGES = [SUBMIT_PAGE, QUEUE_PAGE, DASHBOARD_PAGE]

# Which interface to show. This is a view switch, not a login: the project has
# no accounts and no authentication, so the sidebar simply asks which view you
# want. Student is listed first, so the default view is the narrower one.
STUDENT_ROLE = "Student"
STAFF_ROLE = "Staff"
ROLES = [STUDENT_ROLE, STAFF_ROLE]

# A ticket filed from the student view arrived through the web form by
# definition, so that view records this source instead of asking for it. Read
# from core rather than retyped (PRINCIPLES.md §2).
WEB_FORM = core.SOURCES[0]

# The only key this app puts in session state (PRINCIPLES.md §6): the ticket the
# Queue page currently has open, or None for the list view.
OPEN_TICKET_ID = "open_ticket_id"

PII_WARNING = (
    "Do not include student ID numbers or passwords in this ticket. "
    "The lab desk never needs them."
)

EM_DASH = "—"


# --- Small shared helpers ----------------------------------------------------


def filter_value(choice):
    """Translate an 'All' selectbox choice into core's None = no filter."""
    return None if choice == ANY_VALUE else choice


def assignee_label(ticket):
    """The assignee to show, using core's word for nobody."""
    return ticket["assignee"] or core.UNASSIGNED


def days_open(created_at):
    """Days between created_at and now, to one decimal.

    For a ticket that is still open: it is still accruing time, so the clock
    is the right end point. The clock is read through core.now_iso(), the
    codebase's single time seam (PRINCIPLES.md §5).
    """
    elapsed = datetime.fromisoformat(core.now_iso()) - datetime.fromisoformat(created_at)
    return round(elapsed.total_seconds() / 86400.0, 1)


def days_to_resolution(created_at, resolved_at):
    """Days between created_at and resolved_at, to one decimal.

    A resolved or closed ticket stopped accruing time when it was resolved,
    so its duration is resolved_at - created_at and never reads the clock
    (PRINCIPLES.md §2).
    """
    elapsed = datetime.fromisoformat(resolved_at) - datetime.fromisoformat(created_at)
    return round(elapsed.total_seconds() / 86400.0, 1)


def open_ticket(ticket_id):
    """Point the Queue page at ticket_id (or None for the list) and rerun."""
    st.session_state[OPEN_TICKET_ID] = ticket_id
    st.rerun()


# --- Feature 1: Submit -------------------------------------------------------


def render_submit(show_source):
    """The submit form. show_source is False in the student view.

    Staff choose the source because they back-enter requests that reached the
    desk by email or in person. Someone filing this form themselves is using
    the web form, so the student view records WEB_FORM rather than offering a
    choice the adoption metric would then have to trust.
    """
    st.header("Submit a ticket")
    st.write("Tell the lab desk what you need. Fields marked * are required.")

    with st.form("submit_ticket", clear_on_submit=True):
        title = st.text_input(
            "Title *", placeholder="Short summary, e.g. projector shows no signal"
        )
        description = st.text_area(
            "Description",
            placeholder="What happened, which room, which machine, when?",
        )
        st.caption(PII_WARNING)

        left, right = st.columns(2)
        with left:
            category = st.selectbox("Category", core.CATEGORIES)
            priority = st.selectbox("Priority", core.PRIORITIES)
            source = st.selectbox("Source", core.SOURCES) if show_source else WEB_FORM
        with right:
            requester_name = st.text_input("Your name *")
            requester_email = st.text_input("Your email")

        submitted = st.form_submit_button("Submit ticket")

    if not submitted:
        return

    if not title.strip():
        st.error("Title is required. Please describe the problem in a few words.")
        return
    if not requester_name.strip():
        st.error("Your name is required so the desk knows who to follow up with.")
        return

    try:
        ticket_id = core.create_ticket(
            DB_PATH,
            title,
            description,
            category,
            priority,
            source,
            requester_name,
            requester_email,
        )
    except ValueError as exc:
        st.error(str(exc))
        return

    st.success(
        f"Ticket #{ticket_id} submitted with status {core.STATUSES[0]}. "
        "It is waiting for a technician and is already on the Queue page."
    )


# --- Feature 2: Queue --------------------------------------------------------


def queue_row(ticket):
    """One ticket as the table row the queue shows."""
    return {
        "ID": ticket["id"],
        "Title": ticket["title"],
        "Status": ticket["status"],
        "Priority": ticket["priority"],
        "Category": ticket["category"],
        "Assignee": assignee_label(ticket),
        "Source": ticket["source"],
        "Created at": ticket["created_at"],
    }


def render_queue_list():
    st.header("Ticket queue")

    search = st.text_input(
        "Search title and description", placeholder="e.g. printer, MATLAB, ENG 213"
    )
    status_column, priority_column, category_column, assignee_column = st.columns(4)
    status = status_column.selectbox("Status", [ANY_VALUE] + core.STATUSES)
    priority = priority_column.selectbox("Priority", [ANY_VALUE] + core.PRIORITIES)
    category = category_column.selectbox("Category", [ANY_VALUE] + core.CATEGORIES)
    assignee = assignee_column.selectbox(
        "Assignee", [ANY_VALUE, core.UNASSIGNED] + core.TECHNICIANS
    )

    tickets = core.list_tickets(
        DB_PATH,
        search=search.strip() or None,
        status=filter_value(status),
        priority=filter_value(priority),
        category=filter_value(category),
        assignee=filter_value(assignee),
    )

    st.write(f"**{len(tickets)}** ticket(s) match the current search and filters.")
    if not tickets:
        st.info("No tickets match. Clear the search box or set a filter back to All.")
        return

    st.dataframe(
        [queue_row(ticket) for ticket in tickets],
        hide_index=True,
        # Capping the title keeps every other column, timestamps included,
        # on screen without sideways scrolling.
        column_config={"Title": st.column_config.TextColumn(width="medium")},
    )

    titles = {ticket["id"]: ticket["title"] for ticket in tickets}
    chosen = st.selectbox(
        "Open a ticket",
        list(titles),
        format_func=lambda ticket_id: f"#{ticket_id} {EM_DASH} {titles[ticket_id]}",
    )
    if st.button("Open ticket"):
        open_ticket(chosen)


def render_ticket_fields(ticket):
    st.subheader("Ticket details")
    left, right = st.columns(2)
    with left:
        st.write(f"**Status:** {ticket['status']}")
        st.write(f"**Priority:** {ticket['priority']}")
        st.write(f"**Category:** {ticket['category']}")
        st.write(f"**Source:** {ticket['source']}")
        st.write(f"**Assignee:** {assignee_label(ticket)}")
    with right:
        st.write(f"**Requester:** {ticket['requester_name']}")
        st.write(f"**Requester email:** {ticket['requester_email'] or EM_DASH}")
        st.write(f"**Created at:** {ticket['created_at']}")
        st.write(f"**Resolved at:** {ticket['resolved_at'] or EM_DASH}")
        # Which duration this ticket has depends on whether it has been
        # resolved: a Resolved or Closed ticket is measured to resolved_at,
        # only a still-open one against the clock (PRINCIPLES.md §2).
        if ticket["resolved_at"]:
            st.write(
                "**Days to resolution:** "
                f"{days_to_resolution(ticket['created_at'], ticket['resolved_at'])}"
            )
        else:
            st.write(f"**Days open:** {days_open(ticket['created_at'])}")

    st.write("**Description**")
    st.write(ticket["description"] or EM_DASH)


def render_notes(ticket_id):
    notes = core.list_notes(DB_PATH, ticket_id)
    st.subheader(f"Notes ({len(notes)})")
    if not notes:
        st.write("No notes yet.")
        return
    for note in notes:
        st.markdown(f"**{note['author']}** {EM_DASH} {note['created_at']}")
        st.write(note["body"])
        st.divider()


def render_detail(ticket_id):
    ticket = core.get_ticket(DB_PATH, ticket_id)
    if ticket is None:
        st.error(f"Ticket #{ticket_id} does not exist.")
        if st.button("Back to the queue"):
            open_ticket(None)
        return

    if st.button("Back to the queue"):
        open_ticket(None)

    st.header(f"Ticket #{ticket['id']} {EM_DASH} {ticket['title']}")
    render_triage(ticket)

    # Re-read after triage: the controls above may have just changed this
    # ticket, so the fields and notes below show the result of that change
    # rather than the state the page started with (PRINCIPLES.md §6).
    ticket = core.get_ticket(DB_PATH, ticket_id)
    render_ticket_fields(ticket)
    render_notes(ticket_id)


def render_queue():
    if st.session_state[OPEN_TICKET_ID] is None:
        render_queue_list()
    else:
        render_detail(st.session_state[OPEN_TICKET_ID])


# --- Feature 3: Triage (inside the ticket detail view) -----------------------


def render_assign(ticket):
    ticket_id = ticket["id"]
    options = [core.UNASSIGNED] + core.TECHNICIANS
    choice = st.selectbox(
        f"Assign ticket #{ticket_id} to",
        options,
        index=options.index(assignee_label(ticket)),
    )
    if not st.button("Apply assignment"):
        return

    try:
        core.assign_ticket(
            DB_PATH, ticket_id, None if choice == core.UNASSIGNED else choice
        )
    except ValueError as exc:
        st.error(str(exc))
        return

    if choice == core.UNASSIGNED:
        st.success(f"Ticket #{ticket_id} is now unassigned.")
    else:
        st.success(f"Ticket #{ticket_id} is assigned to {choice}.")


def render_status_change(ticket):
    ticket_id = ticket["id"]
    choice = st.selectbox(
        f"Set ticket #{ticket_id} status to",
        core.STATUSES,
        index=core.STATUSES.index(ticket["status"]),
    )
    pressed = st.button("Change status")
    st.caption(
        "Every status is listed on purpose. A move the desk's rules do not "
        "allow is refused with the reason, not hidden from you."
    )
    if not pressed:
        return

    try:
        core.change_status(DB_PATH, ticket_id, choice)
    except (core.TransitionError, ValueError) as exc:
        st.error(str(exc))
        return

    st.success(f"Ticket #{ticket_id} is now {choice}.")


def render_add_note(ticket_id):
    st.markdown("**Add a note**")
    with st.form(f"add_note_{ticket_id}", clear_on_submit=True):
        author = st.selectbox("Author", NOTE_AUTHORS)
        body = st.text_area("Note", placeholder="What did you check or change?")
        added = st.form_submit_button("Add note")

    if not added:
        return
    if not body.strip():
        st.error("Note text is required.")
        return

    try:
        core.add_note(DB_PATH, ticket_id, author, body)
    except ValueError as exc:
        st.error(str(exc))
        return

    st.success(f"Note added to ticket #{ticket_id}.")


def render_triage(ticket):
    st.subheader("Triage")
    assign_column, status_column = st.columns(2)
    with assign_column:
        render_assign(ticket)
    with status_column:
        render_status_change(ticket)
    render_add_note(ticket["id"])


# --- Feature 4: Dashboard ----------------------------------------------------


def render_counts(title, counts, note=None):
    """A labelled row of metrics plus the same counts as a bar chart."""
    st.subheader(title)
    if note:
        st.caption(note)
    columns = st.columns(len(counts))
    for column, (label, count) in zip(columns, counts.items()):
        column.metric(label, count)
    # sort=False keeps the bars in the order core defines the buckets in
    # (Low to Urgent, Open to Closed) instead of alphabetically; horizontal
    # bars keep multi-word labels like "In Progress" readable.
    st.bar_chart(
        {"Bucket": list(counts), "Tickets": list(counts.values())},
        x="Bucket",
        y="Tickets",
        x_label="",
        y_label="Tickets",
        sort=False,
        horizontal=True,
        height=220,
    )


def render_resolution_metric(avg_resolution_hours):
    st.subheader("Average time to resolution")
    if avg_resolution_hours is None:
        st.metric("Hours per resolved ticket", EM_DASH)
        st.caption("No ticket has been resolved yet.")
        return

    st.metric("Hours per resolved ticket", f"{avg_resolution_hours:.1f} hours")
    if avg_resolution_hours >= 48:
        st.caption(f"That is about {avg_resolution_hours / 24:.1f} days per ticket.")
    st.caption(
        "Measured from created_at to resolved_at over every ticket that has "
        "been resolved."
    )


def render_oldest_open(oldest_open):
    st.subheader("Oldest open tickets")
    if not oldest_open:
        st.info("Nothing is open. The queue is clear.")
        return
    st.dataframe(
        [
            {
                "ID": ticket["id"],
                "Title": ticket["title"],
                "Priority": ticket["priority"],
                "Assignee": assignee_label(ticket),
                "Created at": ticket["created_at"],
                "Days open": days_open(ticket["created_at"]),
            }
            for ticket in oldest_open
        ],
        hide_index=True,
    )


def render_by_source(by_source):
    st.subheader("Adoption: share of tickets by source")
    st.caption(
        "The adoption measure for the web form: the share of tickets that "
        "arrive through it instead of by email or at the desk."
    )
    st.dataframe(
        [
            {
                "Source": source,
                "Tickets": reading["count"],
                "Share": f"{reading['share'] * 100:.1f}%",
            }
            for source, reading in by_source.items()
        ],
        hide_index=True,
    )


def render_dashboard():
    st.header("Desk dashboard")
    metrics = core.dashboard_metrics(DB_PATH)

    render_counts("Tickets by status", metrics["by_status"])
    render_counts("Tickets by priority", metrics["by_priority"])
    render_counts(
        "Open tickets per technician",
        metrics["workload"],
        note=(
            "Open and In Progress tickets held by each technician, plus the "
            "tickets nobody has picked up yet."
        ),
    )
    render_oldest_open(metrics["oldest_open"])
    render_resolution_metric(metrics["avg_resolution_hours"])
    render_by_source(metrics["by_source"])


# --- Page shell --------------------------------------------------------------


def main():
    st.set_page_config(page_title="LabDesk", layout="wide")
    core.init_db(DB_PATH)
    if OPEN_TICKET_ID not in st.session_state:
        st.session_state[OPEN_TICKET_ID] = None

    st.sidebar.title("LabDesk")
    st.sidebar.caption("CMPE Department Lab Support Desk")
    role = st.sidebar.radio("View as", ROLES)
    # The student view is the submit form and nothing else, so it needs no page
    # navigation; the staff view is the whole desk. Hiding the "Go to" radio
    # also drops its value, so a switch back to Staff starts at Submit Ticket
    # instead of a page the student view never showed.
    is_staff = role == STAFF_ROLE
    page = st.sidebar.radio("Go to", PAGES) if is_staff else SUBMIT_PAGE

    st.title("LabDesk")
    if page == SUBMIT_PAGE:
        render_submit(show_source=is_staff)
    elif page == QUEUE_PAGE:
        render_queue()
    else:
        render_dashboard()


main()
