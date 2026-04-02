#!/usr/bin/env python3
"""
Luma Registration Sync — Pull event registrations from Luma into Google Sheets.

Usage:
  Interactive:  python luma_sync.py
  Batch:        python luma_sync.py --event-id evt-XXX --mode replace
  Append:       python luma_sync.py --event-id evt-XXX --sheet-id SHEET_ID --mode append
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Luma API Client
# ---------------------------------------------------------------------------

LUMA_BASE = "https://public-api.luma.com"


class LumaClient:
    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers["x-luma-api-key"] = api_key

    def get_event(self, event_id: str) -> dict:
        r = self.session.get(f"{LUMA_BASE}/v1/event/get", params={"id": event_id})
        r.raise_for_status()
        return r.json().get("event", r.json())

    def get_guests(self, event_id: str, approval_status: str | None = None) -> list[dict]:
        guests = []
        params: dict = {"event_id": event_id, "pagination_limit": 100}
        if approval_status:
            params["approval_status"] = approval_status

        while True:
            r = self.session.get(f"{LUMA_BASE}/v1/event/get-guests", params=params)
            r.raise_for_status()
            data = r.json()
            for entry in data.get("entries", []):
                # API nests guest data under "guest" key
                guest = entry.get("guest", entry)
                guests.append(guest)
            if not data.get("has_more"):
                break
            params["pagination_cursor"] = data["next_cursor"]

        return guests


# ---------------------------------------------------------------------------
# Data extraction
# ---------------------------------------------------------------------------

# Fixed columns always present
FIXED_HEADER = [
    "Name",
    "Email",
    "Status",
    "Registered At",
    "Checked In At",
    "Ticket Type",
    "Company",
    "Job Title",
    "LinkedIn",
    "GitHub",
    "Check-in QR",
]

# Map question_type to a known column; anything else becomes a dynamic column
ANSWER_TYPE_TO_COLUMN = {
    "company": None,   # handled specially (company + job_title)
    "linkedin": "LinkedIn",
    "github": "GitHub",
    "terms": None,     # skip terms checkbox
}


def _extract_answer_value(answer: dict) -> str:
    """Extract a display-friendly string from a registration answer."""
    val = answer.get("value", answer.get("answer", ""))
    if isinstance(val, bool):
        return "Yes" if val else "No"
    if isinstance(val, list):
        return ", ".join(str(v) for v in val)
    if isinstance(val, dict):
        return json.dumps(val, ensure_ascii=False)
    return str(val) if val else ""


def build_header_and_rows(guests: list[dict]) -> tuple[list[str], list[list[str]]]:
    """Build the full header (fixed + dynamic question columns) and all rows."""
    # First pass: discover dynamic question columns across all guests
    dynamic_columns: dict[str, str] = {}  # question_id -> label
    for guest in guests:
        for ans in guest.get("registration_answers") or []:
            qtype = ans.get("question_type", "")
            qid = ans.get("question_id", "")
            if qtype in ANSWER_TYPE_TO_COLUMN:
                continue  # handled by fixed columns or skipped
            if qid and qid not in dynamic_columns:
                dynamic_columns[qid] = ans.get("label", f"Q-{qid}")

    header = FIXED_HEADER + list(dynamic_columns.values())
    dynamic_ids = list(dynamic_columns.keys())

    # Second pass: build rows
    rows = []
    for guest in guests:
        tickets = guest.get("event_tickets") or []
        ticket_name = tickets[0].get("name", "") if tickets else ""

        # Parse registration answers into a lookup
        answers_by_type: dict[str, dict] = {}
        answers_by_id: dict[str, dict] = {}
        for ans in guest.get("registration_answers") or []:
            answers_by_type[ans.get("question_type", "")] = ans
            answers_by_id[ans.get("question_id", "")] = ans

        company_ans = answers_by_type.get("company", {})

        row = [
            guest.get("user_name") or guest.get("name") or "",
            guest.get("user_email") or guest.get("email") or "",
            guest.get("approval_status") or "",
            guest.get("registered_at") or "",
            guest.get("checked_in_at") or "",
            ticket_name,
            company_ans.get("answer_company", company_ans.get("answer", "")),
            company_ans.get("answer_job_title", ""),
            _extract_answer_value(answers_by_type.get("linkedin", {})),
            _extract_answer_value(answers_by_type.get("github", {})),
            guest.get("check_in_qr_code") or "",
        ]

        # Dynamic columns
        for qid in dynamic_ids:
            ans = answers_by_id.get(qid, {})
            row.append(_extract_answer_value(ans))

        rows.append(row)

    return header, rows


# ---------------------------------------------------------------------------
# Google Sheets (OAuth)
# ---------------------------------------------------------------------------

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
SCRIPT_DIR = Path(__file__).resolve().parent
TOKEN_PATH = SCRIPT_DIR / "credentials" / "token.json"
CLIENT_SECRET_CANDIDATES = [
    SCRIPT_DIR / "credentials" / "client_secret.json",
    SCRIPT_DIR / "credentials" / "credentials.json",
    SCRIPT_DIR / "client_secret.json",
]


def _find_client_secret() -> Path:
    for p in CLIENT_SECRET_CANDIDATES:
        if p.exists():
            return p
    print("\nGoogle OAuth client_secret.json not found.")
    print("Looked in:")
    for p in CLIENT_SECRET_CANDIDATES:
        print(f"  {p}")
    print("\nTo set up Google Sheets access:")
    print("  1. Go to https://console.cloud.google.com")
    print("  2. Create a project and enable the Google Sheets API + Google Drive API")
    print("  3. Create OAuth 2.0 credentials (Desktop application)")
    print("  4. Download the JSON and save it as credentials/client_secret.json")
    sys.exit(1)


def get_gspread_client():
    import gspread
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_secret = _find_client_secret()
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(creds.to_json())

    return gspread.authorize(creds)


def write_to_sheet(
    header: list[str], rows: list[list[str]], sheet_id: str | None, mode: str, event_name: str
) -> str:
    """Write guest rows to Google Sheets. Returns the sheet URL."""
    gc = get_gspread_client()
    tab_name = "Luma Registrations"

    if sheet_id:
        sh = gc.open_by_key(sheet_id)
    else:
        title = f"Luma — {event_name} — {datetime.now().strftime('%Y-%m-%d')}"
        sh = gc.create(title)
        print(f"Created new sheet: {sh.url}")

    # Get or create the tab
    try:
        ws = sh.worksheet(tab_name)
    except Exception:
        ws = sh.add_worksheet(title=tab_name, rows=max(len(rows) + 1, 100), cols=len(header))

    if mode == "replace":
        ws.clear()
        ws.update(range_name="A1", values=[header] + rows)
        print(f"Wrote {len(rows)} rows (replace mode).")
    elif mode == "append":
        existing = ws.get_all_values()
        if not existing:
            ws.update(range_name="A1", values=[header] + rows)
            print(f"Sheet was empty — wrote header + {len(rows)} rows.")
        else:
            # Deduplicate by email (column index 1)
            existing_emails = {r[1] for r in existing[1:] if len(r) > 1}
            new_rows = [r for r in rows if r[1] not in existing_emails]
            if new_rows:
                ws.append_rows(new_rows, value_input_option="RAW")
                print(f"Appended {len(new_rows)} new rows ({len(rows) - len(new_rows)} already existed).")
            else:
                print("No new guests to append — sheet is up to date.")

    return sh.url


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------


def interactive(luma: LumaClient):
    default_event = os.getenv("LUMA_DEFAULT_EVENT_ID", "")
    prompt_suffix = f" [{default_event}]" if default_event else ""
    event_id = input(f"Event ID (evt-...){prompt_suffix}: ").strip() or default_event
    if not event_id:
        print("No event ID provided. Exiting.")
        return

    print(f"\nFetching event {event_id}...")
    event = luma.get_event(event_id)
    event_name = event.get("name", "Unknown Event")
    start = event.get("start_at", "")
    print(f"  Event: {event_name}")
    print(f"  Date:  {start}")

    confirm = input("\nProceed? [Y/n]: ").strip().lower()
    if confirm and confirm != "y":
        print("Cancelled.")
        return

    status_filter = (
        input("Filter by status (approved/pending_approval/invited/declined/waitlist) or Enter for all: ").strip()
        or None
    )

    choice = input("Write to (e)xisting sheet or (n)ew sheet? [n]: ").strip().lower()
    sheet_id = None
    if choice == "e":
        sheet_id = input("Google Sheet ID: ").strip()
        if not sheet_id:
            print("No sheet ID provided, creating new sheet.")

    mode = input("Mode — (r)eplace or (a)ppend? [r]: ").strip().lower()
    mode = "append" if mode == "a" else "replace"

    print(f"\nFetching guests...")
    guests = luma.get_guests(event_id, approval_status=status_filter)
    print(f"  Found {len(guests)} guest(s).")

    if not guests:
        print("No guests to write.")
        return

    header, rows = build_header_and_rows(guests)
    url = write_to_sheet(header, rows, sheet_id, mode, event_name)
    print(f"\nDone! Sheet: {url}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Sync Luma event registrations to Google Sheets")
    parser.add_argument("--event-id", help="Luma event ID (evt-...)")
    parser.add_argument("--api-key", help="Luma API key (or set LUMA_API_KEY env var)")
    parser.add_argument("--sheet-id", help="Existing Google Sheet ID (omit to create new)")
    parser.add_argument(
        "--mode",
        choices=["replace", "append"],
        default="replace",
        help="replace: overwrite sheet; append: add new guests only (default: replace)",
    )
    parser.add_argument("--status", help="Filter guests by approval status")
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("LUMA_API_KEY")
    if not api_key:
        print("Error: Luma API key required. Pass --api-key or set LUMA_API_KEY in .env")
        sys.exit(1)

    luma = LumaClient(api_key)

    # No event-id flag → interactive mode
    if not args.event_id:
        interactive(luma)
        return

    # Batch mode
    event_id = args.event_id
    print(f"Fetching event {event_id}...")
    event = luma.get_event(event_id)
    event_name = event.get("name", "Unknown Event")
    print(f"  Event: {event_name}")

    print("Fetching guests...")
    guests = luma.get_guests(event_id, approval_status=args.status)
    print(f"  Found {len(guests)} guest(s).")

    if not guests:
        print("No guests to write.")
        return

    header, rows = build_header_and_rows(guests)
    url = write_to_sheet(header, rows, args.sheet_id, args.mode, event_name)
    print(f"\nDone! Sheet: {url}")


if __name__ == "__main__":
    main()
